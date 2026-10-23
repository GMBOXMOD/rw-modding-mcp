#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rw_lint.py —— 铁锈战争模组「写后验证」诊断入口

luke 语最大的坑是**静默失效**：键名拼错、大小写错、用了不存在的键，
游戏都不报错，只是那行配置悄悄不生效。这个工具在写完代码后跑一遍，
把这些"看不见的错"揪出来。

用法
----
    # 校验单个文件
    python tools/rw_lint.py "mymod/units/mytank.ini"

    # 校验整个模组目录
    python tools/rw_lint.py "mymod" --jar "D:/steam/steamapps/common/Rusted Warfare/game-lib.jar"

    # 只输出错误，不看警告
    python tools/rw_lint.py "mymod" --quiet

    # 机器可读
    python tools/rw_lint.py "mymod" --json

    # 打印速查表（事件名 / 函数 / 枚举 / 内存类型 / 硬限制），不用翻源码
    python tools/rw_lint.py --ref

退出码
------
    0 = 无错误（可能仍有警告）
    1 = 有错误

检查项
------
  E  错误（几乎肯定是 bug）
    E01  键名大小写/拼写错误（能模糊匹配到正确的键）
    E02  全角冒号 `：` 当半角冒号用
    E03  `\"\"\"` 数量为奇数（会吞掉后面整段配置）
    E04  `${` 与 `}` 不配对
    E05  重复的节头
    E06  `projectile:` / `turret:` 引用了不存在的节
    E07  文件带 BOM
    E10  autoTriggerOnEvent 的事件名不存在（18 个合法值）
    E11  [hiddenAction_*] 里写了 isVisible（加载期会抛异常）
    E12  addActionCooldownApplyToActions 缺 addActionCooldownTime
    E13  @memory 的类型不合法
    E14  canAttack: true 但缺 canAttackFlyingUnits / LandUnits / UnderwaterUnits

  W  警告（可能是 bug，也可能是刻意的）
    W01  未知键（三份资料都查不到）
    W02  双语的基键 / `_zh` 只写了一侧
    W03  用了 1.15p9+ 的键（decal 等）却没声明 minVersion
    W04  键的版本高于声明的 minVersion
    W05  `copyFrom` / `alsoTriggerAction` 引用了不存在的节
    W06  节里没有任何键
