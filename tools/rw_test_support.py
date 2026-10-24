# -*- coding: utf-8 -*-
"""可选真实模组样本的只读定位；不复制、不执行、不修改模组。"""

import os


def find_test_mod(name, project_root):
    """优先 RW_TEST_MOD_ROOTS，其次仓库内部和仓库旁边。

    多个根目录用 os.pathsep 分隔（Windows 是分号）。只查指定名称，不递归搜整盘。
    此配置仅供测试使用，不改变 MCP 的项目根或资料路径。
    """
    roots = [os.path.expanduser(os.path.expandvars(p.strip()))
             for p in os.environ.get("RW_TEST_MOD_ROOTS", "").split(os.pathsep) if p.strip()]
    root = os.path.abspath(project_root)
    roots.extend((root, os.path.dirname(root)))
    for directory in dict.fromkeys(roots):
        candidate = os.path.abspath(os.path.join(directory, name))
        if os.path.isdir(candidate):
            return candidate
    return None
