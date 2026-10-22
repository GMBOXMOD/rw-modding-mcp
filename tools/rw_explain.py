#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""explain_actions —— 把事件/autoTrigger → 动作 → alsoTriggerAction 的调用图画出来。

能做的（纯静态、可判定）
------------------------
  1. 调用图：谁触发谁、经过哪个 alsoTriggerAction、repeat 多少次、门控条件是什么
  2. 每个动作读了哪些 memory、写了哪些 memory
  3. 四条规则：
       loop-counter   循环变量有没有复位、有没有推进
       unreachable    动作定义了但没人调用
       uninit-memory  @memory 声明了、被读了，但从没被写过
       index-bound    循环下标步长 / 偏移导致的上界问题

做不到的（明确不做，不猜）
--------------------------
  * 条件表达式在运行时到底成不成立（除了字面量 true/false）
  * repeat 次数是运行时表达式的情况（只认字面量和 @global 常量）
  * 跨文件继承（copyFrom / all-units.template）带来的边
  * 数组的真实长度（luke 数组自动扩容，没有声明）
  * 单位最终打不打人 —— 那是运行时行为，静态看不出来

用法
----
    python tools/rw_explain.py <文件>
    python tools/rw_explain.py <文件> --json
    python tools/rw_explain.py <文件> --action scanThreatSlot
"""

import io
import json
import os
import re
import sys

TRIGGER_EVENT = "autoTriggerOnEvent"
TRIGGER_PERIODIC = "autoTrigger"
GATE_KEYS = ("alsoTriggerOrQueueActionConditional", "alsoTriggerActionConditional")
EDGE_KEY = "alsoTriggerAction"
REPEAT_KEY = "alsoTriggerActionRepeat"
COND_KEY = "requireConditional"

ACTION_PREFIXES = ("hiddenAction_", "action_")

NOT_CHECKED = [
    "条件表达式在运行时是否成立（只认字面量 true/false）",
    "repeat 是运行时表达式的情况（只认字面量与 @global 常量）",
    "跨文件继承（copyFrom / all-units.template）产生的调用边",
    "luke 数组的真实长度（引擎自动扩容，没有声明可查）",
    "单位最终会不会真的打人（运行时行为）",
]


# ---------------------------------------------------------------- 解析

def _parse_sections(lines):
    """自己解析节与键值。

    不能直接用 rw_lint.parse_file 的 entries：它把块写法的值记成三个引号本身，
    块里的内容不会拼进去，而 setUnitMemory 基本都是块写法。
    """
    sections = {}
    order = []
    comments = []
    cur = None
    i, n = 0, len(lines)
    while i < n:
        raw = lines[i]
        st = raw.strip()
        line_no = i + 1
        i += 1

        if not st or st.startswith("#"):
            continue

        m = re.match(r"^\[(.+?)\]\s*$", st)
        if m:
            cur = m.group(1).strip()
            if cur not in sections:
                sections[cur] = {}
                order.append((cur, line_no))
            continue

        if cur is None or st.startswith("@"):
            continue
        if ":" not in st:
            continue

        key, _, val = st.partition(":")
        key = key.strip()
        val = val.strip()

        if val.startswith('"""'):
            body = val[3:]
            if '"""' in body:                          # 单行块
                val = body.split('"""')[0]
            else:                                      # 多行块
                buf = [body] if body.strip() else []
                while i < n:
                    ln = lines[i]
                    i += 1
                    if '"""' in ln:
                        head = ln.split('"""')[0]
                        if head.strip():
                            buf.append(head)
                        break
                    buf.append(ln)
                val = "\n".join(buf)
        elif " #" in val:
            # 行尾注释。引擎其实**不剥**行尾 #（只跳过整行以 # 开头的），
            # 这里为了能画出图，按去掉注释后的值解析，同时记一条告警。
            comments.append({"line": line_no, "section": cur, "key": key, "raw": val})
            val = val.split(" #", 1)[0].rstrip()

        sections[cur].setdefault(key, []).append((line_no, val))

    return sections, order, comments