"""

import os
import re
import io
import sys
import csv
import json
import argparse
import time


def _load_cache_module():
    """加载同目录的 rw_cache.py。

    不用 `import rw_cache`：本文件经常被 importlib 从任意 cwd 直接加载
    （skill/scripts/ 下就是这种用法），那时 sys.path 里没有 tools/。
    """
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "rw_cache.py")
    if not os.path.isfile(path):
        return None
    try:
        spec = importlib.util.spec_from_file_location("rw_lint_cache", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:                                        # noqa: BLE001
        return None


rw_cache = _load_cache_module()
_PARSE_MEMO = rw_cache.ParseMemo() if rw_cache else None

# 引擎按**前缀**动态消费的键族。
# 反编译确认：ag.java 里 `for (String s : ab2.e("animation_"))`、
# bh.java 里 `ab2.k(string2, "mutator")` —— 这些键名不是固定字面量，
# 代码表里也查不到具体拼写，按前缀整族放行。
KEY_PREFIX_FAMILIES = (
    "animation_", "mutator",
    # 动画部件名：f.java 里是 string3.startsWith("body") 这种判断，
    # 所以 body_0s / leg_1_3 之类的具体拼写不会出现在代码表里。
    # 带下划线是为了不误吞 turretRange 这类真键。
    "body_", "leg_", "arm_", "turret_",
)

# 中文表里带占位符的模板键，例如 builtFrom_#_name、action_#_[actionKey]
CN_TEMPLATE_RX = re.compile(r"^[A-U]-(?:[a-z]+-)?\d*：([A-Za-z_@][^（(]*#[^（(]*)[（(]")


def _template_to_rx(tpl):
    """把模板键转成正则：`#` -> 序号，`[xxx]` -> 任意名字。"""
    parts = []
    i = 0
    for m in re.finditer(r"#|\[[^\]]*\]", tpl):
        parts.append(re.escape(tpl[i:m.start()]))
        parts.append(r"\d+" if m.group(0) == "#" else r".+")
        i = m.end()
    parts.append(re.escape(tpl[i:]))
    return re.compile("^" + "".join(parts) + "$", re.IGNORECASE)


def load_key_templates(path):
    """中文表 -> 模板键的正则列表。

    例：builtFrom_#_name -> ^builtfrom_数字+_name$
    带占位符的键在代码表里只有模板形式，具体拼写（builtFrom_1_name）查不到，
    所以必须靠模板匹配，否则会被当成未知键。
    """
    out = []
    if not path or not os.path.isfile(path):
        return out
    seen = set()
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    for line in lines:
        m = CN_TEMPLATE_RX.match(line.strip())
        if not m:
            continue
        tpl = m.group(1).strip()
        if tpl in seen:
            continue
        seen.add(tpl)
        try:
            out.append(_template_to_rx(tpl))
        except re.error:
            continue
    return out


def load_text_keys(path):
    """一行一个键名的补充表（小写，忽略 # 注释行）。

    用来补代码表没收录的键 —— 从 game-lib.jar 常量池导出的那份就是。
    """
    if not path or not os.path.isfile(path):
        return set()
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        return {ln.strip().lower() for ln in fh
                if ln.strip() and not ln.lstrip().startswith("#")}


def is_family_key(key_lower, templates):
    """这个键是不是属于某个动态键族（前缀族或模板族）。"""
    for p in KEY_PREFIX_FAMILIES:
        if key_lower.startswith(p) and len(key_lower) > len(p):
            return True
    for rx in templates or ():
        if rx.match(key_lower):
            return True
    return False


# ---------------------------------------------------------------- 常量

# 不需要当成"键"来校验的指令行前缀
DIRECTIVE = ("@memory", "@global", "@define", "@copyFromSection", "@copyFrom_skipThisSection")

# 这些基键要求中英成对
BILINGUAL_BASES = (
    "displayText", "displayDescription",
    "text", "description",
    "showMessageToPlayer", "showMessageToAllPlayers",
    "isLockedMessage", "cannotPlaceMessage",
)

# 出现这些键就意味着需要 decal 能力（1.15p9+）
DECAL_MARKERS = ("layer", "frame", "basePosition", "imageStack", "stack_indexStart",
                 "alpha", "drawLineTo", "imageScaleX", "imageScaleY")

VERSION_ORDER = ["1.13", "1.13.3", "1.14", "1.15", "1.15p9", "1.15p11"]

# 值枚举：这几个键的取值是封闭集合，填错静默失效（按钮不出现 / 单位不动 / 贴花消失）
ENUM_VALUES = {
    "displaytype": ["none", "rally", "upgrade", "queueUnit", "building",
                    "action", "infoOnly", "infoOnlyNoBox", "infoOnlyStockpile"],
    "movementtype": ["NONE", "LAND", "BUILDING", "AIR", "WATER", "HOVER",
                     "OVER_CLIFF", "OVER_CLIFF_WATER"],
    "layer": ["shadow", "beforeBody", "afterBody", "onTop", "beforeUI", "inactive"],
}

# 只接受纯数字的键：值里出现字母就说明填错了
# 注意：buildSpeed 是 time 类型（可写 `3s`），不在这个集合里
PLAIN_NUMERIC = {"maxhp", "mass", "radius", "nanorange", "techlevel",
                 "maxattackrange", "fogofwarsightrange", "nanorepairspeed",
                 "nanobuildspeed", "total_frames", "frame_width", "frame_height"}

# ---- 以下四张表全部来自反编译源码，不是文档推测 ----

# autoTriggerOnEvent 的合法事件名（af 枚举的 name()，共 18 个）
EVENTS = {
    "created", "completeAndActive", "destroyed", "killedAnyUnit",
    "queuedUnitFinished", "queueItemAdded", "queueItemCancelled",
    "teleported", "touchTargetSuccess", "newWaypointGivenByPlayer",
    "teamChanged", "transportingNewUnit", "transportUnloadedOrRemovedUnit",
    "tookDamage", "enteredTransport", "leftTransport", "newMessage",
    "attachmentRemoved",
}

# 逻辑函数全集（LogicBoolean 里 addBooleanType 注册的 27 个）。
# 注意：没有 abs / floor / round / pow / tan，sqrt 叫 squareRoot。
FUNCS = {
    "memory", "readUnitMemory", "eventData", "playername", "teamname",
    "debug", "debugPassthrough", "select", "str", "substring",
    "lowercase", "uppercase", "int", "rnd", "max", "min", "length",
    "squareRoot", "distanceSquared", "cos", "sin", "distance",
    "direction", "distanceBetweenSquared", "distanceBetween",
    "directionBetween", "createMarker",
}

# 大家容易凭直觉写、但引擎里确实没有的函数
NONEXISTENT_FUNCS = {"abs", "floor", "round", "pow", "atan2", "asin", "acos",
                     "ceil", "log", "exp", "mod", "clamp", "lerp"}

# `%{}` 里还有另一套数学表达式解析器（custom/f/b$1），额外支持 sqrt / tan，^ 表示乘方
MATH_EXTRA = {"sqrt", "tan"}

# @memory 允许的类型
MEM_TYPES = {"boolean", "bool", "float", "number", "unit", "string", "text"}

# 按钮类文本键：必须是运行期 %{}，写成载入期 ${} 会永远显示初始值
ACTION_TEXT_KEYS = {"text", "text_zh", "description", "description_zh"}

# 节名 → 中文代码表的章节字母（A=core、B=canBuild…U=music）
# 用来判断"这个键是否属于这个节"
SECTION_FAMILY_RULES = [
    ("global_resource", "O"), ("resource", "P"),
    ("hiddenaction", "M"), ("action", "M"),
    ("canbuild", "B"), ("placementrule", "N"),
    ("projectile", "F"), ("turret", "E"),
    ("attachment", "J"), ("animation", "L"),
    ("effect", "K"), ("decal", "Q"), ("template", "R"),
    ("comment", "S"), ("graphics", "C"), ("movement", "G"),
    ("attack", "D"), ("ai", "H"), ("core", "A"),
    ("leg_", "I"), ("arm_", "I"), ("mod", "T"), ("music", "U"),
]
# 这些节是"什么都能写"的容器，不参与归属校验
FAMILY_EXEMPT = {"R", "S", "T", "U"}
# 这些章节的键本来就会被别的节复用，不强制校验
FAMILY_LOOSE = {"A", "B", "M"}

FAMILY_NAMES = {
    "A": "core 核心", "B": "canBuild 可建造", "C": "graphics 图像", "D": "attack 攻击",
    "E": "turret 炮塔", "F": "projectile 抛射体", "G": "movement 运动", "H": "ai AI",
    "I": "leg/arm 腿脚胳膊", "J": "attachment 附属", "K": "effect 效果", "L": "animation 动画",
    "M": "action 行动", "N": "placementRule 放置规则", "O": "global_resource 全局资源",
    "P": "resource 局部资源", "Q": "decal 贴花", "R": "template 模板", "S": "comment 注释",
    "T": "mod 模组", "U": "music 音乐",
}

# [canBuild_N] name 里可以写内置指令，它们不是单位，别误报
BUILTIN_BUILD_ENTRIES = {"reclaim", "repair", "setrally", "sell", "upgrade",
                         "attack", "move", "stop", "guard", "patrol", "load",
                         "unload", "loadinto", "loadup"}


def split_top(text, sep=","):
    """按顶层分隔符切分，忽略括号 / 引号里的分隔符。"""
    out, buf, depth, quote = [], [], 0, None
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == sep and depth == 0:
            out.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    out.append("".join(buf))
    return out


def strip_runtime_blocks(text):
    """去掉 %{...}（运行期）块，返回剩下的载入期部分。

    `%{select( memory.x[${section.y}], ...)}` 这种写法里，
    外层的 %{ } 是运行期、里层的 ${ } 是载入期常量 —— 合法。
    所以要同时跟踪两种括号，不能只数 `}`。"""
    out = []
    stack = []
    i = 0
    while i < len(text):
        if text.startswith("%{", i):
            stack.append("t")
            i += 2
            continue
        if text.startswith("${", i):
            if "t" not in stack:
                out.append("${")
            stack.append("v")
            i += 2
            continue
        if text[i] == "}":
            if stack:
                stack.pop()
            i += 1
            continue
        if "t" not in stack:
            out.append(text[i])
        i += 1
    return "".join(out)


def ver_key(v):
    """把版本串转成可比较的元组。"""
    v = (v or "").strip().lower()
    v = re.sub(r"^[vV]", "", v).replace("p", ".")
    if not v:
        return (0,)
    parts = []
    for p in re.split(r"[.\-]", v):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


# ---------------------------------------------------------------- 资料加载

def load_csv_keys(path):
    """官方 CSV -> {小写键名: (版本, 类型, 描述)}"""
    out = {}
    if not path or not os.path.isfile(path):
        return out
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.reader(fh):
            if len(row) < 4:
                continue
            code = row[1].strip()
            if not code:
                continue
            base = re.sub(r"\(.*$", "", code.rstrip(":").strip())
            base = base.replace("{LANG}", "").strip()
            if base and base.lower() not in out:
                out[base.lower()] = (row[0].strip(), row[2].strip(), row[3].strip(), base)
    return out


def build_canon(csv_keys, cn_canon):
    """小写键名 -> 官方原始拼写，用来抓大小写错误。"""
    canon = {}
    for k, v in csv_keys.items():
        if len(v) >= 4 and v[3]:
            canon[k] = v[3]
    for k, v in cn_canon.items():
        canon.setdefault(k, v)
    return canon


def expand_lang_keys(known):
    """把 `text` / `displayText` 这类基键展开成 `text_zh` / `text_es` 等。
    官方文档用 `{LANG}` 占位，实际写 `_zh`（ISO 639-1），所以必须放行。"""
    lang_bases = {
        "text", "description", "displaytext", "displaydescription",
        "showmessagetoplayer", "showmessageforallplayers",
        "showmessagetoallenemyplayers", "islocketmessage",
        "cannotplacemessage", "name", "displayname",
    }
    extra = set()
    for k in list(known):
        if k in lang_bases:
            for lang in ("zh", "es", "fr", "de", "ru", "ja", "ko", "pt", "it",
                         "pl", "tr", "vi", "th", "id", "fil", "uk", "cs", "nl"):
                extra.add(f"{k}_{lang}")
    return known | extra


def load_cn_keys(path):
    """中文离线代码表 -> {小写键名: 释义}"""
    out = {}
    if not path or not os.path.isfile(path):
        return out
    for line in io.open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"^[A-Z]-[a-z]+-?\d*：([A-Za-z_@][\w@]*)[（(]([^）)]*)[）)]", line.strip())
        if m:
            out[m.group(1).lower()] = m.group(2)
    return out


def load_cn_canon(path):
    """中文表里键的原始拼写。"""
    out = {}
    if not path or not os.path.isfile(path):
        return out
    for line in io.open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"^[A-Z]-[a-z]+-?\d*：([A-Za-z_@][\w@]*)[（(]", line.strip())
        if m:
            out.setdefault(m.group(1).lower(), m.group(1))
    return out


def load_key_families(cn_path):
    """中文代码表 -> {小写键名: {章节字母}}。章节字母即 section 归属。"""
    out = {}
    if not cn_path or not os.path.isfile(cn_path):
        return out
    rx = re.compile(r"^([A-U])-(?:[a-z]+-)?\d*：([A-Za-z_@][\w@]*)[（(]")
    for line in io.open(cn_path, encoding="utf-8", errors="replace"):
        m = rx.match(line.strip())
        if m:
            out.setdefault(m.group(2).lower(), set()).add(m.group(1))
    return out


def section_family(sec):
    """节名 -> 章节字母；认不出返回 None。"""
    if not sec:
        return None
    low = sec.lower()
    for prefix, fam in SECTION_FAMILY_RULES:
        if low.startswith(prefix):
            return fam
    return None


def load_jar_keys(jar_path):
    """从 game-lib.jar 常量池里捞候选键名（可选，需 --jar）"""
    out = set()
    if not jar_path or not os.path.isfile(jar_path):
        return out
    import struct
    import zipfile

    def utf8s(data):
        if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
            return []
        (cnt,) = struct.unpack(">H", data[8:10])
        res, i, n = [], 10, 1
        while n < cnt and i < len(data):
            tag = data[i]
            i += 1
            if tag == 1:
                if i + 2 > len(data):
                    break
                (ln,) = struct.unpack(">H", data[i:i + 2])
                i += 2
                res.append(data[i:i + ln].decode("utf-8", "replace"))
                i += ln
            elif tag in (7, 8, 16, 19, 20):
                i += 2
            elif tag == 15:
                i += 3
            elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
                i += 4
            elif tag in (5, 6):
                i += 8
                n += 1
            else:
                break
            n += 1
        return res

    with zipfile.ZipFile(jar_path) as z:
        for name in z.namelist():
            if not (name.endswith(".class") and
                    name.startswith("com/corrodinggames/rts/game/units/custom/")):
                continue
            for s in utf8s(z.read(name)):
                if re.match(r"^@?[a-z][A-Za-z0-9_]{2,40}$", s):
                    out.add(s.rstrip(":").lower())
    return out


# ---------------------------------------------------------------- 解析

class Issue:
    def __init__(self, level, code, path, line, msg):
        self.level, self.code, self.path, self.line, self.msg = level, code, path, line, msg

    def __str__(self):
        tag = "E" if self.level == "error" else "W"
        return f"{self.path}:{self.line}: [{tag}{self.code}] {self.msg}"

    def as_dict(self):
        return dict(level=self.level, code=self.code, file=self.path,
                    line=self.line, message=self.msg)


def parse_file(path, use_cache=True):
    """返回 (sections, entries, raw_lines)。entries = [(line_no, key, value, section)]

    带进程内记忆：按 (绝对路径, mtime_ns, 大小) 命中。
    check_file 内部也要 parse 一次，两处共用同一份结果 ——
    否则每个文件会被解析两遍（实测占整个扫描时间的 21%）。
    """
    if use_cache and _PARSE_MEMO is not None:
        hit = _PARSE_MEMO.get(path)
        if hit is not None:
            return hit
    raw = io.open(path, "rb").read()
    text = raw.decode("utf-8-sig", "replace")
    lines = text.split("\n")

    sections = []          # [(line_no, name)]
    entries = []           # [(line_no, key, value, section)]
    directives = {}        # {section: 指令行数}（@memory / @global 也算内容）
    defines = set()        # 本文件里 @define / @global 声明的名字，它们是可写的键
    cur = None
    in_block = False       # 是否在 """ 块内
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()

        # 注释行先跳过，再数引号 —— 注释里写 `"""` 不该影响块判定
        # （引擎也是先判注释再判块，见 ab.java:172）
        if not in_block and stripped.startswith("#"):
            continue

        # 统计 """ 出现次数（同一行可能开也可能闭）
        q = stripped.count('"""')
        if q % 2 == 1:
            # `@define x:"""` 这种形式：块开始了，但名字照样要登记
            dm0 = re.match(r"^@(?:define|global)\s+([A-Za-z_][\w]*)", stripped)
            if dm0 and not in_block:
                defines.add(dm0.group(1).lower())
            # `key: """` 这种形式：块虽然开始了，但这个键本身是内容
            m0 = re.match(r"^([A-Za-z_@][\w@]*)\s*[:=]\s*\"\"\"", stripped)
            if m0 and not in_block:
                entries.append((idx, m0.group(1), '"""', cur))
            in_block = not in_block
            continue
        if in_block:
            continue
        if q and q % 2 == 0 and q > 0:
            continue

        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("[") and stripped.endswith("]"):
            name = stripped[1:-1].strip()
            sections.append((idx, name))
            cur = name
            continue

        if stripped.startswith(DIRECTIVE):
            directives[cur] = directives.get(cur, 0) + 1
            dm = re.match(r"^@(?:define|global)\s+([A-Za-z_][\w]*)", stripped)
            if dm:
                defines.add(dm.group(1).lower())
            continue

        m = re.match(r"^([A-Za-z_@][\w@]*)\s*([:＝：=])\s*(.*)$", stripped)
        if m:
            entries.append((idx, m.group(1), m.group(3), cur))
    result = (sections, entries, lines, raw, directives, defines)
    if use_cache and _PARSE_MEMO is not None:
        _PARSE_MEMO.put(path, result)
    return result


