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
        if low in ds.cn_entries or low in ds.csv_rows or low in ds.jar_keys:
            match = "exact"
        elif any(s.lower() == low for s in ds.spellings):
            match = "case"
        else:
            norm = re.sub(r"[_0-9]", "", low)
            for cand in ds.spellings:
                if re.sub(r"[_0-9]", "", cand.lower()) == norm:
                    low, match = cand.lower(), "normalized"
                    break

        if match is None:
            near = difflib.get_close_matches(q, ds.spellings, n=n_sug, cutoff=0.6)
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

        return {
            "ok": True, "query": key, "found": True, "match": match,
            "key": canonical,
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
