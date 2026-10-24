#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""铁锈战争模组 MCP 服务端（stdio）。

五个只读工具：
    lookup_key     查一个 luke 键的拼写 / 所属节 / 版本 / 类型 / 描述 / 例子
    search_source  在反编译的 Java 源码树里搜索
    get_ref        结构化速查表（事件 / 函数 / 枚举 / 内存类型 / 配对规则 / 硬限制）
    lint           对模组文件或目录跑静态检查

注册：把 bootstrap.py 的路径填进你所用 MCP 客户端的配置即可，见 README。
"""

import os
import sys
from typing import Literal

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# mcp 2.x 把 FastMCP 改名为 MCPServer；1.x 仍是 FastMCP。两条线都兼容。
# 先试 2.x：bootstrap 锁的是 mcp>=2.3,<3，反过来的话每次启动都要先付一次失败的导入。
try:
    from mcp.server import MCPServer as FastMCP        # mcp 2.x
except ImportError:                                    # pragma: no cover
    from mcp.server.fastmcp import FastMCP             # mcp 1.x

from rw_mcp import impl                               # noqa: E402

mcp = FastMCP("rusted-warfare-modding")


@mcp.tool()
def lookup_key(key: str = "", max_suggestions: int = 5,
               keys: list[str] | None = None, section: str = "",
               detail: Literal["brief", "full"] = "brief") -> dict:
    """查键。默认 brief：短释义、例子、来源、约束与资料冲突；full 返回原始中英文条目。
    section 用 attack/action 等节名或 A–U 字母消除多义；keys 一次查最多 32 个不同键。
    found 表示资料命中，不是游戏验证通过。"""
    return impl.lookup_key(key, max_suggestions, keys, section, detail)


@mcp.tool()
def search_source(pattern: str = "", regex: bool = False, case_sensitive: bool = False,
                  path_filter: str = "", max_results: int = 10, mode: Literal["literal", "regex"] | None = None,
                  patterns: list[str] | None = None, context_lines: int = 2,
                  offset: int = 0, max_chars: int = 8000) -> dict:
    """搜索 Java 源码并返回附近上下文。mode=literal/regex；旧 regex 参数仍可用。
    patterns 批量搜最多 8 个词；path_filter 是路径子串，不是 glob。默认 10 条、前后 2 行。
    max_chars 限制匹配内容字符数（不含元数据），截断用 next_offset 翻页。
    空结果查看 reason/hints；不要把零命中等同于 API 不存在。"""
    return impl.search_source(pattern, regex, case_sensitive, path_filter, max_results,
                              mode, patterns, context_lines, offset, max_chars)


@mcp.tool()
def explain_actions(path: str, action: str = "", fmt: str = "text") -> dict:
    """把事件/autoTrigger/按钮 → 动作 → alsoTriggerAction 的调用图画出来，标 repeat 次数、门控条件、
    @memory 读写；检查循环变量、不可达动作、未初始化 memory、下标、行尾注释和缺失动作引用。

    fmt: text（默认，只返回文本图 + 发现）/ json（返回完整结构）/ both。"""
    return impl.explain_actions(path, action or None, fmt)


@mcp.tool()
def get_ref(topic: str = "", name: str = "") -> dict:
    """按 topic 筛速查资料，可再用 name 精确查名称。常用 topic：events/functions/enums/memory/rules/sections。
    例如 topic=events,name=killedAnyUnit；topic=enums,name=movementType。不传参数兼容完整速查表。
    名称收录不代表完整运行时语义已经验证。"""
    return impl.get_ref(topic, name)


@mcp.tool()
def lint(path: str = "", only: str = "all", max_issues: int = 100,
         paths: list[str] | None = None) -> dict:
    """对模组文件或目录跑静态检查，返回结构化的 issues（错误/警告、文件、行号、说明）。

    issues 里的 f 是 issue_files 的下标，不是路径 —— 路径只在 issue_files 里出现一次。
    改完一个文件再跑时，未改动的文件直接复用上次结论（会先校验跨文件依赖），
    返回里的 elapsed_ms / scanned_files / cache 可以直接看出省了多少。
    paths 可一次传多个文件，省掉多次往返。CORE: 仅核对定义，未检查范围见 core.not_checked；
    原版目录可用服务环境 RW_CORE_UNITS 指定。"""
    return impl.lint(path, only, max_issues, paths)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
