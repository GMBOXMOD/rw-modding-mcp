# -*- coding: utf-8 -*-
"""数据层：路径解析 + 惰性单例。

设计要点
--------
1. 所有路径都不依赖 cwd —— 服务进程的 cwd 由宿主决定，不可信。
2. 三个数据源（CSV / 中文表 / jar）解析一次约 150ms，用单例缓存；
   用 mtime 做失效判断（3 次 stat，约 10 微秒）。
3. Java 源码索引单独懒加载：1,698 个文件约 1 秒。**不做 mtime 失效**，
   因为每次查询要 stat 1,698 次，比直接重启服务还贵。重新反编译后重启即可。
"""

import io
import os
import sys
import threading

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLS = os.path.dirname(_HERE)
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import rw_lint  # noqa: E402  （必须先补 sys.path）

# 默认的游戏安装路径；可用 RW_GAME_JAR 覆盖
DEFAULT_JAR = r"D:\steam\steamapps\common\Rusted Warfare\game-lib.jar"


def _resolve_root():
    """项目根：环境变量 -> 从本文件上溯找 tools/rw_lint.py -> 硬编码兜底。"""
    env = os.environ.get("RW_PROJECT_ROOT")
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    d = _HERE
    for _ in range(5):
        if os.path.isfile(os.path.join(d, "tools", "rw_lint.py")):
            return d
        d = os.path.dirname(d)
    return os.path.dirname(_TOOLS)


ROOT = _resolve_root()
CSV_PATH = os.environ.get("RW_CSV") or rw_lint.find_asset("官方代码表（Modding References）.csv")
CN_PATH = os.environ.get("RW_CN") or rw_lint.find_asset("单位代码表Modding API Reference.txt")
JAR_PATH = os.environ.get("RW_GAME_JAR") or (DEFAULT_JAR if os.path.isfile(DEFAULT_JAR) else None)
JAVA_SRC = os.environ.get("RW_JAVA_SRC") or os.path.join(ROOT, "tools", "jar", "src")


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


class Dataset(object):
    __slots__ = ("sig", "csv_rows", "csv_keys", "cn_entries", "cn_keys",
                 "cn_canon", "key_families", "canon", "known", "jar_keys", "spellings")

    def __init__(self):
        self.sig = None
        self.csv_rows = {}
        self.csv_keys = {}
        self.cn_entries = {}
        self.cn_keys = {}
        self.cn_canon = {}
        self.key_families = {}
        self.canon = {}
        self.known = set()
        self.jar_keys = set()
        self.spellings = []


def _build(sig):
    ds = Dataset()
    ds.sig = sig

    ds.csv_rows = rw_lint.load_csv_rows(CSV_PATH)
    ds.csv_keys = rw_lint.load_csv_keys(CSV_PATH)
    ds.cn_entries = rw_lint.load_cn_entries(CN_PATH)
    ds.cn_keys = rw_lint.load_cn_keys(CN_PATH)
    ds.cn_canon = rw_lint.load_cn_canon(CN_PATH)
    ds.key_families = rw_lint.load_key_families(CN_PATH)
    ds.canon = rw_lint.build_canon(ds.csv_keys, ds.cn_canon)
    ds.known = rw_lint.expand_lang_keys(set(ds.csv_keys) | set(ds.cn_keys))
    ds.known |= {"repeatconditional", "extratriggeractions", "islockedmessage",
                 "cannotplacemessage", "customvalue", "preferences"}
    if JAR_PATH:
        try:
            ds.jar_keys = rw_lint.load_jar_keys(JAR_PATH)
        except Exception:
            ds.jar_keys = set()

    # 所有出现过的拼写，供 difflib 纠错
    seen = set()
    for src in (ds.csv_rows, ds.cn_entries):
        for bucket in src.values():
            for item in bucket:
                sp = item.get("spelling")
                if sp:
                    seen.add(sp)
    seen |= set(ds.canon.values()) if isinstance(ds.canon, dict) else set()
    seen |= {k for k in ds.known if k}
    ds.spellings = sorted(seen)
    return ds


_lock = threading.Lock()
_ds = None


def get_dataset(force=False):
    global _ds
    sig = (_mtime(CSV_PATH), _mtime(CN_PATH), _mtime(JAR_PATH) if JAR_PATH else 0.0)
    with _lock:
        if force or _ds is None or _ds.sig != sig:
            _ds = _build(sig)
        return _ds


# ---- Java 源码索引（独立懒加载） ----
_java_lock = threading.Lock()
_java_lines = None


def get_java_lines():
    """[(relpath_forward_slash, lineno, text)]，按 (path, lineno) 排序。"""
    global _java_lines
    with _java_lock:
        if _java_lines is not None:
            return _java_lines
        rows = []
        for dirpath, _dirnames, filenames in os.walk(JAVA_SRC):
            for fn in filenames:
                if not fn.endswith(".java"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, JAVA_SRC).replace("\\", "/")
                try:
                    text = io.open(full, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                for i, line in enumerate(text.split("\n"), 1):
                    rows.append((rel, i, line))
        rows.sort(key=lambda r: (r[0], r[1]))
        _java_lines = rows
        return _java_lines


def describe():
    """自检 / 排错用：当前解析到的路径与规模。"""
    ds = get_dataset()
    return {
        "root": ROOT,
        "csv": CSV_PATH,
        "cn": CN_PATH,
        "jar": JAR_PATH,
        "java_src": JAVA_SRC,
        "counts": {
            "csv_rows": len(ds.csv_rows),
            "csv_keys": len(ds.csv_keys),
            "cn_entries": len(ds.cn_entries),
            "cn_keys": len(ds.cn_keys),
            "key_families": len(ds.key_families),
            "jar_keys": len(ds.jar_keys),
            "known": len(ds.known),
            "spellings": len(ds.spellings),
        },
    }
