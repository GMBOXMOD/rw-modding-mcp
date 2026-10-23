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
def lookup_key(key: str, max_suggestions: int = 5) -> dict:
    """查一个 luke 键：规范拼写、所属节、版本、值类型、中英文描述与例子；查不到时给近似拼写建议。"""
    return impl.lookup_key(key, max_suggestions)


@mcp.tool()
def search_source(pattern: str, regex: bool = False, case_sensitive: bool = False,
                  path_filter: str = "", max_results: int = 50) -> dict:
    """在反编译的 Java 源码树里搜索，返回文件、行号和匹配行。path_filter 可限定子目录，如 "custom/"。"""
    return impl.search_source(pattern, regex, case_sensitive, path_filter, max_results)


@mcp.tool()
def explain_actions(path: str, action: str = "", fmt: str = "text") -> dict:
    """把事件/autoTrigger → 动作 → alsoTriggerAction 的调用图画出来，标 repeat 次数、门控条件、
    @memory 读写；并做四条静态检查（循环变量复位与推进、不可达动作、未初始化 memory、下标上界）。

    fmt: text（默认，只返回文本图 + 发现）/ json（返回完整结构）/ both。"""
    return impl.explain_actions(path, action or None, fmt)


@mcp.tool()
def get_ref() -> dict:
    """返回结构化速查表：18 个合法事件、27 个逻辑函数、值枚举、内存类型、必须配对使用的键、硬限制。"""
    return impl.get_ref()


@mcp.tool()
def lint(path: str = "", only: str = "all", max_issues: int = 100,
         paths: list[str] | None = None) -> dict:
    """对模组文件或目录跑静态检查，返回结构化的 issues（错误/警告、文件、行号、说明）。

    issues 里的 f 是 issue_files 的下标，不是路径 —— 路径只在 issue_files 里出现一次。
    改完一个文件再跑时，未改动的文件直接复用上次结论（会先校验跨文件依赖），
    返回里的 elapsed_ms / scanned_files / cache 可以直接看出省了多少。
    paths 可一次传多个文件，省掉多次往返。"""
    return impl.lint(path, only, max_issues, paths)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
