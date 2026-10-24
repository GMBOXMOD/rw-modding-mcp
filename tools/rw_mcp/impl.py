# -*- coding: utf-8 -*-
"""五个只读工具的实现。

约定
----
* 全部同步、返回可 JSON 序列化的 dict、**永不抛异常**（统一由 _safe 兜底）。
* 这里不 import mcp —— 所以 selftest 不装 SDK 也能跑。
"""

import difflib
import os
import re
import time

import rw_lint
import rw_explain
from . import dataset, source_search, reference_query

# ---------------------------------------------------------------- 工具函数


def _safe(tool, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:                                   # noqa: BLE001
        return {"ok": False, "tool": tool, "error": "%s: %s" % (type(e).__name__, e)}


def _clamp(v, lo, hi, default):
    try:
        v = int(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def resolve_target(path):
    """绝对路径直接用；否则先试 cwd，再试项目根。返回 (abs|None, tried[])"""
    if not path:
        return None, []
    tried = []
    cands = [path] if os.path.isabs(path) else [
        os.path.join(os.getcwd(), path),
        os.path.join(dataset.ROOT, path),
    ]
    for c in cands:
        c = os.path.normpath(os.path.abspath(c))
        tried.append(c)
        if os.path.exists(c):
            return c, tried
    return None, tried


def _sections_of(low):
    ds = dataset.get_dataset()
    letters = set(ds.key_families.get(low) or ())
    letters.update(family for row in ds.csv_rows.get(low, ())
                   for family in [rw_lint.section_family(row.get("section"))] if family)
    return [{"letter": ch, "name": rw_lint.FAMILY_NAMES.get(ch, ch)}
            for ch in sorted(letters)]


def _notes_for(low, family=None):
    out = []
    for rule in rw_lint.REF_RULES["must_pair"]:
        if any(k.lower() == low for k in rule["keys"]):
            if low == "canattack":
                if family and family != "D":
                    continue
                out.append("[attack] " + rule["note"])
            else:
                out.append(rule["note"])
    for rule in rw_lint.REF_RULES["hard_constraints"]:
        words = {word.lower() for word in re.findall(r"[A-Za-z_]\w*", rule["rule"])}
        scope_family = rw_lint.section_family(rule["scope"].lstrip("["))
        if low in words and (not family or not scope_family or scope_family == family):
            out.append(rule["scope"] + ": " + rule["rule"])
    return out


_TYPE_CATS = ("bool", "num", "str", "unit", "file")


def _type_cat(t):
    """把值类型归到粗类目。认不出来返回 None —— 不参与比较，避免命名差异造成噪音。

    只认 5 类：bool / num / str / unit / file。
    像 `price` vs `price(s)`、`tags`、`memories` 这类只是叫法不同，一律不判冲突。
    """
    t = (t or "").lower().strip()
    if not t:
        return None
    if "bool" in t:
        return "bool"
    if t in ("float", "number", "int") or "number" in t:
        return "num"
    if "string" in t or t in ("text", "localestring"):
        return "str"
    if t == "unit" or t == "unit[]":
        return "unit"
    if "image" in t or "file" in t:
        return "file"
    return None


_VER_RX = re.compile(r"1\.1[3-5](?:p\d+)?")


def _version_mentions(cn_rows):
    """从中文表正文里捞出提到的版本号。

    中文表**没有版本字段**（只有 描述/值类型/正确例子/错误例子/约束），
    所以「两张表的版本声明对比」在数据上做不到 —— 不要假装能做。

    能做的只是：把正文里提到的版本号连同上下文摆出来，让人自己看。
    比如 setFlag 的「版本差异：1.15 之前范围为 0-31，1.15 起改为无限制」，
    这是**行为变更**说明，不是「从该版本开始存在」的声明，两者不能混为一谈。
    """
    out = []
    seen = set()
    for row in cn_rows:
        blob = " ".join(filter(None, [row.get("description"), row.get("value_type")] +
                              list(row.get("constraints") or [])))
        if not blob.strip():
            continue
        versions = _VER_RX.findall(blob)
        if not versions:
            continue
        key = (tuple(versions), blob[:60])
        if key in seen:
            continue
        seen.add(key)
        out.append({"versions": versions, "text": blob.strip()[:160]})
    return out


def _dedup(seq):
    seen, out = set(), []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ---------------------------------------------------------------- lookup_key


def _section_letter(section):
    text = (section or "").strip().strip("[]")
    if len(text) == 1 and text.upper() in rw_lint.FAMILY_NAMES:
        return text.upper()
    if text.lower() in ("leg", "arm", "leg/arm"):
        return "I"
    return rw_lint.section_family(text)


def _brief_key(result):
    if not result.get("found"):
        return result
    out = {k: v for k, v in result.items() if k not in ("csv", "cn", "related", "linter_known", "suggestions")}
    entries, seen = [], set()
    rows = result["cn"] or result["csv"]
    for row in rows:
        family = row.get("chapter") or rw_lint.section_family(row.get("section")) or ""
        if family in seen:
            continue
        seen.add(family)
        description = " ".join((row.get("description") or row.get("gloss") or "").split())
        examples = row.get("correct_examples") or [row.get("example") or ""]
        example = next((v for v in examples if v), "")
        entry = {"section": family,
                 "description": description if len(description) <= 200 else description[:199] + "…",
                 "example": example if len(example) <= 200 else ""}
        if len(example) > 200:
            # 不能给半段可复制的配置代码；长例子请从 full 模式取完整版本。
            entry["example_omitted"] = True
        if row.get("chapter"):
            entry["cn_line"] = row["line"]
        else:
            entry["csv_row"] = row["row"]
        if len(description) > 200 or len(example) > 200:
            entry["truncated"] = True
        entries.append(entry)
    for field in ("version_mentions", "versions", "value_types", "constraints", "notes"):
        if not out.get(field):
            out.pop(field, None)
    out["entries"] = entries[:3]
    out["detail"] = "brief"
    out["details_available"] = bool(result["csv"] or result["cn"])
    if len(entries) > 3:
        out["entries_omitted"] = len(entries) - 3
        out["notes"] = out.get("notes", []) + ["存在更多节的释义；传 section 缩小范围，或 detail=full 查看全部。"]
    return out


def lookup_key(key="", max_suggestions=5, keys=None, section="", detail="brief"):
    """默认简洁条目；原始中英文资料通过 detail=full 获取。旧位置参数仍兼容。"""
    def run():
        mode = (detail or "brief").lower()
        if mode not in ("brief", "full"):
            return {"ok": False, "error": "detail 必须是 brief 或 full"}
        family = _section_letter(section) if section else None
        if section and not family:
            return {"ok": False, "error": "无法识别 section，请传 attack/action 等节名或 A–U 章节字母"}

        def one(value):
            result = _lookup_key_full(value, max_suggestions, family)
            return _brief_key(result) if mode == "brief" else result

        if keys is not None:
            if not isinstance(keys, (list, tuple)) or not keys or any(not isinstance(k, str) for k in keys):
                return {"ok": False, "error": "keys 必须是非空字符串列表"}
            unique = list(dict.fromkeys(keys))
            if len(unique) > 32:
                return {"ok": False, "error": "一次最多查询 32 个不同的键，请分批"}
            got = {k: one(k) for k in unique}
            missing = [k for k, value in got.items() if not value.get("found")]
            return {"ok": all(v.get("ok") for v in got.values()), "count": len(unique),
                    "requested_count": len(keys), "found": len(unique) - len(missing),
                    "missing": missing, "detail": mode, "results": got}
        return one(key)
    return _safe("lookup_key", run)


def _lookup_key_full(key="", max_suggestions=5, family=None):
    def run():
        q = (key or "").strip()
        if not q:
            return {"ok": False, "error": "key 不能为空"}
        ds = dataset.get_dataset()
        low = q.lower()
        n_sug = _clamp(max_suggestions, 1, 20, 5)

        match = None
        ambiguous = []
        if low in ds.cn_entries or low in ds.csv_rows or low in ds.jar_keys:
            match = "exact"
        elif any(s.lower() == low for s in ds.spellings):
            match = "case"
        else:
            # 兜底匹配：只忽略下划线和大小写，**绝不剥数字**。
            # 剥数字会把 customTarget1 / customTarget2 混成一个，
            # 而这类"查到了但答错"比查不到更难排查。
            norm = low.replace("_", "")
            cands = [s for s in ds.spellings if s.lower().replace("_", "") == norm]
            if len(cands) == 1:
                low, match = cands[0].lower(), "normalized"
            elif len(cands) > 1:
                # 多个候选一律不猜，把选择权交回去
                ambiguous = sorted(cands)[:10]

        if match is None:
            near = difflib.get_close_matches(q, ds.spellings, n=n_sug, cutoff=0.6)
            if ambiguous:
                return {
                    "ok": True, "query": key, "found": False, "match": "ambiguous", "key": None,
                    "ambiguous": [{"key": s,
                                   "sections": [x["letter"] for x in _sections_of(s.lower())]}
                                  for s in ambiguous],
                    "suggestions": [],
                    "notes": ["查询归一化后同时匹配多个键，无法判断你要哪个 —— "
                              "请从 ambiguous 里挑一个完整拼写再查。"],
                }
            return {
                "ok": True, "query": key, "found": False, "match": "none", "key": None,
                "suggestions": [{"key": s, "sections": [x["letter"] for x in _sections_of(s.lower())]}
                                for s in near],
                "notes": ["当前资料未收录；这不等于引擎一定不支持。事件/函数可用 get_ref(topic=events/functions, name=...) 查询。"],
            }

        csv_rows = ds.csv_rows.get(low, [])
        cn_rows = ds.cn_entries.get(low, [])
        canonical = (ds.cn_canon.get(low) if isinstance(ds.cn_canon, dict) else None) \
            or (csv_rows[0]["spelling"] if csv_rows else None) \
            or (cn_rows[0]["spelling"] if cn_rows else None) \
            or key

        available_sections = _sections_of(low)
        if family:
            csv_rows = [r for r in csv_rows if rw_lint.section_family(r.get("section")) == family]
            cn_rows = [r for r in cn_rows if r.get("chapter") == family]
        versions = [r["version"] for r in csv_rows if r.get("version")]
        order = {v: i for i, v in enumerate(rw_lint.VERSION_ORDER)}
        versions = sorted(_dedup(versions), key=lambda v: (order.get(v, 99), v))

        if match in ("exact", "case"):
            match = "exact" if q == canonical else "case"

        related = []
        if len(canonical) >= 5:
            pref = canonical[:6].lower()
            related = [s for s in ds.spellings
                       if s.lower().startswith(pref) and s.lower() != low][:8]

        # 两张表交叉校验：只被一张收录，说明表本身有缺口或版本不同步。
        # 工具**无法判断谁对**，只能把这个事实摆出来，不替使用者背书。
        has_csv, has_cn = bool(csv_rows), bool(cn_rows)
        agreement = ("both" if has_csv and has_cn
                     else "csv_only" if has_csv
                     else "cn_only" if has_cn
                     else "section_unconfirmed" if family else "jar_only")
        conflicts = []
        if has_csv and has_cn:
            csv_cats = {_type_cat(r.get("value_type")) for r in csv_rows} - {None}
            cn_cats = {_type_cat(r.get("value_type")) for r in cn_rows} - {None}
            if csv_cats and cn_cats and not (csv_cats & cn_cats):
                conflicts.append({
                    "field": "value_type",
                    "csv": _dedup([r.get("value_type") for r in csv_rows]),
                    "cn": _dedup([r.get("value_type") for r in cn_rows]),
                    "note": "两张表对同一个键的类型说法互斥 —— 谁对需要你自己判断",
                })

        warnings = []
        if agreement == "csv_only":
            warnings.append("只有官方 CSV 收录，中文表没有 —— 可能是中文表缺条目或版本不同步")
        elif agreement == "cn_only":
            warnings.append("只有中文表收录，官方 CSV 没有 —— 可能是 CSV 缺条目或版本不同步")
        elif agreement == "jar_only":
            warnings.append("只在游戏二进制里出现过，两份代码表都没收录 —— 说明文字不可信")

        if family and not (csv_rows or cn_rows):
            warnings.append("已找到这个键，但资料没有证明它属于指定节；不要把 found=true 当作该节可用的保证。")
        if not family and len(available_sections) > 1:
            warnings.append("这个键用于多个节；释义按节区分，建议传 section。")
        result = {
            "ok": True, "query": key, "found": True, "match": match,
            "key": canonical,
            "agreement": agreement,
            "conflicts": conflicts,
            "version_mentions": _version_mentions(cn_rows),
            "warnings": warnings,
            "sections": [v for v in available_sections if not family or v["letter"] == family],
            "versions": versions,
            "value_types": _dedup([r["value_type"] for r in csv_rows + cn_rows]),
            "sources": {"csv": bool(csv_rows), "cn": bool(cn_rows),
                        "jar": low in ds.jar_keys},
            "linter_known": low in ds.known,
            "csv": csv_rows,
            "cn": cn_rows,
            "related": related,
            "notes": _notes_for(low, family),
            "suggestions": [], "detail": "full",
            # 即使简洁模式也保留所有约束，不能为了省返回而隐去限制。
            "constraints": _dedup("[%s] %s" % (r["chapter"], value)
                                  for r in cn_rows for value in r.get("constraints", [])),
        }
        if family:
            result["section_match"] = bool(csv_rows or cn_rows)
            result["available_sections"] = available_sections
        return result

    return _safe("lookup_key", run)


# ---------------------------------------------------------------- search_source


def search_source(pattern="", regex=False, case_sensitive=False,
                  path_filter="", max_results=10, mode="", patterns=None,
                  context_lines=2, offset=0, max_chars=8000):
    return _safe("search_source", source_search.search, pattern, regex, case_sensitive,
                 path_filter, max_results, mode, patterns, context_lines, offset, max_chars)


# ---------------------------------------------------------------- explain_actions


def explain_actions(path, action=None, fmt="text"):
    def run():
        t0 = time.perf_counter()
        target, tried = resolve_target(path)
        if target is None:
            return {"ok": False, "error": "路径不存在", "tried": tried}
        res = rw_explain.explain(target, action, as_json=True)
        if not res.get("ok"):
            res["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
            return res

        summary = {
            "actions": sum(1 for n in res["nodes"].values()
                           if n["kind"] in ("action", "hiddenAction")),
            "entries": len(res["entries"]),
            "findings": len(res["findings"]),
            "by_rule": {r: sum(1 for f in res["findings"] if f["rule"] == r)
                        for r in sorted({f["rule"] for f in res["findings"]})},
        }
        text = rw_explain.render_text(res, action)
        elapsed = int((time.perf_counter() - t0) * 1000)

        mode = (fmt or "text").lower()
        if mode in ("json", "both"):
            out = dict(res)
            out.pop("text", None)
            out["summary"] = summary
            out["elapsed_ms"] = elapsed
            if mode == "both":
                out["text"] = text
            return out

        # 默认只给文本图。整份 nodes 是同一张图的 JSON 形态，两样都返回等于
        # 让调用方为一张图付两遍钱（实测 3078 → 700 左右）。
        return {
            "ok": True, "file": res.get("file"), "text": text,
            "findings": res.get("findings") or [],
            "summary": summary, "elapsed_ms": elapsed,
        }

    return _safe("explain_actions", run)


# ---------------------------------------------------------------- get_ref


def get_ref(topic="", name=""):
    return _safe("get_ref", reference_query.query, topic, name)


# ---------------------------------------------------------------- lint


def lint(path="", only="all", max_issues=100, paths=None):
    def run():
        n_max = _clamp(max_issues, 1, 1000, 100)

        # 批量：一次调用检查多个文件/目录，省掉 agent 来回往返
        raw_targets = list(paths) if paths else ([path] if path else [])
        if not raw_targets:
            return {"ok": False, "error": "需要 path 或 paths"}

        resolved, missing = [], []
        for p in raw_targets:
            t, tried = resolve_target(p)
            if t is None:
                missing.append({"path": p, "tried": tried})
            else:
                resolved.append((p, t))
        if not resolved:
            return {"ok": False, "error": "路径不存在", "missing": missing}

        t0 = time.perf_counter()
        all_issues, skipped, per_target = [], [], []
        scanned = 0
        errors = warnings = 0
        cache_tot = {"enabled": False, "hits": 0, "misses": 0}
        last = {}

        for p, t in resolved:
            # 不传 jar_path：与 CLI 默认行为一致，保证同一目录在两边得到相同的计数。
            res = rw_lint.run_lint(t)
            if not res["ok"]:
                per_target.append({"path": p, "ok": False, "error": res.get("error")})
                continue
            last = res
            all_issues += res["issues"]
            skipped += res["skipped"]
            scanned += res["files"]
            errors += res["errors"]
            warnings += res["warnings"]
            c = res.get("cache") or {}
            if c.get("enabled"):
                cache_tot["enabled"] = True
                cache_tot["hits"] += c.get("hits", 0)
                cache_tot["misses"] += c.get("misses", 0)
            per_target.append({"path": p, "ok": True, "files": res["files"],
                               "errors": res["errors"], "warnings": res["warnings"],
                               "elapsed_ms": res.get("elapsed_ms", 0)})
            if len(resolved) > 1 and "core" in res:
                per_target[-1]["core"] = res["core"]

        shown = all_issues
        if only in ("errors", "error"):
            shown = [i for i in all_issues if i.level == "error"]
        elif only in ("warnings", "warning"):
            shown = [i for i in all_issues if i.level == "warning"]

        all_issues.sort(key=lambda i: (i.path, i.line))
        shown.sort(key=lambda i: (i.path, i.line))
        dur = int((time.perf_counter() - t0) * 1000)

        # 每条 issue 都带一遍完整绝对路径太贵了：62 字符的路径重复 200 次，
        # 光路径就吃掉六千多 token。改成「文件表 + 下标」，路径只出现一次。
        picked = shown[:n_max]
        file_idx, file_list = {}, []
        for it in picked:
            key = it.path
            if key not in file_idx:
                file_idx[key] = len(file_list)
                try:
                    file_list.append(os.path.relpath(key, dataset.ROOT))
                except ValueError:            # 跨盘符，relpath 会抛
                    file_list.append(key)

        out = {
            "ok": True,
            "target": resolved[0][1] if len(resolved) == 1 else None,
            "targets": per_target,
            "files": scanned, "scanned_files": scanned,
            "errors": errors, "warnings": warnings,
            "issue_files": file_list,
            "issues": [{"f": file_idx[i.path], "line": i.line, "code": i.code,
                        "level": i.level, "message": i.msg} for i in picked],
            "issues_total": len(shown), "issues_returned": len(picked),
            "truncated": len(shown) > n_max,
            # 按规则号汇总。被截断时也能一眼看出问题分布，决定要不要缩小范围再查。
            # 统计的是**过滤后**的集合，和 issues_total 口径一致。
            "by_code": {c: n for c, n in sorted(
                ((c, sum(1 for i in shown if i.code == c))
                 for c in {i.code for i in shown}))},
            "skipped": skipped,
            "elapsed_ms": dur, "duration_ms": dur,
            "cache": cache_tot,
        }
        if len(resolved) == 1:
            # 单目标时保留键名资料，批量时没有单一含义就省略
            out["key_sources"] = last.get("key_sources") or {}
            if "core" in last:
                out["core"] = last["core"]
        if missing:
            out["missing"] = missing
        return out

    return _safe("lint", run)