def _scan_directives(lines, comments=None):
    """@memory / @global 声明。@global 的值同样要剥行尾注释，
    否则 `@global SLOTS: 4 # 槽数` 会让 repeat 解析不出来，整条循环分析被跳过。"""
    mem, glob = {}, {}
    for idx, line in enumerate(lines, 1):
        st = line.strip()
        m = re.match(r"^@memory\s+([A-Za-z_]\w*)\s*:\s*(\S+)", st)
        if m:
            mem[m.group(1)] = {"type": m.group(2), "line": idx}
            continue
        g = re.match(r"^@global\s+([A-Za-z_]\w*)\s*:\s*(.+)$", st)
        if g:
            val = g.group(2).strip()
            if " #" in val:
                if comments is not None:
                    comments.append({"line": idx, "section": "@global",
                                     "key": g.group(1), "raw": val})
                val = val.split(" #", 1)[0].rstrip()
            glob[g.group(1).upper()] = {"value": val, "line": idx}
    return mem, glob


def _resolve_int(expr, globals_):
    if expr is None:
        return None
    e = expr.strip()
    m = re.fullmatch(r"\$\{([A-Za-z_]\w*)\}", e)
    if m:
        g = globals_.get(m.group(1).upper())
        if not g:
            return None
        e = g["value"]
    if re.fullmatch(r"-?\d+", e):
        return int(e)
    return None


def _split_targets(value):
    return [p.strip() for p in re.split(r"[,\n]", value or "") if p.strip()]


def _parse_setunitmemory(value):
    """拆 setUnitMemory 的赋值 → [(base, lhs, rhs)]，逗号只在括号外才分割。"""
    if not value:
        return []
    text = value.replace('"""', "").strip()
    parts, cur, depth = [], "", 0
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)

    out = []
    for p in parts:
        if "=" not in p:
            continue
        lhs, rhs = p.split("=", 1)
        lhs = lhs.strip()
        m = re.match(r"^([A-Za-z_]\w*)", lhs)
        if m:
            out.append((m.group(1), lhs, rhs.strip()))
    return out


def _mem_reads(text):
    return set(re.findall(r"memory\.([A-Za-z_]\w*)", text or ""))


def _array_accesses(text):
    """数组访问。写的时候是裸名 `arr[i]=`，读的时候可能带 memory. 前缀，两种都收。"""
    return [(m.group(1), m.group(2).strip())
            for m in re.finditer(r"(?:\bmemory\.)?([A-Za-z_]\w*)\s*\[\s*([^\]]+)\]",
                                 text or "")]


def _kind(section):
    s = (section or "").lower()
    if s.startswith("hiddenaction"):
        return "hiddenAction"
    if s.startswith("action"):
        return "action"
    return "other"


def _is_actionish(section):
    return _kind(section) in ("action", "hiddenAction")


def _make_resolver(sections):
    """luke 里 alsoTriggerAction: foo 指向 [action_foo] 或 [hiddenAction_foo]，
    寻址用的是去掉前缀后的名字。"""
    index = {}
    for name in sections:
        low = name.lower()
        for p in ACTION_PREFIXES:
            if low.startswith(p.lower()):
                index[low[len(p):]] = name
                break
        index.setdefault(low, name)
    return lambda target: index.get((target or "").strip().lower())


# ---------------------------------------------------------------- 建图

