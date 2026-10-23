#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rw_lint 的两级缓存：解析结果（parse）与逐文件检查结果（issues）。

设计原则：**宁可重算，也不能复用错的结果。**

一级：解析缓存（ParseMemo）
    按 (绝对路径, mtime_ns, 文件大小) 命中。解析结果是纯派生数据，没有跨文件依赖，
    所以只要文件本身没变就可以放心复用。

二级：检查结果缓存（IssueCache）
    比一级多一道关卡。`check_file` 的结果除了本文件内容，还依赖四个**跨文件聚合集合**
    （all_sections / global_defines / referenced / unit_names）。
    只按 mtime 复用是错的 —— 改 A 文件可能让 B 文件的检查结论变化。

    所以把四个集合换成 ProbeSet，它会记录 check_file 做过的每一次
    `in` / `len` / 遍历。缓存里存的是「这些查询的答案」。
    复用前逐条重放：只要有一个答案变了，就重算这个文件。
    这是**按构造正确**的：没有记录到的输入不会被悄悄用旧值。

缓存目录：
    Windows  %LOCALAPPDATA%\\rw-modding-mcp\\lint
    其它     $XDG_CACHE_HOME/rw-modding-mcp/lint 或 ~/.cache/rw-modding-mcp/lint
    用环境变量 RW_LINT_CACHE=0 关闭。
