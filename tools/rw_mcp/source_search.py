# -*- coding: utf-8 -*-
"""有界源码检索：保留旧匹配字段，增加上下文、批量、分页和空结果提示。"""

import difflib
import json
import re
import time

from . import dataset


def _limit(value, low, high, default):
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


def _size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def search(pattern="", regex=False, case_sensitive=False, path_filter="", max_results=10,
           mode="", patterns=None, context_lines=2, offset=0, max_chars=8000):
    chosen = (mode or ("regex" if regex else "literal")).lower()
    if chosen not in ("literal", "regex"):
        return {"ok": False, "error": "mode 必须是 literal 或 regex"}
    if mode and chosen == "literal" and regex:
        return {"ok": False, "error": "mode=literal 与旧参数 regex=true 冲突，请只使用一种模式参数"}
    raw = patterns if patterns is not None else [pattern]
    if not isinstance(raw, (list, tuple)) or not raw or any(not isinstance(p, str) or not p for p in raw):
        return {"ok": False, "error": "需要非空 pattern 或非空字符串列表 patterns"}
    queries = list(dict.fromkeys(raw))
    if len(queries) > 8 or any(len(p) > 200 for p in queries):
        return {"ok": False, "error": "一次最多 8 个不同的 pattern，每个上限 200 字符"}
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regexes = [re.compile(p if chosen == "regex" else re.escape(p), flags) for p in queries]
    except re.error as e:
        return {"ok": False, "error": "正则不合法: %s" % e}

    count_limit = _limit(max_results, 1, 200, 10)
    context = _limit(context_lines, 0, 5, 2)
    page_offset = _limit(offset, 0, 10**9, 0)
    char_limit = _limit(max_chars, 1000, 20000, 8000)
    flt = (path_filter or "").replace("\\", "/").lower()
    start = time.perf_counter()
    lines = dataset.get_java_lines()
    scanned, matches = set(), []
    counts = [0] * len(queries)
    total = 0
    used_chars = 2                     # matches 的 JSON 数组括号
    budget_exhausted = False
    single = regexes[0] if len(regexes) == 1 else None
    for index, (rel, lineno, text) in enumerate(lines):
        if flt and flt not in rel.lower():
            continue
        scanned.add(rel)
        if single is not None:
            matched = [0] if single.search(text) else []
        else:
            matched = [n for n, rx in enumerate(regexes) if rx.search(text)]
        if not matched:
            continue
        total += 1
        for n in matched:
            counts[n] += 1
        if total <= page_offset or len(matches) >= count_limit or budget_exhausted:
            continue
        item = {"file": rel, "line": lineno, "text": text.strip()[:300]}
        if len(text.strip()) > 300:
            item["text_truncated"] = True
        if len(queries) > 1:
            item["patterns"] = [queries[n] for n in matched]
        if context:
            before = [row[2] for row in lines[max(0, index - context):index] if row[0] == rel]
            after = [row[2] for row in lines[index + 1:index + context + 1] if row[0] == rel]
            item["before"] = [line[:300] for line in before]
            item["after"] = [line[:300] for line in after]
            if any(len(line) > 300 for line in before + after):
                item["context_truncated"] = True
        size = _size(item) + (1 if matches else 0)
        if used_chars + size > char_limit and not matches:
            # 第一条也装不下时先省略上下文，避免不断返回同一个空页面。
            item.pop("before", None)
            item.pop("after", None)
            item["context_truncated"] = True
            size = _size(item)
        if used_chars + size > char_limit:
            budget_exhausted = True
            continue
        matches.append(item)
        used_chars += size

    hints = []
    reason = None
    path_suggestions = []
    if not lines:
        reason = "source_unavailable"
        hints.append("没有可检索的 Java 源码；先运行 bootstrap.py --decompile，完成后重启 MCP。")
    elif not scanned:
        reason = "path_filter_no_files"
        hints.append("path_filter 没有匹配任何 Java 文件；它是相对路径子串，不是 glob。可清空后重查。")
        paths = sorted({row[0] for row in lines})
        path_suggestions = difflib.get_close_matches(path_filter.replace("\\", "/"), paths, n=3, cutoff=0.35)
    elif not total:
        reason = "no_match"
        hints.append("已扫描匹配路径，但没有命中；这不等于该 API 不存在，反编译标识符可能已混淆。")
    if chosen == "literal" and any("|" in q or "\\" in q or ".*" in q or "(?" in q for q in queries):
        hints.append("literal 按原文搜索，不解释转义或 A|B。正则请设 mode=regex；多个普通词请用 patterns。")
        if any(r"%\{" in q for q in queries):
            hints.append("要按原文找 %{，pattern 应直接写 %{，不要写 %\\{。")
    if budget_exhausted and not matches:
        hints.append("单条匹配也超过 max_chars，请增大该内容预算；当前没有可继续的分页游标。")
    elif budget_exhausted:
        hints.append("达到匹配内容字符预算；可用 next_offset 翻页，或缩小路径/搜索范围。")
    truncated = total > page_offset + len(matches)
    result = {
        "ok": True, "pattern": pattern if patterns is None else "", "mode": chosen,
        "case_sensitive": bool(case_sensitive), "root": dataset.JAVA_SRC,
        "path_filter": path_filter or "", "files_scanned": len(scanned),
        "total_matches": total, "returned": len(matches), "truncated": truncated,
        "offset": page_offset, "next_offset": page_offset + len(matches) if truncated and matches else None,
        "context_lines": context, "content_chars": used_chars, "max_chars": char_limit,
        "budget_exhausted": budget_exhausted, "reason": reason, "hints": hints,
        "elapsed_ms": int((time.perf_counter() - start) * 1000), "matches": matches,
    }
    if patterns is not None:
        result["patterns"] = queries
        result["by_pattern"] = dict(zip(queries, counts))
    if path_suggestions:
        result["path_suggestions"] = path_suggestions
    return result
