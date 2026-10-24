# -*- coding: utf-8 -*-
"""只筛选已有速查资料，不把名字匹配冒充经过验证的完整运行时语义。"""

import difflib
import rw_lint


_ALIASES = {
    "event": "events", "function": "functions", "enum": "enums",
    "memory": "memory_types", "section": "sections", "versions": "version_order",
    "numeric": "plain_numeric_keys",
}
TOPICS = ("events", "functions", "enums", "memory_types", "sections", "rules",
          "must_pair", "hard_constraints", "nonexistent_functions", "math_extra",
          "version_order", "plain_numeric_keys")


def _rule_matches(rule, name):
    low = name.lower()
    return (any(low == key.lower() for key in rule.get("keys", []))
            or low in rule.get("scope", "").lower())


def _filter(data, name):
    if not name:
        return data
    low = name.lower()
    if isinstance(data, list):
        return [item for item in data if (_rule_matches(item, name) if isinstance(item, dict)
                                         else str(item).lower() == low)]
    if isinstance(data, dict):
        exact = {key: value for key, value in data.items() if key.lower() == low}
        if exact:
            return exact
        out = {}
        for key, value in data.items():
            if key.lower() == low or (isinstance(value, str) and low in value.lower()):
                out[key] = value
            elif isinstance(value, list):
                found = _filter(value, name)
                if found:
                    out[key] = found
        return out
    return data if str(data).lower() == low else None


def _candidates(data):
    if isinstance(data, dict):
        return list(data)
    return [str(v) for v in data if not isinstance(v, dict)]


def query(topic="", name=""):
    payload = rw_lint.ref_payload()
    chosen = (topic or "all").strip().lower()
    chosen = _ALIASES.get(chosen, chosen)
    if chosen == "all":
        if name:
            return {"ok": False, "error": "按 name 查询时请指定 topic", "topics": list(TOPICS)}
        payload["ok"] = True
        payload["generated_from"] = "rw_lint.ref_payload"
        payload["counts"] = {
            "events": len(payload["events"]), "functions": len(payload["functions"]),
            "sections": len(payload["sections"]),
            "must_pair": len(payload["rules"]["must_pair"]),
            "hard_constraints": len(payload["rules"]["hard_constraints"]),
        }
        return payload
    if chosen not in TOPICS:
        return {"ok": False, "error": "未知 topic", "topics": list(TOPICS)}
    data = payload["rules"][chosen] if chosen in ("must_pair", "hard_constraints") else payload[chosen]
    lookup = name.strip()
    array = chosen == "memory_types" and lookup.endswith("[]")
    if array:
        lookup = lookup[:-2]
    if chosen == "sections" and lookup:
        family = rw_lint.section_family(lookup.strip("[]"))
        lookup = family or lookup
    if chosen == "math_extra":
        items = {"names": _filter(data["names"], lookup), "note": data["note"]}
        found = bool(items["names"])
    else:
        items = _filter(data, lookup)
        found = bool(items)
    result = {"ok": True, "topic": chosen, "name": name, "found": found,
              "items": items, "generated_from": "rw_lint.ref_payload"}
    if array:
        result["array"] = True
    if not found:
        candidates = _candidates(data)
        by_lower = {v.lower(): v for v in candidates}
        near = difflib.get_close_matches(lookup.lower(), list(by_lower), n=5, cutoff=0.6)
        result["suggestions"] = [by_lower[v] for v in near]
        if chosen == "functions" and lookup.lower() in {v.lower() for v in payload["nonexistent_functions"]}:
            result["known_unavailable"] = True
            result["notes"] = ["该名称在当前资料的 nonexistent_functions 中，不要按已支持的逻辑函数使用。"]
        else:
            result["notes"] = ["当前速查资料没有匹配条目；不能据此推断引擎一定不支持。"]
    elif chosen in ("events", "functions"):
        result["notes"] = ["这里只确认速查表中的名称；没有记录的接收者、参数或运行时语义不作推断。"]
    if lookup:
        rules = [rule for group in payload["rules"].values() for rule in group
                 if _rule_matches(rule, lookup)]
        if rules and chosen not in ("rules", "must_pair", "hard_constraints"):
            result["related_rules"] = rules
    return result
