#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""坏样本回归测试。

和 `tools/rw_mcp/selftest.py` 的区别：
  selftest 测的是"工具本身能不能跑"（自己调自己）；
  这里测的是"**该报的错有没有报**" —— 每个样本都是故意写错的真实配置，
  规则一旦被改坏，这里会立刻红。

跑法：
    python tests/run_tests.py
    python tests/run_tests.py -v
"""

import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import importlib.util

spec = importlib.util.spec_from_file_location("rw_lint", os.path.join(ROOT, "tools", "rw_lint.py"))
rw_lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rw_lint)

FIX = os.path.join(HERE, "fixtures")

# 每个样本：期望的**精确**规则集合（多报、少报都算失败）
CASES = [
    ("bad_event_name.ini",          ["10"],           "事件名拼错（tookDamge）"),
    ("bad_isvisible.ini",           ["11"],           "hiddenAction 里写 isVisible"),
    ("bad_canattack.ini",           ["14"],           "canAttack:true 缺三个目标类型键"),
    ("bad_memory_comment.ini",      ["15"],           "@memory 行尾注释"),
    ("bad_alwayssinglepress.ini",   ["15"],           "alwaysSinglePress 缺配套键"),
    ("bad_repeat.ini",              ["13", "14"],     "repeat 没配 alsoTriggerAction / 写 0"),
    ("bad_func.ini",                ["16"],           "用了不存在的函数 abs()"),
    ("good_minimal.ini",            [],               "最小合法单位（应零错误）"),
]

# 说明：这里的编号就是 rw_lint 的 Issue.code（E13 与 W13 都记作 "13"）。


def codes_of(path):
    res = rw_lint.run_lint(path)
    if not res["ok"]:
        return None, res.get("error")
    return {i.code for i in res["issues"]}, None


def main():
    verbose = "-v" in sys.argv
    passed = failed = 0
    print("坏样本回归测试\n")

    for fn, want, desc in CASES:
        path = os.path.join(FIX, fn)
        if not os.path.isfile(path):
            print("  FAIL  %-28s 样本不存在" % fn)
            failed += 1
            continue
        got, err = codes_of(path)
        if got is None:
            print("  FAIL  %-28s 检查器报错：%s" % (fn, err))
            failed += 1
            continue

        want_set, got_set = set(want), set(got)
        missing = sorted(want_set - got_set)     # 该报没报
        extra = sorted(got_set - want_set)       # 不该报却报了
        ok = not missing and not extra

        if ok:
            passed += 1
            print("  PASS  %-28s %s" % (fn, desc))
        else:
            failed += 1
            print("  FAIL  %-28s %s" % (fn, desc))
            print("        期望 %s，实际 %s" % (sorted(want_set) or "[]", sorted(got_set)))
            if missing:
                print("        漏报：%s" % missing)
            if extra:
                print("        多报：%s" % extra)

        if verbose:
            print("        实际命中：%s" % sorted(got))

    print("\n%d PASS / %d FAIL" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