def analyze_file(path):
    lines = io.open(path, encoding="utf-8", errors="replace").read().split("\n")
    sections, order, comments = _parse_sections(lines)
    mem_decl, globals_ = _scan_directives(lines, comments)
    resolve = _make_resolver(sections)
    sec_line = dict(order)

    nodes = {}
    for sec, kv in sections.items():

        def first(k):
            return kv[k][0][1] if k in kv else None

        node = {
            "section": sec,
            "line": sec_line.get(sec, 0),
            "kind": _kind(sec),
            "triggers": [],
            "require": first(COND_KEY),
            "repeat": None,
            "gate": None,
            "edges": [],
            "memory_writes": [],
            "memory_reads": set(),
            "setunitmemory": [],
            "array_accesses": [],
        }

        if first(TRIGGER_EVENT) is not None:
            node["triggers"].append({"type": "event", "value": first(TRIGGER_EVENT).strip()})
        if first(TRIGGER_PERIODIC) is not None:
            node["triggers"].append({"type": "periodic", "value": first(TRIGGER_PERIODIC).strip()})
        for gk in GATE_KEYS:
            if first(gk) is not None:
                node["gate"] = first(gk).strip()
                break

        rep_raw = first(REPEAT_KEY)
        if rep_raw is not None:
            node["repeat"] = {"expr": rep_raw.strip(), "value": _resolve_int(rep_raw, globals_)}

        for _ln, v in kv.get(EDGE_KEY, []):
            for tgt in _split_targets(v):
                node["edges"].append({"to": tgt, "resolved": resolve(tgt),
                                      "repeat": node["repeat"]})

        writes = set()
        # updateUnitMemory 官方定义是「类似 setUnitMemory 但性能更好」，
        # 写入语义一样，必须一起扫，否则用它写的变量会被误报成「只读不写」。
        for wk in ("setUnitMemory", "updateUnitMemory"):
            for _ln, v in kv.get(wk, []):
                for base, lhs, rhs in _parse_setunitmemory(v):
                    writes.add(base)
                    node["setunitmemory"].append({"base": base, "target": lhs,
                                                  "value": rhs, "via": wk})
                    node["memory_reads"] |= _mem_reads(rhs)
                for arr, idx in _array_accesses(v):
                    node["array_accesses"].append({"array": arr, "index": idx})
                # readUnitMemory(name=...) 是函数式读取
                for nm in re.findall(r"readUnitMemory\s*\(\s*(?:name\s*=\s*)?[\"']?"
                                     r"([A-Za-z_]\w*)", v):
                    node["memory_reads"].add(nm)
        node["memory_writes"] = sorted(writes)
        node["memory_reads"] = sorted(node["memory_reads"] | _mem_reads(node["require"] or ""))

        nodes[sec] = node

    inbound = {}
    for name, node in nodes.items():
        for e in node["edges"]:
            if e["resolved"]:
                inbound.setdefault(e["resolved"], []).append(name)

    findings = []
    findings += _rule_trailing_comment(comments)
    findings += _rule_unresolved_edge(nodes)
    findings += _rule_loop_counter(nodes)
    findings += _rule_unreachable(nodes, inbound)
    findings += _rule_uninit_memory(nodes, mem_decl)
    findings += _rule_index_bound(nodes)

    return {
        "ok": True,
        "file": path,
        "nodes": nodes,
        "inbound": inbound,
        "entries": [n for n, node in nodes.items() if node["triggers"]],
        "findings": findings,
        "memory_declared": {k: v["type"] for k, v in mem_decl.items()},
        "globals": {k: v["value"] for k, v in globals_.items()},
        "unresolved_edges": sorted({e["to"] for node in nodes.values()
                                    for e in node["edges"] if not e["resolved"]}),
        "trailing_comments": comments,
        "not_checked": NOT_CHECKED,
    }


# ---------------------------------------------------------------- 规则

def _rule_trailing_comment(comments):
    out = []
    for c in comments:
        out.append({
            "rule": "trailing-comment", "level": "warning", "line": c["line"],
            "message": "第 %d 行 %s 有行尾注释：引擎不剥行尾 #，这个值会带着注释一起解析；"
                       "本工具按去掉注释后的值画图，但游戏里很可能不生效"
                       % (c["line"], c["key"]),
        })
    return out


def _rule_unresolved_edge(nodes):
    out = []
    for name, node in nodes.items():
        for e in node["edges"]:
            if e["resolved"]:
                continue
            out.append({
                "rule": "unresolved-edge", "level": "warning", "line": node["line"],
                "message": "「%s」的 alsoTriggerAction 指向「%s」，但文件里没有对应的"
                           "[action_%s] / [hiddenAction_%s]（也可能是行尾注释或拼写问题）"
                           % (name, e["to"], e["to"], e["to"]),
            })
    return out


