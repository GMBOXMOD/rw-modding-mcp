# -*- coding: utf-8 -*-
"""四个只读工具的实现。

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
from . import dataset

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
    letters = dataset.get_dataset().key_families.get(low) or set()
    return [{"letter": ch, "name": rw_lint.FAMILY_NAMES.get(ch, ch)}
            for ch in sorted(letters)]


def _notes_for(low):
    out = []
    for rule in rw_lint.REF_RULES["must_pair"]:
        if any(k.lower() == low for k in rule["keys"]):
            out.append(rule["note"])
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


def lookup_key(key, max_suggestions=5):
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
                "notes": ["三份资料都没有这个键。luke 语里拼错不会报错，只会静默失效。"],
            }

        csv_rows = ds.csv_rows.get(low, [])
        cn_rows = ds.cn_entries.get(low, [])
        canonical = (ds.cn_canon.get(low) if isinstance(ds.cn_canon, dict) else None) \
            or (csv_rows[0]["spelling"] if csv_rows else None) \
            or (cn_rows[0]["spelling"] if cn_rows else None) \
            or key

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
                     else "jar_only")
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

        return {
            "ok": True, "query": key, "found": True, "match": match,
            "key": canonical,
            "agreement": agreement,
            "conflicts": conflicts,
            "version_mentions": _version_mentions(cn_rows),
            "warnings": warnings,
            "sections": _sections_of(low),
            "versions": versions,
            "value_types": _dedup([r["value_type"] for r in csv_rows]),
            "sources": {"csv": bool(csv_rows), "cn": bool(cn_rows),
                        "jar": low in ds.jar_keys},
            "linter_known": low in ds.known,
            "csv": csv_rows,
            "cn": cn_rows,
            "related": related,
            "notes": _notes_for(low),
            "suggestions": [],
        }

    return _safe("lookup_key", run)


# ---------------------------------------------------------------- search_source


def search_source(pattern, regex=False, case_sensitive=False,
                  path_filter="", max_results=50):
    def run():
        pat = pattern or ""
        if not pat:
            return {"ok": False, "error": "pattern 不能为空"}
        if len(pat) > 200:
            return {"ok": False, "error": "pattern 太长（上限 200 字符）"}
        n_max = _clamp(max_results, 1, 200, 50)

        flags = 0 if case_sensitive else re.IGNORECASE
        if regex:
            try:
                rx = re.compile(pat, flags)
            except re.error as e:
                return {"ok": False, "error": "正则不合法: %s" % e}
            mode = "regex"
        else:
            rx = re.compile(re.escape(pat), flags)
            mode = "literal"

        t0 = time.time()
        lines = dataset.get_java_lines()
        flt = (path_filter or "").replace("\\", "/").lower()

        scanned = set()
        matches = []
        total = 0
        for rel, lineno, text in lines:
            if flt and flt not in rel.lower():
                continue
            scanned.add(rel)
            if rx.search(text):
                total += 1
                if len(matches) < n_max:
                    matches.append({"file": rel, "line": lineno,
                                    "text": text.strip()[:300]})

        return {
            "ok": True, "pattern": pattern, "mode": mode,
            "case_sensitive": bool(case_sensitive),
            "root": dataset.JAVA_SRC, "path_filter": path_filter or "",
            "files_scanned": len(scanned), "total_matches": total,
            "returned": len(matches), "truncated": total > len(matches),
            "elapsed_ms": int((time.time() - t0) * 1000),
            "matches": matches,
        }

    return _safe("search_source", run)


# ---------------------------------------------------------------- explain_actions


def explain_actions(path, action=None):
    def run():
        target, tried = resolve_target(path)
        if target is None:
            return {"ok": False, "error": "路径不存在", "tried": tried}
        res = rw_explain.explain(target, action, as_json=True)
        if not res.get("ok"):
            return res
        # 给调用方一个直接可读的文本版，JSON 版保留完整结构
        res["text"] = rw_explain.render_text(res, action)
        res["summary"] = {
            "actions": sum(1 for n in res["nodes"].values()
                           if n["kind"] in ("action", "hiddenAction")),
            "entries": len(res["entries"]),
            "findings": len(res["findings"]),
            "by_rule": {r: sum(1 for f in res["findings"] if f["rule"] == r)
                        for r in sorted({f["rule"] for f in res["findings"]})},
        }
        return res

    return _safe("explain_actions", run)


# ---------------------------------------------------------------- get_ref


def get_ref():
    def run():
        p = rw_lint.ref_payload()
        p["ok"] = True
        p["generated_from"] = "rw_lint.ref_payload"
        p["counts"] = {
            "events": len(p["events"]),
            "functions": len(p["functions"]),
            "sections": len(p["sections"]),
            "must_pair": len(p["rules"]["must_pair"]),
            "hard_constraints": len(p["rules"]["hard_constraints"]),
        }
        return p

    return _safe("get_ref", run)


# ---------------------------------------------------------------- lint


def lint(path, only="all", max_issues=200):
    def run():
        n_max = _clamp(max_issues, 1, 1000, 200)
        target, tried = resolve_target(path)
        if target is None:
            return {"ok": False, "error": "路径不存在", "tried": tried}

        t0 = time.time()
        # 不传 jar_path：与 CLI 默认行为一致，保证同一目录在两边得到相同的计数。
        res = rw_lint.run_lint(target)
        dur = int((time.time() - t0) * 1000)

        if not res["ok"]:
            return {"ok": False, "error": res.get("error") or "检查失败",
                    "target": target, "tried": tried}

        issues = res["issues"]
        if only in ("errors", "error"):
            issues = [i for i in issues if i.level == "error"]
        elif only in ("warnings", "warning"):
            issues = [i for i in issues if i.level == "warning"]

        return {
            "ok": True, "target": target,
            "files": res["files"], "errors": res["errors"], "warnings": res["warnings"],
            "issues": [i.as_dict() for i in issues[:n_max]],
            "issues_total": len(issues), "issues_returned": min(len(issues), n_max),
            "truncated": len(issues) > n_max,
            "skipped": res["skipped"],
            "key_sources": res["key_sources"],
            "assets": res["assets"],
            "duration_ms": dur,
        }

    return _safe("lint", run)