# ---------------------------------------------------------------- 检查

def check_file(path, known, csv_keys, min_version, all_sections, mod_root,
               global_defines=frozenset(), referenced=frozenset(), canon=None,
               unit_names=frozenset(), key_families=None, has_units_template=False,
               key_templates=(), parsed=None):
    issues = []
    sections, entries, lines, raw, directives, defines = parsed or parse_file(path)

    # E07 BOM
    if raw[:3] == b"\xef\xbb\xbf":
        issues.append(Issue("error", "07", path, 1, "文件带 UTF-8 BOM，部分解析器会把首行键名读错"))

    # E03 """ 数量
    n_q = 0
    _inb = False
    for l in lines:
        _st = l.strip()
        if not _inb and _st.startswith("#"):
            continue
        _c = _st.count('"""')
        if _c % 2 == 1:
            _inb = not _inb
        n_q += _c
    if n_q % 2:
        issues.append(Issue("error", "03", path, 1,
                            f'`"""` 出现 {n_q} 次（奇数）。它会吞掉后面整段配置，必须成对'))

    # E02 全角冒号 / E04 花括号
    depth = 0
    in_block = False
    for idx, line in enumerate(lines, 1):
        s = line.strip()
        # 跟踪 """ 块：块内的内容是数据，不参与语法检查
        q = s.count('"""')
        if q % 2 == 1:
            in_block = not in_block
            continue
        if in_block or q:
            continue
        if not s or s.startswith("#"):
            continue
        if re.match(r"^[A-Za-z_@][\w@]*\s*：", s):
            issues.append(Issue("error", "02", path, idx,
                                "用了全角冒号 `：`，必须改成半角 `:`"))
        # 用括号栈扫描，正确处理 %{ ... ${...} ... } 这种嵌套
        stack = []
        i = 0
        while i < len(s):
            if s.startswith("${", i):
                stack.append("v")
                i += 2
            elif s.startswith("%{", i):
                stack.append("t")
                i += 2
            elif s[i] == "}":
                if stack:
                    kind = stack.pop()
                    if kind == "v":
                        depth -= 1
                else:
                    issues.append(Issue("error", "04", path, idx, "多余的 `}`"))
                    break
                i += 1
            else:
                i += 1
        for kind in stack:
            if kind == "v":
                depth += 1
        if depth < 0:
            depth = 0
    if depth != 0:
        issues.append(Issue("error", "04", path, len(lines), f"`${{` 未闭合（差 {depth} 个）"))

    # E05 重复节头
    seen = {}
    for ln, name in sections:
        if name in seen:
            issues.append(Issue("warning", "07", path, ln,
                                f"节 `[{name}]` 重复（首次出现于第 {seen[name]} 行）；键会合并/覆盖，确认是否有意"))
        else:
            seen[name] = ln

    # W06 空节
    sec_keys = {}
    for ln, key, val, sec in entries:
        sec_keys.setdefault(sec, 0)
        sec_keys[sec] += 1

    # E01 / W01 键名
    known = known | defines | set(global_defines)
    canon = canon or {}
    for ln, key, val, sec in entries:
        kl = key.lower()
        if kl in known:
            # 已知键：再核对一次大小写（luke 语区分大小写，写错静默失效）
            official = canon.get(kl)
            if official and official != key:
                issues.append(Issue("error", "01", path, ln,
                                    f"键名大小写错误：`{key}`，应为 `{official}`"))
            continue
        # 动态键族（animation_* / mutator* / builtFrom_#_name …）直接放行
        if is_family_key(kl, key_templates):
            continue
        # 尝试大小写纠正
        cands = [k for k in known if k.lower() == kl]
        if cands:
            issues.append(Issue("error", "01", path, ln,
                                f"键名大小写错误：`{key}`，应为 `{cands[0]}`（luke 语区分大小写，写错会静默失效）"))
            continue
        # 模糊匹配（去掉下划线/数字后比较）
        norm = re.sub(r"[_0-9]", "", kl)
        fuzzy = [k for k in known if re.sub(r"[_0-9]", "", k.lower()) == norm]
        if fuzzy:
            issues.append(Issue("error", "01", path, ln,
                                f"键名疑似拼错：`{key}`，最接近 `{fuzzy[0]}`"))
            continue
        # 通用多语言后缀：`xxx_zh` / `xxx_es`，只要基键已知就合法
        m_lang = re.match(r"^(.+)_([a-z]{2})$", kl)
        if m_lang and m_lang.group(1) in known:
            continue
        if kl in referenced:
            continue        # 被 ${...} 读回来用 → 自定义键，合法
        issues.append(Issue("warning", "01", path, ln,
                            f"未知键 `{key}`（三份资料均未收录，且没被 ${{}} 引用过），确认是否拼错"))

    # W08 同一节里重复写同一个键（后者静默覆盖前者）
    seen_keys = {}
    for ln, key, val, sec in entries:
        sig = (sec, key.lower())
        if sig in seen_keys:
            issues.append(Issue("warning", "08", path, ln,
                                f"键 `{key}` 在节 `[{sec}]` 里重复（首次在第 {seen_keys[sig]} 行），后者会覆盖前者"))
        else:
            seen_keys[sig] = ln

    # E08 值枚举错（displayType / movementType / layer）
    import difflib
    for ln, key, val, sec in entries:
        allowed = ENUM_VALUES.get(key.lower())
        if not allowed:
            continue
        v = val.strip()
        if not v or v.startswith("if ") or "${" in v or "%{" in v:
            continue
        if v.lower() in {a.lower() for a in allowed}:
            continue
        near = difflib.get_close_matches(v, allowed, n=1, cutoff=0.5)
        hint = f"，最接近 `{near[0]}`" if near else ""
        issues.append(Issue("error", "08", path, ln,
                            f"`{key}` 的取值 `{v}` 不合法{hint}；可选：{' / '.join(allowed)}"))

    # E09 纯数字键填了非数字
    for ln, key, val, sec in entries:
        if key.lower() not in PLAIN_NUMERIC:
            continue
        v = val.strip()
        if not v or "${" in v or "%{" in v or v.upper() == "IGNORE":
            continue
        if re.fullmatch(r"[-+]?\d+(\.\d+)?", v):
            continue
        issues.append(Issue("error", "09", path, ln,
                            f"`{key}` 需要数字，但写的是 `{v}`"))

    # W09 ${...} 引用了未定义的变量
    # 依据：不带点、不带括号的 `${x}` 只能是 @global / @define 声明的名字
    declared = set(defines) | {d.lower() for d in global_defines}
    _seen_w09 = set()
    for idx, line in enumerate(lines, 1):
        st = line.strip()
        if not st or st.startswith("#"):
            continue
        for expr in re.findall(r"\$\{([^}]*)\}", line):
            e = expr.strip()
            if not e or "." in e or "(" in e or " " in e:
                continue
            if not re.fullmatch(r"[A-Za-z_][\w]*", e):
                continue
            if e.lower() in declared:
                continue
            if (idx, e) in _seen_w09:
                continue
            _seen_w09.add((idx, e))
            issues.append(Issue("warning", "09", path, idx,
                                f"`${{{e}}}` 在本次扫描范围内没找到 @global / @define 声明（若确实没定义，游戏里会静默变成空值）"))

    # W10 插值用反了
    for ln, key, val, sec in entries:
        if not sec:
            continue
        v = val.strip()
        if sec.startswith("action") and key in ACTION_TEXT_KEYS and "${" in strip_runtime_blocks(v):
            issues.append(Issue("warning", "10", path, ln,
                                f"按钮文本 `{key}` 用了载入期 `${{}}`，应改用运行期 `%{{}}`，否则永远显示初始值"))
        if key in ("setUnitMemory", "updateUnitMemory") and "%{" in v:
            issues.append(Issue("warning", "10", path, ln,
                                f"`{key}` 里出现运行期 `%{{}}`，这里只认载入期 `${{}}` 和字面量"))

    # W11 [canBuild_*] 的 name 指向了不存在的单位
    if unit_names:
        for ln, key, val, sec in entries:
            if not (sec or "").startswith("canBuild") or key != "name":
                continue
            for nm in re.split(r"[,;]", val):
                nm = nm.strip()
                if (nm and not nm.startswith("${")
                        and nm.lower() not in unit_names
                        and nm.lower() not in BUILTIN_BUILD_ENTRIES):
                    issues.append(Issue("warning", "11", path, ln,
                                        f"`[canBuild] name: {nm}` 在本模组里找不到同名单位（`[core] name:` 或 altNames）"))

    # W12 键放错节（这个键不属于这个节）
    key_families = key_families or {}
    for ln, key, val, sec in entries:
        if not sec:
            continue
        sec_fam = section_family(sec)
        if not sec_fam or sec_fam in FAMILY_EXEMPT:
            continue
        kfams = key_families.get(key.lower())
        if not kfams or len(kfams) != 1:
            continue                      # 多章节共用的键，不判
        only = next(iter(kfams))
        if only == sec_fam or only in FAMILY_LOOSE:
            continue
        issues.append(Issue("warning", "12", path, ln,
                            f"`{key}` 属于 `{only}` 章（{FAMILY_NAMES.get(only, only)}），"
                            f"却写在 `[{sec}]`（`{sec_fam}` 章）里，确认是否放错节"))

    # ---- 以下检查全部基于反编译源码确认的硬事实 ----

    # E10 事件名不在 18 个合法值里（写错就永远不触发，且不报错）
    for ln, key, val, sec in entries:
        if key != "autoTriggerOnEvent":
            continue
        for ev in split_top(val.strip()):
            ev = re.sub(r"\(.*$", "", ev).strip()
            if not ev or ev.startswith("${"):
                continue
            if ev not in EVENTS:
                near = difflib.get_close_matches(ev, sorted(EVENTS), n=1, cutoff=0.6)
                hint = f"，最接近 `{near[0]}`" if near else ""
                issues.append(Issue("error", "10", path, ln,
                                    f"事件名 `{ev}` 不存在{hint}；合法值见 `--ref`"))

    # E11 [hiddenAction_*] 里写 isVisible（非静态 false）→ 加载期抛异常
    for ln, key, val, sec in entries:
        if not (sec or "").lower().startswith("hiddenaction") or key != "isVisible":
            continue
        if val.strip().lower() not in ("false", "0", "no"):
            issues.append(Issue("error", "11", path, ln,
                                "`[hiddenAction_*]` 里不能写 `isVisible`（除非静态 false）；"
                                "引擎会抛 \"isVisible doesn't make sense to use in hidden actions\""))

    # E12 addActionCooldownApplyToActions 缺 addActionCooldownTime
    by_sec = {}
    for ln, key, val, sec in entries:
        by_sec.setdefault(sec, {})[key.lower()] = (ln, val)
    for sec, kv in by_sec.items():
        if "addactioncooldownapplytoactions" in kv and "addactioncooldowntime" not in kv:
            issues.append(Issue("error", "12", path, kv["addactioncooldownapplytoactions"][0],
                                "`addActionCooldownApplyToActions` 必须同时写 `addActionCooldownTime`，否则无效"))

        # W13 repeat 没有配对 alsoTriggerAction
        if "alsotriggeractionrepeat" in kv and "alsotriggeraction" not in kv:
            issues.append(Issue("warning", "13", path, kv["alsotriggeractionrepeat"][0],
                                "`alsoTriggerActionRepeat` 必须与 `alsoTriggerAction` 同节，否则完全无效"))

        # W14 repeat: 0 会把 alsoTriggerAction 整个取消
        if "alsotriggeractionrepeat" in kv:
            rln, rval = kv["alsotriggeractionrepeat"]
            if rval.strip() in ("0", "0.0"):
                issues.append(Issue("warning", "14", path, rln,
                                    "`alsoTriggerActionRepeat: 0` 不是「不重复」，而是把整个 `alsoTriggerAction` 取消"))

        # E14 canAttack: true 时三个目标类型键是必填（引擎不给默认值）
        # 但如果模组里有 all-units.template，这些键可能已经从那里继承了，
        # 不能只按"本节里有没有"来判断。
        if (not has_units_template
                and kv.get("canattack", (0, ""))[1].strip().lower() in ("true", "1", "yes")):
            need = [("canattackflyingunits", "canAttackFlyingUnits"),
                    ("canattacklandunits", "canAttackLandUnits"),
                    ("canattackunderwaterunits", "canAttackUnderwaterUnits")]
            miss = [disp for low, disp in need if low not in kv]
            if miss:
                issues.append(Issue("error", "14", path, kv["canattack"][0],
                                    f"`canAttack: true` 时必须同时写 {' 和 '.join(f'`{m}`' for m in miss)}"
                                    f"（引擎不给默认值，缺了加载期直接抛异常）"))

        # W15 alwaysSinglePress 三键缺一不可
        if "alwayssinglepress" in kv and kv["alwayssinglepress"][1].strip().lower() in ("true", "1", "yes"):
            pairs = [("canplayercancel", "canPlayerCancel"),
                     ("allowmultipleinqueue", "allowMultipleInQueue")]
            miss = [disp for low, disp in pairs
                    if kv.get(low, (0, ""))[1].strip().lower() not in ("false", "0", "no")]
            if miss:
                issues.append(Issue("warning", "15", path, kv["alwayssinglepress"][0],
                                    f"`alwaysSinglePress: true` 还需 {' 和 '.join(f'`{m}: false`' for m in miss)}，否则不生效"))

    # W16 用了不存在的逻辑函数
    # 扫两处：${} / %{} 表达式，以及 setUnitMemory / updateUnitMemory 的值
    exprs = []       # [(行号, 表达式文本)]
    for idx, line in enumerate(lines, 1):
        st = line.strip()
        if not st or st.startswith("#"):
            continue
        for e in re.findall(r"[\$%]\{([^}]*)\}", line):
            exprs.append((idx, e))
    for ln, key, val, sec in entries:
        if key in ("setUnitMemory", "updateUnitMemory"):
            exprs.append((ln, val))
    for idx, expr in exprs:
        if True:
            for m in re.finditer(r"(?<![.\w])([A-Za-z_][A-Za-z0-9_]*)\s*\(", expr):
                fn = m.group(1)
                if fn in FUNCS or fn in MATH_EXTRA or fn in ("if", "and", "or", "not"):
                    continue
                # 只报两类：① 确实不存在的常见函数 ② 疑似拼错全局函数
                # 其他一律放过 —— 单位上下文方法（nearestUnit / getOffsetRelative …）
                # 不在那 27 个全局函数里，写全名单只会不断漏。
                if fn in NONEXISTENT_FUNCS:
                    issues.append(Issue("warning", "16", path, idx,
                                        f"函数 `{fn}(` 不存在；共 27 个全局函数，见 `--ref`"
                                        f"（取绝对值用 `max(x, -x)`，开方用 `squareRoot`）"))
                    continue
                near = difflib.get_close_matches(fn, sorted(FUNCS), n=1, cutoff=0.85)
                if near and fn not in near:
                    issues.append(Issue("warning", "16", path, idx,
                                        f"函数 `{fn}(` 疑似拼错，是否想写 `{near[0]}`？"))

    # E15 @memory / @global / @define 行尾写了注释（会被当成值的一部分）
    for idx, line in enumerate(lines, 1):
        st = line.strip()
        if not re.match(r"^@(memory|global|define)\b", st):
            continue
        # 值里出现 " #" 就是行尾注释
        if re.search(r"\s#", st):
            issues.append(Issue("error", "15", path, idx,
                                "`@memory` / `@global` / `@define` 行尾不能写注释 —— "
                                "引擎不剥离行尾 `#`，会把它当成值的一部分（注释请独占一行）"))

    # E13 @memory 的类型不合法
    for idx, line in enumerate(lines, 1):
        m = re.match(r"^\s*@memory\s+([A-Za-z_][\w]*)\s*:\s*(\S+)", line)
        if not m:
            continue
        name, typ = m.group(1), m.group(2).rstrip("[]")
        if typ.lower() not in MEM_TYPES:
            issues.append(Issue("error", "13", path, idx,
                                f"`@memory {name}` 的类型 `{typ}` 不合法；"
                                f"可选：{' / '.join(sorted(MEM_TYPES))}（数组加 []）"))

    # W04 版本门槛（同一键只报一次，避免刷屏）
    reported = {}
    if min_version:
        mv = ver_key(min_version)
        for ln, key, val, sec in entries:
            info = csv_keys.get(key.lower())
            if not info or not info[0]:
                continue
            if ver_key(info[0]) > mv:
                need = info[0]
                bucket = reported.setdefault(need, [])
                if key not in bucket:
                    bucket.append(key)

    # W04 汇总输出（按版本合并，避免每个键刷一条）
    for need, keys in sorted(reported.items()):
        issues.append(Issue("warning", "04", path, 1,
                            f"有 {len(keys)} 个键需要 {need}，但 mod-info.txt 声明的是 minVersion: {min_version}"
                            f"（{'、'.join(keys[:6])}{' 等' if len(keys) > 6 else ''}）"))

    # W03 用了 decal 却没声明 minVersion
    if not min_version:
        used = {k.lower() for _, k, _, _ in entries}
        if used & {d.lower() for d in DECAL_MARKERS} or any(s.startswith("decal") for s in seen):
            issues.append(Issue("warning", "03", path, 1,
                                "用了 decal / 1.15p9+ 的键，但没在 mod-info.txt 声明 `minVersion: 1.15p9`"))

    # W02 双语成对
    # 只检查"有值"的键：`displayDescription:`（空值）是刻意清空，不算漏翻
    # mod-info.txt 方向相反（基键=中文，_en=英文），不套用通用规则
    is_modinfo = os.path.basename(path).lower() == "mod-info.txt"
    keys_here = {k for _, k, v, _ in entries if v.strip()} if not is_modinfo else set()
    for base in BILINGUAL_BASES:
        if base in keys_here and f"{base}_zh" not in keys_here:
            ln = next(l for l, k, _, _ in entries if k == base)
            issues.append(Issue("warning", "02", path, ln,
                                f"`{base}` 有值但缺 `{base}_zh`（中文玩家会看到英文）"))
        if f"{base}_zh" in keys_here and base not in keys_here:
            ln = next(l for l, k, _, _ in entries if k == f"{base}_zh")
            issues.append(Issue("warning", "02", path, ln,
                                f"`{base}_zh` 有值但缺基键 `{base}`（英文环境无文本）"))

    # E06 / W05 引用完整性
    def resolve(name, prefixes):
        """luke 语里 `projectile: 1` 指的是 `[projectile_1]`，也可能是自定义名。"""
        if name in all_sections:
            return True
        for p in prefixes:
            if f"{p}_{name}" in all_sections or f"{p}{name}" in all_sections:
                return True
        return False

    for ln, key, val, sec in entries:
        v = val.strip()
        if not v:
            continue
        if key in ("projectile", "altProjectile"):
            if not resolve(v, ("projectile",)):
                issues.append(Issue("error", "06", path, ln,
                                    f"`{key}: {v}` 指向的弹丸节不存在（应有 `[projectile_{v}]`）"))
        elif key == "copyFrom":
            if v.startswith('"""'):
                continue          # 多行 copyFrom，值在块里，跳过
            if any(t in v for t in ("/", "\\", ".template", ".ini", ".txt", "ROOT:", "SHARED:")):
                continue          # 这是"复制整个文件"，不是复制某个节
            for target in re.split(r"[,\s]+", v):
                if target and not resolve(target, ("", "units/", "units\\")):
                    issues.append(Issue("warning", "05", path, ln,
                                        f"`copyFrom: {target}` 指向的节在本次扫描范围内找不到"))
        elif key == "alsoTriggerAction":
            for target in re.split(r"[,\s]+", v):
                if target and not target.startswith("${") and \
                        not resolve(target, ("action", "hiddenAction")):
                    issues.append(Issue("warning", "05", path, ln,
                                        f"`alsoTriggerAction: {target}` 指向的动作节找不到"))

    # W06 空节（@memory / @global 这类指令也算内容）
    for ln, name in sections:
        if sec_keys.get(name, 0) == 0 and directives.get(name, 0) == 0:
            issues.append(Issue("warning", "06", path, ln, f"节 `[{name}]` 里没有任何键"))

    return issues