def _rule_loop_counter(nodes):
    """循环变量：同一触发链上、repeat 之前有没有复位；循环体里有没有推进。

    复位必须看**祖先链**，不能看全文件 ——
    文件别处也写 `scan_i= 0` 不代表这条链在进循环前复位过。
    """
    # 入边表（沿它向上找祖先）
    inbound = {}
    for name, node in nodes.items():
        for e in node["edges"]:
            if e["resolved"]:
                inbound.setdefault(e["resolved"], set()).add(name)

    def closure(parent):
        seen, stack = set(), [parent]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(inbound.get(cur, ()))
        return seen

    # 每个节点里"把变量赋成常量"的集合（标量、右侧不引用自己）
    const_of = {}
    for name, node in nodes.items():
        got = set()
        for w in node["setunitmemory"]:
            if "[" in w["target"]:
                continue
            if not re.search(r"\b%s\b" % re.escape(w["base"]), w["value"]):
                got.add(w["base"])
        const_of[name] = got

    out = []
    for name, node in nodes.items():
        rep = node["repeat"]
        if not rep or rep["value"] is None or rep["value"] < 2:
            continue
        scope = closure(name)
        for e in node["edges"]:
            tgt_name = e["resolved"]
            tgt = nodes.get(tgt_name) if tgt_name else None
            if not tgt:
                continue
            adv = [w for w in tgt["setunitmemory"]
                   if "[" not in w["target"]
                   and re.search(r"\bmemory\.%s\s*[+\-]" % re.escape(w["base"]), w["value"])]
            if not adv:
                gv = set(re.findall(r"memory\.([A-Za-z_]\w*)", tgt["gate"] or ""))
                if gv:
                    out.append({
                        "rule": "loop-counter", "level": "error", "line": node["line"],
                        "message": "「%s」repeat %s 次调用「%s」，但循环体没有推进任何变量；"
                                   "门控引用了 %s，永远等不到收尾"
                                   % (name, rep["expr"], tgt_name, ", ".join(sorted(gv))),
                    })
                continue
            for w in adv:
                base = w["base"]
                if not any(base in const_of[a] for a in scope):
                    out.append({
                        "rule": "loop-counter", "level": "warning", "line": node["line"],
                        "message": "「%s」repeat %s 次调用「%s」，循环变量 %s 在循环体里推进了，"
                                   "但这条触发链上（含 %s 本身）找不到进循环前把它复位成常量的写法"
                                   "（例如 %s= 0）—— 多轮调用会接着上一轮的值"
                                   % (name, rep["expr"], tgt_name, base, name, base),
                    })
    return out


def _rule_unreachable(nodes, inbound):
    out = []
    for name, node in nodes.items():
        if not _is_actionish(name) or node["triggers"] or inbound.get(name):
            continue
        out.append({
            "rule": "unreachable", "level": "warning", "line": node["line"],
            "message": "动作「%s」没有任何入边，也没有 autoTrigger / autoTriggerOnEvent，"
                       "静态看永远不会被调用（除非别的文件 copyFrom 它）" % name,
        })
    return out


def _rule_uninit_memory(nodes, mem_decl):
    written, read = set(), set()
    for node in nodes.values():
        written |= set(node["memory_writes"])
        read |= set(node["memory_reads"])
    out = []
    for name, info in mem_decl.items():
        if name in written or name not in read:
            continue
        out.append({
            "rule": "uninit-memory", "level": "warning", "line": info["line"],
            "message": "@memory %s 被读取，但本文件里没有任何地方写它 —— 读到的永远是默认值（0 / 空）"
                       % name,
        })
    return out


def _rule_index_bound(nodes):
    """循环下标：沿 repeat 边看**循环体**里的数组访问。"""
    out = []
    for name, node in nodes.items():
        rep = node["repeat"]
        if not rep or rep["value"] is None or rep["value"] < 2:
            continue
        n = rep["value"]
        for e in node["edges"]:
            tgt = nodes.get(e["resolved"]) if e["resolved"] else None
            if not tgt or not tgt["array_accesses"]:
                continue
            step = {}
            for w in tgt["setunitmemory"]:
                m = re.fullmatch(r"\s*memory\.%s\s*\+\s*(\d+)\s*" % re.escape(w["base"]),
                                 w["value"])
                if m:
                    step[w["base"]] = int(m.group(1))
            for acc in tgt["array_accesses"]:
                m = re.fullmatch(r"memory\.([A-Za-z_]\w*)\s*(?:\+\s*(\d+))?", acc["index"])
                if not m:
                    continue
                var, off = m.group(1), int(m.group(2) or 0)
                k = step.get(var, 1)
                last = (n - 1) * k + off
                if k > 1:
                    out.append({
                        "rule": "index-bound", "level": "warning", "line": tgt["line"],
                        "message": "「%s」循环 %d 次、%s 每轮 +%d，%s[%s] 最大下标 %d —— "
                                   "中间会跳过 %d 个" % (tgt["section"], n, var, k,
                                                       acc["array"], acc["index"], last, k - 1),
                    })
                elif off:
                    out.append({
                        "rule": "index-bound", "level": "warning", "line": tgt["line"],
                        "message": "「%s」循环 %d 次（%s 从 0 到 %d），但访问 %s[%s]，"
                                   "最后一次下标 %d —— 可能越界"
                                   % (tgt["section"], n, var, n - 1,
                                      acc["array"], acc["index"], last),
                    })
    return out