"""

import hashlib
import io
import json
import os
import tempfile
import zlib

CACHE_VERSION = 3


# ---------------------------------------------------------------- 基础工具

def cache_root():
    override = os.environ.get("RW_LINT_CACHE_DIR")      # 测试 / CI 用来隔离
    if override:
        return override
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "rw-modding-mcp", "lint")


def cache_enabled():
    """RW_LINT_CACHE=0 / off / false 关闭缓存。"""
    return os.environ.get("RW_LINT_CACHE", "1").strip().lower() not in ("0", "off", "false", "no")


def digest(items):
    """稳定的摘要。

    两个坑都要避开：
    - 不能用内置 hash()，它每个进程都随机化；
    - 不能依赖迭代顺序，set/frozenset 的顺序同样随进程变化，
      所以先按 str 排序再摘要。
    """
    h = hashlib.md5()
    for it in sorted(items, key=str):
        h.update(str(it).encode("utf-8", "replace"))
        h.update(b"\x00")
    return h.hexdigest()[:16]


def _stat_key(path):
    st = os.stat(path)
    return (os.path.abspath(path), st.st_mtime_ns, st.st_size)


# ---------------------------------------------------------------- 一级：解析缓存

class ParseMemo:
    """parse_file 的记忆。只在进程内，用来避免同一文件被解析两次。"""

    def __init__(self, limit=6000):
        self._d = {}
        self.limit = limit
        self.hits = 0
        self.misses = 0

    def get(self, path):
        try:
            key = _stat_key(path)
        except OSError:
            return None
        val = self._d.get(key)
        if val is None:
            self.misses += 1
        else:
            self.hits += 1
        return val

    def put(self, path, value):
        try:
            key = _stat_key(path)
        except OSError:
            return
        if len(self._d) >= self.limit:
            self._d.clear()          # 长驻服务扫很多模组时别把内存吃满
        self._d[key] = value

    def clear(self):
        self._d.clear()

    def stats(self):
        return {"hits": self.hits, "misses": self.misses, "size": len(self._d)}


# ---------------------------------------------------------------- 探针集合

class ProbeSet(frozenset):
    """一个会记录「被问过什么」的集合。

    check_file 对跨文件集合只会做三种操作：`x in s`、`len(s)` / `if s:`、以及遍历。
    这三种全部拦下来记录，就能精确知道它依赖了哪些答案。
    """

    def __new__(cls, data, name=""):
        o = super().__new__(cls, data)
        o.name = name
        o.probes = []
        return o

    def __contains__(self, item):
        ans = super().__contains__(item)
        self.probes.append(["in", item, ans])
        return ans

    def __len__(self):
        n = super().__len__()
        self.probes.append(["len", None, n])
        return n

    def __iter__(self):
        items = tuple(super().__iter__())
        self.probes.append(["all", None, digest(items)])
        return iter(items)

    # 集合运算会产生新集合，等于「整集合都依赖」，按遍历处理
    def _op(self, other):
        self.probes.append(["all", None, digest(tuple(self))])
        return super().__iter__()


def make_probe_sets(sets):
    """把 {名字: 集合} 包成 ProbeSet，返回 (probe_sets, 原始集合)。"""
    return {k: ProbeSet(v, k) for k, v in sets.items()}


def probes_ok(probes, current, digests):
    """重放记录下来的查询。全部答案一致才算命中。

    probes  上次记录的 {集合名: [[kind, arg, ans], ...]}
    current 本次的 {集合名: 普通 set}
    digests 本次各集合的内容摘要（整集合依赖用）
    """
    for name, plist in probes.items():
        s = current.get(name)
        if s is None:
            return False
        for kind, arg, ans in plist:
            if kind == "in":
                if (arg in s) != ans:
                    return False
            elif kind == "len":
                if len(s) != ans:
                    return False
            else:
                if digests.get(name) != ans:
                    return False
    return True


# ---------------------------------------------------------------- 二级：检查结果缓存

class IssueCache:
    """逐文件检查结果缓存，落盘持久化。

    条目结构（内存里）：
        {abs_path: {"mtime": int, "size": int, "scope": str, "ctx": str,
                    "issues": [[level, code, line, msg], ...],
                    "probes": {name: [[kind, arg, ans], ...]}}}
    """

    MAX_PROBES_PER_FILE = 400       # 探针太多的文件不缓存，避免缓存文件失控
    MAX_ENTRIES = 20000             # 扫过的文件多了就整体丢弃，不让缓存无限长大

    def __init__(self, data_sig="", enabled=True):
        self.enabled = bool(enabled) and cache_enabled()
        self.data_sig = data_sig
        self.entries = {}
        self.hits = 0
        self.misses = 0
        self.skipped = 0
        self._dirty = False
        self.path = os.path.join(cache_root(), "issues.json.z") if self.enabled else None
        if self.enabled:
            self._load()

    # -- 存取 --------------------------------------------------------

    def _load(self):
        if not self.path or not os.path.isfile(self.path):
            return
        try:
            with io.open(self.path, "rb") as fh:
                blob = zlib.decompress(fh.read())
            raw = json.loads(blob.decode("utf-8"))
        except (OSError, ValueError, zlib.error):
            return
        if raw.get("version") != CACHE_VERSION:
            return
        if raw.get("data") != self.data_sig:
            return                     # 规则或数据表变了，整份作废
        got = raw.get("files")
        if isinstance(got, dict):
            self.entries = got

    def save(self):
        if not self.enabled or not self.path or not self._dirty:
            return False
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            payload = {"version": CACHE_VERSION, "data": self.data_sig,
                       "files": self.entries}
            blob = zlib.compress(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                6)
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path), suffix=".tmp")
            os.close(fd)
            with io.open(tmp, "wb") as fh:
                fh.write(blob)
            os.replace(tmp, self.path)     # 原子替换，避免半截文件
            self._dirty = False
            return True
        except OSError:
            return False

    # -- 查询 --------------------------------------------------------

    def lookup(self, path, scope, ctx, current_sets, digests):
        """命中返回 issues 列表（Issue 由调用方还原），否则 None。"""
        if not self.enabled:
            return None
        ent = self.entries.get(os.path.abspath(path))
        if not ent:
            self.misses += 1
            return None
        try:
            _p, mtime, size = _stat_key(path)
        except OSError:
            self.misses += 1
            return None
        if ent.get("mtime") != mtime or ent.get("size") != size:
            self.misses += 1
            return None
        if ent.get("scope") != scope or ent.get("ctx") != ctx:
            self.misses += 1
            return None
        if not probes_ok(ent.get("probes") or {}, current_sets, digests):
            self.misses += 1
            return None
        self.hits += 1
        return ent.get("issues") or []

    def store(self, path, scope, ctx, issues, probes):
        if not self.enabled:
            return
        if sum(len(v) for v in probes.values()) > self.MAX_PROBES_PER_FILE:
            self.skipped += 1
            return
        if len(self.entries) >= self.MAX_ENTRIES:
            self.entries.clear()
        try:
            _p, mtime, size = _stat_key(path)
        except OSError:
            return
        self.entries[os.path.abspath(path)] = {
            "mtime": mtime, "size": size, "scope": scope, "ctx": ctx,
            "issues": [[i.level, i.code, i.line, i.msg] for i in issues],
            "probes": {k: v for k, v in probes.items() if v},
        }
        self._dirty = True

    def stats(self):
        return {"enabled": self.enabled, "hits": self.hits, "misses": self.misses,
                "reused_files": self.hits, "skipped": self.skipped,
                "cached_entries": len(self.entries)}
