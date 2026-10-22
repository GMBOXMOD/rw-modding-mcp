#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rw_mcp 自检。全只读。

    python tools/rw_mcp/selftest.py            # 直接调用 impl（不需要装 mcp SDK）
    python tools/rw_mcp/selftest.py --stdio    # 起真实 stdio 服务，走 MCP 协议
    python tools/rw_mcp/selftest.py --time     # 冷启动计时
"""

import argparse
import asyncio
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from rw_mcp import impl, dataset  # noqa: E402

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  PASS  %s" % name)
    else:
        FAIL += 1
        print("  FAIL  %s %s" % (name, detail))


def run_direct():
    print("== 直接调用 impl ==")
    info = dataset.describe()
    print("  数据源：CSV=%s 键 / 中文表=%s 键 / 二进制=%s 键"
          % (info["counts"]["csv_rows"], info["counts"]["cn_entries"], info["counts"]["jar_keys"]))
    print("  root=%s" % info["root"])

    r = impl.lookup_key("canAttack")
    check("lookup_key(canAttack) 找到", r.get("found") is True, r)
    check("  → 规范拼写正确", r.get("key") == "canAttack", r.get("key"))
    check("  → 归属 D 章(attack)", any(s["letter"] == "D" for s in r.get("sections", [])), r.get("sections"))
    # jar 数据源只在找得到 game-lib.jar 时才要求（CI / Linux 上通常没有）
    if dataset.JAR_PATH:
        check("  → 三个数据源都有", all(r.get("sources", {}).values()), r.get("sources"))
    else:
        check("  → CSV 与中文表都有",
              bool(r.get("sources", {}).get("csv")) and bool(r.get("sources", {}).get("cn")),
              r.get("sources"))
        print("  SKIP  jar 数据源：没找到 game-lib.jar（设 RW_GAME_JAR 可覆盖）")

    r = impl.lookup_key("canattack")
    check("lookup_key(canattack) 大小写归一", r.get("match") in ("case", "normalized"), r.get("match"))

    r = impl.lookup_key("canAtack")
    check("lookup_key(canAtack) 未找到但有建议",
          r.get("found") is False and any(s["key"].lower() == "canattack" for s in r.get("suggestions", [])),
          r.get("suggestions"))

    r = impl.lookup_key("layer")
    check("lookup_key(layer) 归属 Q 章(decal)",
          any(s["letter"] == "Q" for s in r.get("sections", [])), r.get("sections"))
    check("  → 版本含 1.15p9", "1.15p9" in (r.get("versions") or []), r.get("versions"))

    r = impl.lookup_key("isVisible")
    check("lookup_key(isVisible) 多条中文释义", len(r.get("cn") or []) >= 4, len(r.get("cn") or []))

    r = impl.lookup_key("displayText")
    check("lookup_key(displayText) 命中占位符别名", bool(r.get("cn")), r.get("cn"))

    # 归一化兜底：多个候选时必须拒绝猜测，不能静默取第一个
    r = impl.lookup_key("m_ax")
    check("lookup_key(m_ax) 报歧义而不是瞎猜",
          r.get("match") == "ambiguous" and len(r.get("ambiguous") or []) >= 2,
          r.get("match"))

    # 不许剥数字：customTarget1 / customTarget2 是两个键
    r = impl.lookup_key("customTarget")
    check("lookup_key(customTarget) 不误匹配到 customTarget1",
          r.get("found") is False, r.get("key"))

    # 两张表交叉校验
    r = impl.lookup_key("layer")
    check("lookup_key 带 agreement 字段", r.get("agreement") in
          ("both", "csv_only", "cn_only", "jar_only"), r.get("agreement"))
    check("lookup_key 带 conflicts 字段", isinstance(r.get("conflicts"), list), r.get("conflicts"))

    # 两张表类型互斥的已知样本（CSV 说 float，中文表说 boolean）
    r = impl.lookup_key("energyNeedstoRechargeToFull")
    check("lookup_key 能报出两表类型冲突", len(r.get("conflicts") or []) >= 1, r.get("conflicts"))

    # search_source 需要反编译产物；没跑过 --decompile 时跳过
    has_src = os.path.isdir(dataset.JAVA_SRC) and any(
        f.endswith(".java") for _dp, _dn, fns in os.walk(dataset.JAVA_SRC) for f in fns)

    if has_src:
        r = impl.search_source("addBooleanType")
        check("search_source(addBooleanType) 有命中", r.get("total_matches", 0) >= 1, r.get("total_matches"))
        check("  → 每条都有 file/line/text",
              all(m.get("file") and m.get("line") and m.get("text") is not None
                  for m in r.get("matches", [])))

        r = impl.search_source("autoTriggerOnEvent", path_filter="custom/")
        check("search_source 路径过滤生效", r.get("files_scanned", 0) < 1698, r.get("files_scanned"))
    else:
        print("  SKIP  search_source：没有反编译源码（跑 bootstrap.py --decompile 可生成）")

    r = impl.search_source("(", regex=True)
    check("search_source 非法正则返回 ok:false 不崩", r.get("ok") is False, r)

    r = impl.get_ref()
    check("get_ref 事件 18 个", len(r.get("events", [])) == 18, len(r.get("events", [])))
    check("get_ref 函数 27 个", len(r.get("functions", [])) == 27, len(r.get("functions", [])))
    check("get_ref 配对规则 4 条", len(r.get("rules", {}).get("must_pair", [])) == 4)

    # 下面两项依赖本地模组目录；别人克隆仓库后没有这些目录，跳过而不是报错
    koc = os.path.join(dataset.ROOT, "Kings of Cards")
    if os.path.isdir(koc):
        r = impl.lint("Kings of Cards")
        check("lint(Kings of Cards) 通过", r.get("ok") is True, r.get("error"))
        check("  → 15 文件 / 0 错误 / 16 警告",
              (r.get("files"), r.get("errors"), r.get("warnings")) == (15, 0, 16),
              (r.get("files"), r.get("errors"), r.get("warnings")))
    else:
        print("  SKIP  lint(Kings of Cards)：本地没有这个模组目录")

    ex = os.path.join(dataset.ROOT, "示例")
    if os.path.isdir(ex):
        r = impl.lint("示例")
        check("lint(示例) 5 个文件", r.get("ok") is True and r.get("files") == 5, r.get("files"))
    else:
        print("  SKIP  lint(示例)：本地没有这个目录")

    r = impl.lint("no-such-dir-xyz")
    check("lint(不存在路径) 返回 ok:false", r.get("ok") is False and "路径" in (r.get("error") or ""), r)

    if has_src:
        t0 = time.time()
        impl.search_source("addBooleanType")
        warm = (time.time() - t0) * 1000
        check("search_source 全树扫描 < 800ms", warm < 800, "%.0fms" % warm)


def _is_error(res):
    """mcp 1.x 用 isError，2.x 改成 is_error —— 两个都认。"""
    for attr in ("is_error", "isError"):
        v = getattr(res, attr, None)
        if v is not None:
            return bool(v)
    return False


def _payload(res):
    """把 CallToolResult 里的 JSON 文本解析出来。"""
    if not res.content:
        return None
    item = res.content[0]
    text = getattr(item, "text", None)
    if text is None:
        return None
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


async def run_stdio():
    print("== stdio 协议测试 ==")
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as e:
        print("  SKIP  没装 mcp SDK：%s" % e)
        return

    server = os.path.join(TOOLS, "rw_mcp_server.py")
    params = StdioServerParameters(
        command=sys.executable, args=[server],
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})

    # lint 用 fixtures，保证干净克隆 / CI 里也存在
    lint_target = os.path.normpath(os.path.join(TOOLS, "..", "tests", "fixtures"))
    if not os.path.isdir(lint_target):
        lint_target = os.path.join(TOOLS, "rw_lint.py")

    # (工具名, 参数, 额外要断言的字段)
    cases = [
        ("lookup_key", {"key": "layer"}, {"found": True, "key": "layer"}),
        ("search_source", {"pattern": "addBooleanType", "max_results": 3}, {}),
        ("get_ref", {}, {}),
        ("lint", {"path": lint_target}, {}),
    ]

    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            names = [t.name for t in tools.tools]
            check("恰好 4 个工具", len(names) == 4, names)
            check("工具名齐全",
                  set(names) == {"lookup_key", "search_source", "get_ref", "lint"}, names)

            for name, args, expect in cases:
                res = await s.call_tool(name, args)
                # 1) 协议层没报错
                check("%s 无协议错误" % name, _is_error(res) is False, _is_error(res))
                # 2) 业务层 ok 为真（bool(content) 判断不出这个）
                d = _payload(res)
                check("%s 返回可解析 JSON" % name, isinstance(d, dict), str(res.content)[:120])
                if not isinstance(d, dict):
                    continue
                check("%s ok=True" % name, d.get("ok") is True, d.get("error"))
                for k, v in expect.items():
                    check("%s.%s == %r" % (name, k, v), d.get(k) == v, d.get(k))


def run_time():
    print("== 冷启动计时 ==")
    t0 = time.time(); dataset.get_dataset(); t1 = time.time()
    print("  dataset 构建：%.0f ms" % ((t1 - t0) * 1000))
    t0 = time.time(); dataset.get_java_lines(); t1 = time.time()
    print("  Java 索引构建：%.0f ms（1,698 个文件）" % ((t1 - t0) * 1000))
    t0 = time.time(); impl.get_ref(); t1 = time.time()
    print("  get_ref：%.1f ms" % ((t1 - t0) * 1000))


def _force_utf8():
    """Windows 上默认 stdout 是 ANSI 代码页（en-US 是 cp1252），
    打印中文会 UnicodeEncodeError。CI 的 windows-latest 就是这样挂的。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main():
    _force_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdio", action="store_true", help="起真实服务走 MCP 协议")
    ap.add_argument("--time", action="store_true", help="冷启动计时")
    a = ap.parse_args()

    if a.time:
        run_time()
        return 0
    if a.stdio:
        asyncio.run(run_stdio())
    else:
        run_direct()

    print("\n%d PASS / %d FAIL" % (PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