# ---------------------------------------------------------------- 渲染

def render_text(result, action=None):
    nodes = result["nodes"]
    L = []
    L.append("文件：%s" % result["file"])
    if result["globals"]:
        L.append("常量：%s" % ", ".join("%s=%s" % (k, v) for k, v in result["globals"].items()))
    if result["memory_declared"]:
        L.append("memory：%s" % ", ".join("%s:%s" % (k, v)
                                         for k, v in result["memory_declared"].items()))
    if result["unresolved_edges"]:
        L.append("未解析的引用：%s" % ", ".join(result["unresolved_edges"]))
    L.append("")

    seen = set()

    def walk(name, depth, via, repeat, gate):
        node = nodes.get(name)
        pad = "  " * depth
        if node is None:
            L.append("%s└─ %s（未定义）" % (pad, name))
            return
        if name in seen:
            L.append("%s└─ %s（已展开）" % (pad, name))
            return
        seen.add(name)

        head = "%s├─ %s" % (pad, name)
        if via:
            head += "   ← %s" % via
        L.append(head)
        sub = pad + "│   "
        for t in node["triggers"]:
            L.append("%strigger: %s %s" % (sub, t["type"], t["value"]))
        if node["require"]:
            L.append("%srequire: %s" % (sub, node["require"]))
        if repeat:
            val = repeat.get("value")
            shown = repeat.get("expr", "")
            if val is not None and str(val) != str(shown):
                shown += " (=%s)" % val
            L.append("%srepeat : %s 次" % (sub, shown))
        if gate:
            L.append("%sgate   : %s" % (sub, gate))
        if node["memory_writes"]:
            L.append("%swrite  : %s" % (sub, ", ".join(node["memory_writes"])))
        if node["memory_reads"]:
            L.append("%sread   : %s" % (sub, ", ".join(node["memory_reads"])))

        for e in node["edges"]:
            walk(e["resolved"] or e["to"], depth + 1, "alsoTriggerAction", e["repeat"], node["gate"])

    if action:
        target = None
        for nm in nodes:
            if nm.lower() == action.lower() or nm.lower().endswith("_" + action.lower()):
                target = nm
                break
        if not target:
            L.append("找不到动作「%s」。" % action)
            return "\n".join(L)
        starts = [target]
    else:
        starts = result["entries"]

    for st in starts:
        L.append("=== %s ===" % st)
        walk(st, 0, None, None, None)
        L.append("")

    if not action:
        orphans = [n for n in nodes if _is_actionish(n) and n not in seen]
        if orphans:
            L.append("=== 未被任何触发链引用 ===")
            for n in orphans:
                L.append("  %s  (第 %d 行)" % (n, nodes[n]["line"]))
            L.append("")

    if result["findings"]:
        L.append("=== 静态检查 ===")
        for f in result["findings"]:
            L.append("  [%s] %s" % ("错误" if f["level"] == "error" else "警告", f["message"]))
        L.append("")

    L.append("=== 本工具不检查 ===")
    for n in result["not_checked"]:
        L.append("  · " + n)
    return "\n".join(L)


def explain(path, action=None, as_json=False):
    if not os.path.isfile(path):
        return {"ok": False, "error": "文件不存在", "path": path}
    try:
        result = analyze_file(path)
    except Exception as e:                                   # noqa: BLE001
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, e), "path": path}
    if as_json:
        result["file"] = os.path.abspath(path)
        return result
    return {"ok": True, "path": path, "text": render_text(result, action)}


def _force_utf8():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main():
    _force_utf8()
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    path = args[0]
    as_json = "--json" in args
    action = None
    if "--action" in args:
        i = args.index("--action")
        if i + 1 < len(args):
            action = args[i + 1]
    res = explain(path, action, as_json)
    if not res.get("ok"):
        print("错误：%s" % res.get("error"), file=sys.stderr)
        return 1
    print(json.dumps(res, ensure_ascii=False, indent=2) if as_json else res["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