def find_mod_root(path):
    """向上找 mod-info.txt，用来读 minVersion。"""
    d = os.path.dirname(os.path.abspath(path))
    for _ in range(6):
        mi = os.path.join(d, "mod-info.txt")
        if os.path.isfile(mi):
            return d, mi
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None, None


def read_min_version(mod_info):
    if not mod_info:
        return ""
    try:
        for line in io.open(mod_info, encoding="utf-8-sig", errors="replace"):
            m = re.match(r"^\s*minVersion\s*:\s*(\S+)", line, re.I)
            if m:
                return m.group(1)
    except OSError:
        pass
    return ""


def collect_files(target):
    if os.path.isfile(target):
        return [target]
    out = []
    for dp, _, fns in os.walk(target):
        for f in fns:
            low = f.lower()
            if low.endswith((".ini", ".template")) or low == "mod-info.txt":
                out.append(os.path.join(dp, f))
    return sorted(out)


def _asset_key(name):
    """归一化文件名：忽略空格 / 连字符 / 下划线 / 全半角括号，只留主干和扩展名。"""
    stem, ext = os.path.splitext(name)
    return re.sub(r"[\s\-_－—–（）()]+", "", stem).lower(), ext.lower()


def find_asset(filename):
    """在常见位置找资料文件：既支持 tools/ 布局，也支持 skill/scripts/ 布局。

    先按原名精确匹配（保持历史行为），找不到再按归一化文件名回退 ——
    因为 skill 里的中文代码表叫「单位代码表Modding-API-Reference.txt」（连字符），
    而代码里写的是「单位代码表Modding API Reference.txt」（空格）。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = [os.path.normpath(d) for d in (
        os.path.join(here, "..", "references"),   # skill/scripts/ -> skill/references/
        os.path.join(here, ".."),                 # tools/ -> 项目根
        os.path.join(here, "..", ".."),
        os.path.join(here, "..", "..", "references"),
        os.getcwd(),
        os.path.join(os.getcwd(), "references"),
    )]
    for d in dirs:                                # 第一遍：原名精确匹配
        c = os.path.join(d, filename)
        if os.path.isfile(c):
            return c
    want = _asset_key(filename)                   # 第二遍：归一化比对
    for d in dirs:
        try:
            entries = sorted(os.listdir(d))
        except OSError:
            continue
        for e in entries:
            if _asset_key(e) == want and os.path.isfile(os.path.join(d, e)):
                return os.path.join(d, e)
    return None

# ---------------------------------------------------------------- 数据接口
# 下面这些是给 MCP / 其它程序化调用方用的：把 CSV、中文表、速查表都变成数据。

CSV_KEY_RX = re.compile(r"^([A-Za-z_@][\w@\[\]#\-\.]*)\s*:\s*(.*)$")


def load_csv_rows(path):
    """CSV -> {小写键名: [{version, value_type, description, example, spelling, row}]}

    比 load_csv_keys 严格：只收 col1 形如 `key:` 的行，并且保留 Example 列。
    CSV 是 utf-8-sig；列序 [0]版本 [1]键 [2]值类型（表头写 Section Type，是误导）
    [3]描述 [4]例子。同一个键可能有多行，全部保留。
    """
    out = {}
    if not path or not os.path.isfile(path):
        return out
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        for n, row in enumerate(csv.reader(fh), 1):
            if len(row) < 4:
                continue
            code = (row[1] or "").strip()
            desc = (row[3] or "").strip()
            vtype = (row[2] or "").strip()
            m = CSV_KEY_RX.match(code)
            if m:
                base = m.group(1)
            else:
                # 有些条目只写键名、不带冒号。只收"有类型或描述"的，
                # 借此过滤掉目录行（那些行的类型和描述都是空的）。
                if not re.match(r"^[A-Za-z_@][\w@\[\]#\.]*$", code):
                    continue
                if not (vtype or desc):
                    continue
                base = code
            base = re.sub(r"\([^)]*\)", "", base).replace("{LANG}", "").strip()
            if not base:
                continue
            ver = (row[0] or "").strip()
            if ver.startswith("["):
                ver = ""          # 有些行把 [section] 塞在版本列里
            item = dict(row=n,
                        version=ver,
                        value_type=vtype,
                        description=desc,
                        example=(row[4] or "").strip() if len(row) > 4 else "",
                        spelling=base)
            bucket = out.setdefault(base.lower(), [])
            sig = (item["version"], item["value_type"], item["description"], item["example"])
            if not any((x["version"], x["value_type"], x["description"], x["example"]) == sig
                       for x in bucket):
                bucket.append(item)
    return out


CN_HEAD_RX = re.compile(r"^([A-U])-(?:([a-z]+)-)?(\d*)：(.+)$")
CN_NAME_RX = re.compile(r"^([A-Za-z_@][\w@\.\[\]#\-]*?)\s*[（(](.*)[）)]\s*$")
CN_FIELDS = (("描述", "description"), ("值类型", "value_type"),
             ("正确例子", "correct_examples"), ("错误例子", "wrong_examples"),
             ("约束", "constraints"))


def _cn_alias(name):
    """`displayText_[Language]` -> `displaytext`，`builtFrom_#_name` -> `builtfrom`。"""
    n = re.sub(r"\[[^\]]*\]", "", name)
    n = re.sub(r"_#[A-Za-z]*", "", n)
    return n.strip("_").lower()


def load_cn_entries(path):
    """中文代码表 -> {小写键名: [{chapter, entry_id, spelling, gloss, ...}]}"""
    out = {}
    if not path or not os.path.isfile(path):
        return out
    lines = io.open(path, encoding="utf-8", errors="replace").read().split("\n")
    exact, alias = {}, {}
    cur = None
    for idx, raw in enumerate(lines, 1):
        st = raw.strip()
        m = CN_HEAD_RX.match(st)
        if m:
            chap, grp, num, rest = m.groups()
            nm = CN_NAME_RX.match(rest)
            if not nm:
                cur = None
                continue
            entry = dict(line=idx, chapter=chap,
                         entry_id=("%s-%s-%s" % (chap, grp, num)) if grp else ("%s-%s" % (chap, num)),
                         spelling=nm.group(1), gloss=nm.group(2).strip(),
                         description="", value_type="",
                         correct_examples=[], wrong_examples=[], constraints=[])
            exact.setdefault(entry["spelling"].lower(), []).append(entry)
            al = _cn_alias(entry["spelling"])
            if al and al != entry["spelling"].lower():
                alias.setdefault(al, []).append(entry)
            cur = entry
            continue
        if cur is None or not st:
            continue
        for label, field in CN_FIELDS:
            pre = label + "："
            if st.startswith(pre):
                val = st[len(pre):].strip()
                if field in ("description", "value_type"):
                    cur[field] = (cur[field] + "\n" + val).strip() if cur[field] else val
                else:
                    cur[field].extend([x.strip() for x in re.split(r"[；;]", val) if x.strip()])
                break
    out.update(exact)
    for k, v in alias.items():
        if k not in out:
            out[k] = v
    return out


REF_RULES = {
    "must_pair": [
        {"keys": ["addActionCooldownApplyToActions", "addActionCooldownTime"],
         "note": "缺后者则前者无效（E12）"},
        {"keys": ["alsoTriggerActionRepeat", "alsoTriggerAction"],
         "note": "必须写在同一节；Repeat 写 0 不是「不重复」，而是取消整个 alsoTriggerAction（W13 / W14）"},
        {"keys": ["alwaysSinglePress", "canPlayerCancel", "allowMultipleInQueue"],
         "note": "alwaysSinglePress: true 需同时写 canPlayerCancel: false 和 allowMultipleInQueue: false（W15）"},
        {"keys": ["canAttack", "canAttackFlyingUnits", "canAttackLandUnits", "canAttackUnderwaterUnits"],
         "note": "canAttack: true 时三个目标类型键必填，引擎不给默认值（E14）"},
    ],
    "hard_constraints": [
        {"scope": "[hiddenAction_*]", "rule": "不能写 isVisible（除非静态 false）",
         "why": "加载期抛 isVisible doesn't make sense to use in hidden actions（E11）"},
        {"scope": "tookDamage 事件", "rule": "在扣血之前触发",
         "why": "里面读 self.hp 做差分恒为 0"},
        {"scope": "@memory / @global / @define", "rule": "行尾不能写 # 注释",
         "why": "引擎不剥离行尾 #，会当成值的一部分（E15）"},
        {"scope": "action 按钮文本", "rule": "text / description 用 %{} 而非 ${}",
         "why": "载入期插值永远显示初始值（W10）"},
    ],
}


def ref_payload():
    """速查表的结构化形式。--ref 与 MCP 的 get_ref 都从这里渲染。"""
    return {
        "events": sorted(EVENTS),
        "functions": sorted(FUNCS),
        "nonexistent_functions": sorted(NONEXISTENT_FUNCS),
        "math_extra": {"names": sorted(MATH_EXTRA), "note": "%{} 表达式另支持，^ 表示乘方"},
        "enums": {k: list(v) for k, v in ENUM_VALUES.items()},
        "memory_types": sorted(MEM_TYPES),
        "plain_numeric_keys": sorted(PLAIN_NUMERIC),
        "version_order": list(VERSION_ORDER),
        "sections": dict(FAMILY_NAMES),
        "family_exempt": sorted(FAMILY_EXEMPT),
        "family_loose": sorted(FAMILY_LOOSE),
        "rules": REF_RULES,
    }


def render_ref_text():
    """把 ref_payload() 渲染成给人看的中文速查表（--ref 的输出）。"""
    out = []
    out.append("== autoTriggerOnEvent 合法事件（18 个，来自 af 枚举）==")
    out.append("  " + "\n  ".join(sorted(EVENTS)))
    out.append("\n== 逻辑函数（27 个，来自 LogicBoolean 注册表）==")
    out.append("  " + "\n  ".join(sorted(FUNCS)))
    out.append("\n  %{} 数学表达式另支持：" + ", ".join(sorted(MATH_EXTRA)) + "（^ 表示乘方）")
    out.append("\n== 值枚举 ==")
    for k, vals in ENUM_VALUES.items():
        out.append("  %s: %s" % (k, " / ".join(vals)))
    out.append("\n== @memory 类型 ==")
    out.append("  " + " / ".join(sorted(MEM_TYPES)) + "（数组加 []）")
    out.append("\n== 需要配合使用的键 ==")
    out.append("  addActionCooldownApplyToActions 必须配 addActionCooldownTime")
    out.append("  alsoTriggerActionRepeat 必须配 alsoTriggerAction；写 0 会取消 alsoTriggerAction")
    out.append("  alwaysSinglePress: true 必须配 canPlayerCancel: false + allowMultipleInQueue: false")
    out.append("\n== 硬限制 ==")
    out.append("  [hiddenAction_*] 里不能写 isVisible（非静态 false）→ 加载期抛异常")
    out.append("  tookDamage 在扣血之前触发 → 里面读 self.hp 做差分恒为 0")
    return "\n".join(out)


def _data_signature(csv_path, cn_path, jar_path, text_path, n_jar):
    """数据表 + 规则文件本身的指纹。任何一项变了，整份结果缓存作废。

    带上 __file__ 的 mtime：改了规则却复用旧结论是最难查的一类 bug。
    """
    if rw_cache is None:
        return ""
    parts = ["v%d" % rw_cache.CACHE_VERSION]
    for p in (csv_path, cn_path, text_path, os.path.abspath(__file__)):
        try:
            st = os.stat(p)
            parts.append("%s:%d:%d" % (os.path.basename(p), st.st_mtime_ns, st.st_size))
        except (OSError, TypeError):
            parts.append("%s:-" % (p,))
    parts.append("jar=%d" % n_jar)
    return rw_cache.digest(parts)


def _stamp(path):
    try:
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)
    except (OSError, TypeError):
        return None


_TABLE_MEMO = {}


def _load_tables(csv_path, cn_path, jar_path):
    """加载全部键名资料，按文件指纹记忆化。

    这几张表加起来 500 KB 左右，解析约 50 ms —— 对单文件检查来说这是固定成本，
    而长驻服务每次 lint 都要付一遍。表没变就直接复用。
    """
    text_path = find_asset("二进制键名.txt")
    key = (csv_path, _stamp(csv_path), cn_path, _stamp(cn_path),
           jar_path, _stamp(jar_path), text_path, _stamp(text_path))
    hit = _TABLE_MEMO.get(key)
    if hit is not None:
        return hit

    csv_keys = load_csv_keys(csv_path)
    cn_keys = load_cn_keys(cn_path)
    jar_keys = load_jar_keys(jar_path) if jar_path else set()
    text_keys = load_text_keys(text_path)
    cn_canon = load_cn_canon(cn_path)
    key_families = load_key_families(cn_path)
    key_templates = load_key_templates(cn_path)
    canon = build_canon(csv_keys, cn_canon)
    known = expand_lang_keys(set(csv_keys) | set(cn_keys) | jar_keys | text_keys)
    known |= {"repeatconditional", "extratriggeractions", "islockedmessage",
              "cannotplacemessage", "customvalue", "preferences"}

    val = dict(csv_keys=csv_keys, cn_keys=cn_keys, jar_keys=jar_keys,
               text_keys=text_keys, canon=canon, known=known,
               key_families=key_families, key_templates=key_templates,
               text_path=text_path)
    _TABLE_MEMO.clear()          # 只保留最近一份，避免多套数据表常驻内存
    _TABLE_MEMO[key] = val
    return val


def run_lint(target, csv_path=None, cn_path=None, jar_path=None, incremental=True):
    """程序化入口：不打印、不退出，返回结果字典。

    issues 里是 Issue 对象（保留 __str__ 的原始格式），需要 JSON 时用 .as_dict()。

    incremental=True 时启用两级缓存（见 rw_cache.py）：
      一级按文件 mtime/大小复用解析结果；
      二级复用逐文件检查结果，但会先重放它上次对跨文件集合做过的所有查询，
      有一条答案变了就重算 —— 所以改一个文件不会漏掉别的文件的结论。
    """
    t_start = time.perf_counter()
    res = dict(ok=True, error=None, files=0, errors=0, warnings=0,
               issues=[], skipped=[], key_sources={}, assets={},
               elapsed_ms=0, scanned_files=0, cache={"enabled": False})
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(here)
        csv_path = csv_path or find_asset("官方代码表（Modding References）.csv")
        cn_path = cn_path or find_asset("单位代码表Modding API Reference.txt")
        res["assets"] = dict(csv=csv_path, cn=cn_path, jar=jar_path)

        tb = _load_tables(csv_path, cn_path, jar_path)
        csv_keys, cn_keys, jar_keys = tb["csv_keys"], tb["cn_keys"], tb["jar_keys"]
        text_keys, canon, known = tb["text_keys"], tb["canon"], tb["known"]
        key_families, key_templates = tb["key_families"], tb["key_templates"]
        res["key_sources"] = dict(csv=len(csv_keys), cn=len(cn_keys),
                                  jar=len(jar_keys), text=len(text_keys),
                                  known=len(known))
        if not known:
            res["ok"] = False
            res["error"] = "没加载到任何键名资料，请用 --csv / --cn 指定路径"
            return res

        files = collect_files(target)
        res["files"] = len(files)
        res["scanned_files"] = len(files)

        all_sections, all_defines, unit_names, referenced, parsed = set(), set(), set(), set(), {}
        for f in files:
            try:
                full = parse_file(f)
            except Exception as e:
                res["skipped"].append(dict(file=f, error=str(e)))
                continue
            secs, entries, lines = full[0], full[1], full[2]
            parsed[f] = full
            all_sections |= {s for _, s in secs}
            all_defines |= full[5]
            for _ln, _k, _v, _sec in entries:
                if (_sec or "").lower().startswith("core") and _k in ("name", "altNames"):
                    for _nm in re.split(r"[,\s]+", _v.strip()):
                        if _nm and not _nm.startswith("${"):
                            unit_names.add(_nm.lower())
            for line in lines:
                for expr in re.findall(r"\$\{([^}]*)\}", line):
                    for ident in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr):
                        referenced.add(ident.lower())

        # ---- 缓存准备 -------------------------------------------------
        cross_sets = dict(all_sections=all_sections, global_defines=all_defines,
                          referenced=referenced, unit_names=unit_names)
        issue_cache = None
        scope = ""
        digests = {}
        if incremental and rw_cache is not None:
            issue_cache = rw_cache.IssueCache(
                _data_signature(csv_path, cn_path, jar_path,
                                tb["text_path"], len(jar_keys)),
                enabled=True)
            if issue_cache.enabled:
                # scope 把「扫单文件」和「扫整个目录」区分开：
                # 两者看到的跨文件集合不同，结论不能互相复用。
                scope = rw_cache.digest(sorted(os.path.abspath(f) for f in files))
                digests = {k: rw_cache.digest(sorted(v)) for k, v in cross_sets.items()}

        all_issues = []
        for f in parsed:
            mod_root_dir, mod_info = find_mod_root(f)
            mv = read_min_version(mod_info)
            has_tpl = bool(mod_root_dir and os.path.isfile(
                os.path.join(mod_root_dir, "all-units.template")))
            ctx = "%s|%d" % (mv, 1 if has_tpl else 0)

            if issue_cache is not None:
                hit = issue_cache.lookup(f, scope, ctx, cross_sets, digests)
                if hit is not None:
                    all_issues += [Issue(lv, cd, f, ln, ms) for lv, cd, ln, ms in hit]
                    continue

            if issue_cache is not None:
                probes = rw_cache.make_probe_sets(cross_sets)
                try:
                    iss = check_file(
                        f, known, csv_keys, mv, probes["all_sections"], root,
                        probes["global_defines"], probes["referenced"], canon,
                        probes["unit_names"], key_families, has_tpl, key_templates,
                        parsed=parsed[f])
                except Exception:
                    # 检查中途抛异常时探针是残缺的，宁可不算缓存
                    all_issues += check_file(
                        f, known, csv_keys, mv, all_sections, root, all_defines,
                        referenced, canon, unit_names, key_families, has_tpl,
                        key_templates, parsed=parsed[f])
                else:
                    issue_cache.store(f, scope, ctx, iss,
                                      {k: v.probes for k, v in probes.items()})
                    all_issues += iss
            else:
                all_issues += check_file(
                    f, known, csv_keys, mv, all_sections, root, all_defines,
                    referenced, canon, unit_names, key_families, has_tpl,
                    key_templates, parsed=parsed[f])

        all_issues.sort(key=lambda i: (i.path, i.line))
        res["issues"] = all_issues
        res["errors"] = sum(1 for i in all_issues if i.level == "error")
        res["warnings"] = sum(1 for i in all_issues if i.level == "warning")

        if issue_cache is not None:
            issue_cache.save()
            st = issue_cache.stats()
            st["parse"] = _PARSE_MEMO.stats() if _PARSE_MEMO is not None else None
            res["cache"] = st
        res["elapsed_ms"] = int((time.perf_counter() - t_start) * 1000)
        return res
    except Exception as e:
        res["ok"] = False
        res["error"] = "%s: %s" % (type(e).__name__, e)
        return res


# ---------------------------------------------------------------- main
def _force_utf8():
    """Windows 上默认 stdout 是 ANSI 代码页，打印中文会 UnicodeEncodeError。
    只在 CLI 入口调用 —— 模块级调用会干扰 MCP 服务端的 stdout 协议通道。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main():
    _force_utf8()
    ap = argparse.ArgumentParser(description="铁锈战争模组写后验证")
    ap.add_argument("target", nargs="?", help="要检查的文件或目录（用 --ref 时可省略）")
    ap.add_argument("--csv", default=None, help="官方代码表 CSV")
    ap.add_argument("--cn", default=None, help="中文离线代码表 txt")
    ap.add_argument("--jar", default=None, help="game-lib.jar（可选，增加二进制键名）")
    ap.add_argument("--quiet", action="store_true", help="只显示错误")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--ref", action="store_true",
                    help="打印速查表（事件名 / 函数 / 枚举 / 内存类型）后退出")
    ap.add_argument("--no-cache", action="store_true",
                    help="不复用缓存，强制全量重算（怀疑缓存有错时用）")
    ap.add_argument("--timing", action="store_true", help="额外打印耗时与缓存命中")
    args = ap.parse_args()

    if args.ref:
        print(render_ref_text())
        return 0

    if not args.target:
        ap.error("需要指定要检查的文件或目录（或用 --ref 查看速查表）")

    res = run_lint(args.target, args.csv, args.cn, args.jar,
                   incremental=not args.no_cache)
    if not res["ok"]:
        print("错误：" + str(res["error"]), file=sys.stderr)
        return 1
    for sk in res["skipped"]:
        print(f"跳过 {sk['file']}：{sk['error']}", file=sys.stderr)

    all_issues = res["issues"]
    errors = [i for i in all_issues if i.level == "error"]
    warns = [i for i in all_issues if i.level == "warning"]

    if args.json:
        print(json.dumps(dict(files=res["files"], errors=len(errors), warnings=len(warns),
                              elapsed_ms=res.get("elapsed_ms", 0),
                              cache=res.get("cache"),
                              issues=[i.as_dict() for i in all_issues]),
                         ensure_ascii=False, indent=2))
    else:
        ks = res["key_sources"]
        print(f"扫描 {res['files']} 个文件；键名资料 {ks.get('known', 0)} 条"
              f"（CSV {ks.get('csv', 0)} / 中文表 {ks.get('cn', 0)} / 二进制 {ks.get('jar', 0)}）\n")
        if errors:
            print("=== 错误 ===")
            for i in errors:
                print(" ", i)
            print()
        if warns and not args.quiet:
            print("=== 警告 ===")
            for i in warns:
                print(" ", i)
            print()
        if not errors and not warns:
            print("干净，没发现问题。")
        print(f"\n合计：{len(errors)} 个错误，{len(warns)} 个警告")

    if args.timing:
        c = res.get("cache") or {}
        print("\n耗时 %d ms；文件 %d 个" % (res.get("elapsed_ms", 0), res.get("files", 0)))
        if c.get("enabled"):
            print("结果缓存：命中 %d / 未命中 %d（复用了 %d 个文件的结论）"
                  % (c.get("hits", 0), c.get("misses", 0), c.get("reused_files", 0)))
            p = c.get("parse") or {}
            if p:
                print("解析缓存：命中 %d / 未命中 %d"
                      % (p.get("hits", 0), p.get("misses", 0)))
        else:
            print("缓存：未启用")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
