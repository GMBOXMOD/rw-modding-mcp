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
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import importlib.util

spec = importlib.util.spec_from_file_location("rw_lint", os.path.join(ROOT, "tools", "rw_lint.py"))
rw_lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rw_lint)

FIX = os.path.join(HERE, "fixtures")

# 测试用独立的缓存目录：不污染用户真实缓存，CI 上也保证从零开始
_CACHE_TMP = tempfile.mkdtemp(prefix="rwlint-cache-")
os.environ["RW_LINT_CACHE_DIR"] = _CACHE_TMP

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


# explain_actions 的规则样本：(规则, 行号) 精确比对 —— 同名多条也必须条数一致
EXPLAIN_CASES = [
    ("explain_loop_no_reset.ini",       [("loop-counter", 7)],
     "循环变量推进了但从没复位"),
    ("explain_loop_no_advance.ini",     [("loop-counter", 7)],
     "循环体不推进，门控等不到收尾"),
    ("explain_loop_reset_elsewhere.ini", [("loop-counter", 11)],
     "复位在另一条链上，不算这条链复位过"),
    ("explain_unreachable.ini",         [("unreachable", 6)],
     "动作定义了但没人调用"),
    ("explain_uninit_memory.ini",       [("uninit-memory", 5)],
     "@memory 只读不写"),
    ("explain_index_bound.ini",         [("index-bound", 14)],
     "循环下标步长 2，跳格"),
    ("explain_trailing_comment.ini",    [("trailing-comment", 7),
                                         ("trailing-comment", 12),
                                         ("trailing-comment", 13)],
     "三处行尾注释（@global / 边 / repeat）"),
    ("explain_update_unit_memory.ini",  [],
     "updateUnitMemory 也算写，不应误报"),
    ("explain_action_entry.ini",        [],
     "action_* 是玩家入口，不该报 unreachable"),
]


def check_explain():
    """explain_actions：每个样本的 (规则, 行号) 必须精确匹配，多报少报都算失败。"""
    try:
        spec2 = importlib.util.spec_from_file_location(
            "rw_explain", os.path.join(ROOT, "tools", "rw_explain.py"))
        rx = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(rx)
    except Exception as e:                                  # noqa: BLE001
        print("  SKIP  explain_actions（加载失败：%s）" % e)
        return 0, 0

    ok = bad = 0
    for fn, want, desc in EXPLAIN_CASES:
        path = os.path.join(FIX, fn)
        if not os.path.isfile(path):
            print("  FAIL  %-34s 样本不存在" % fn)
            bad += 1
            continue
        res = rx.explain(path, as_json=True)
        got = sorted((f["rule"], f["line"]) for f in res.get("findings", []))
        want = sorted(want)
        if got == want:
            print("  PASS  %-34s %s" % (fn, desc))
            ok += 1
        else:
            print("  FAIL  %-34s %s" % (fn, desc))
            print("        期望 %s" % (want or "[]"))
            print("        实际 %s" % (got or "[]"))
            bad += 1
    return ok, bad


# 键族样本：期望被报成「未知键」的键名集合（小写）。空集合 = 一个都不该报。
KEY_FAMILY_CASES = [
    ("key_family_ok.ini", [],
     "animation_/builtFrom_#/mutator/body_/turret_ 等键族不该报未知"),
    ("key_family_typo.ini", ["animatoin_speed", "zzznotakey"],
     "键族放行后，真拼错仍然要报"),
]


def check_key_families():
    """键族匹配：合法的动态键名不能报，拼错的必须报。"""
    ok = bad = 0
    for fn, want, desc in KEY_FAMILY_CASES:
        path = os.path.join(FIX, fn)
        if not os.path.isfile(path):
            print("  FAIL  %-28s 样本不存在" % fn)
            bad += 1
            continue
        res = rw_lint.run_lint(path)
        got = sorted({m.group(1).lower()
                      for i in res["issues"] if i.code == "01"
                      for m in [re.search(r"未知键 `([^`]+)`", i.msg)] if m})
        if got == sorted(want):
            print("  PASS  %-28s %s" % (fn, desc))
            ok += 1
        else:
            print("  FAIL  %-28s %s" % (fn, desc))
            print("        期望 %s，实际 %s" % (sorted(want) or "[]", got))
            bad += 1
    return ok, bad


# ---------------------------------------------------------------- 缓存与增量

def _sig(res):
    return sorted((i.level, i.code, i.path, i.line, i.msg) for i in res["issues"])


def check_cache_equivalence():
    """缓存结果必须与全量重算逐条一致 —— 这是缓存唯一真正重要的性质。"""
    ok = bad = 0
    for t in (FIX, os.path.join(ROOT, "示例"), os.path.join(ROOT, "minesweeper"),
              os.path.join(ROOT, "Kings of Cards")):
        if not os.path.exists(t):
            print("  SKIP  %-28s 目录不存在" % os.path.basename(t))
            continue
        full = rw_lint.run_lint(t, incremental=False)
        cold = rw_lint.run_lint(t, incremental=True)
        hot = rw_lint.run_lint(t, incremental=True)
        name = os.path.basename(t)
        if _sig(full) == _sig(cold) == _sig(hot):
            print("  PASS  %-28s 全量=%dms 冷=%dms 热=%dms 结论一致"
                  % (name, full["elapsed_ms"], cold["elapsed_ms"], hot["elapsed_ms"]))
            ok += 1
        else:
            print("  FAIL  %-28s 缓存结论与全量不一致" % name)
            bad += 1
    return ok, bad


def check_cache_incremental():
    """只改一个文件时，只有那一个文件该重算。"""
    ok = bad = 0
    body = io.open(os.path.join(FIX, "good_minimal.ini"), encoding="utf-8").read()
    n = 30
    tmp = tempfile.mkdtemp(prefix="rwlint-inc-")
    try:
        os.makedirs(os.path.join(tmp, "units"))
        io.open(os.path.join(tmp, "mod-info.txt"), "w", encoding="utf-8").write(
            "title: t\nminVersion: 1.15\n")
        for i in range(n):
            io.open(os.path.join(tmp, "units", "u%02d.ini" % i), "w",
                    encoding="utf-8", newline="\n").write(body)

        rw_lint.run_lint(tmp, incremental=True)
        r2 = rw_lint.run_lint(tmp, incremental=True)
        total = n + 1                     # n 个单位文件 + mod-info.txt
        if r2["cache"]["hits"] == total and r2["cache"]["misses"] == 0:
            print("  PASS  %-28s 未改动时 %d 个文件全命中" % ("增量", total))
            ok += 1
        else:
            print("  FAIL  %-28s 未改动时 hits=%d misses=%d（期望 %d/0）"
                  % ("增量", r2["cache"]["hits"], r2["cache"]["misses"], total))
            bad += 1

        io.open(os.path.join(tmp, "units", "u07.ini"), "a",
                encoding="utf-8", newline="\n").write("\n# 改一行\n")
        r3 = rw_lint.run_lint(tmp, incremental=True)
        full = rw_lint.run_lint(tmp, incremental=False)
        if r3["cache"]["misses"] == 1 and _sig(r3) == _sig(full):
            print("  PASS  %-28s 改 1 个文件只重算 1 个" % "增量")
            ok += 1
        else:
            print("  FAIL  %-28s 改 1 个文件 misses=%d（期望 1）"
                  % ("增量", r3["cache"]["misses"]))
            bad += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return ok, bad


def check_cache_cross_file():
    """改 A 必须让依赖 A 的 B 也重算 —— 缓存最危险的地方就在这里。"""
    ok = bad = 0
    tmp = tempfile.mkdtemp(prefix="rwlint-x-")
    try:
        os.makedirs(os.path.join(tmp, "units"))
        io.open(os.path.join(tmp, "mod-info.txt"), "w", encoding="utf-8").write(
            "title: t\nminVersion: 1.15\n")
        a = os.path.join(tmp, "units", "a.ini")
        b = os.path.join(tmp, "units", "b.ini")
        io.open(a, "w", encoding="utf-8", newline="\n").write(
            "[core]\nname: foo\ndisplayText: F\ndisplayText_zh: 甲\nprice: 10\nmaxHp: 10\n")
        io.open(b, "w", encoding="utf-8", newline="\n").write(
            "[core]\nname: bar\ndisplayText: B\ndisplayText_zh: 乙\n[canBuild]\nname: foo\n")

        rw_lint.run_lint(tmp, incremental=True)            # 先建立缓存
        io.open(a, "w", encoding="utf-8", newline="\n").write(
            "[core]\nname: foo2\ndisplayText: F\ndisplayText_zh: 甲\nprice: 10\nmaxHp: 10\n")
        got = rw_lint.run_lint(tmp, incremental=True)
        full = rw_lint.run_lint(tmp, incremental=False)
        has_w11 = any(i.code == "11" for i in got["issues"])
        if has_w11 and _sig(got) == _sig(full):
            print("  PASS  %-28s 改 A 后 B 被重算并报出 W11" % "跨文件依赖")
            ok += 1
        else:
            print("  FAIL  %-28s W11=%s 与全量一致=%s"
                  % ("跨文件依赖", has_w11, _sig(got) == _sig(full)))
            bad += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return ok, bad


def check_bootstrap_marker():
    """就绪标记：命中不启子进程；spec 变了或包目录没了必须失效。"""
    ok = bad = 0
    try:
        spec2 = importlib.util.spec_from_file_location(
            "rw_bootstrap", os.path.join(ROOT, "rw-modding-mcp", "bootstrap.py"))
        bs = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(bs)
    except Exception as e:                                  # noqa: BLE001
        print("  SKIP  %-28s 加载失败：%s" % ("bootstrap", e))
        return 0, 0

    tmp = tempfile.mkdtemp(prefix="rwlint-boot-")
    try:
        pkg = os.path.join(tmp, "mcp")
        os.makedirs(pkg)
        io.open(os.path.join(pkg, "__init__.py"), "w").write("")
        marker = os.path.join(tmp, ".deps-ready")
        bs.READY_MARKER = marker

        cases = [
            ("无标记", False, None),
            ("spec 不匹配", False, {"spec": "mcp>=1,<2", "mcp_package": pkg}),
            ("包目录不存在", False,
             {"spec": bs.REQUIRED_SPEC, "mcp_package": os.path.join(tmp, "nope")}),
            ("正常命中", True, {"spec": bs.REQUIRED_SPEC, "mcp_package": pkg}),
        ]
        for name, want, content in cases:
            if os.path.isfile(marker):
                os.remove(marker)
            if content is not None:
                io.open(marker, "w", encoding="utf-8").write(json.dumps(content))
            got = bs._deps_ready_cached()
            if got == want:
                print("  PASS  %-28s 返回 %s" % ("就绪标记/" + name, got))
                ok += 1
            else:
                print("  FAIL  %-28s 期望 %s 实际 %s" % ("就绪标记/" + name, want, got))
                bad += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return ok, bad


def check_cache():
    ok = bad = 0
    for fn in (check_cache_equivalence, check_cache_incremental,
               check_cache_cross_file, check_bootstrap_marker):
        a, b = fn()
        ok += a
        bad += b
    return ok, bad


def check_workflows():
    """校验 .github/workflows/*.yml 能被 YAML 解析。

    踩过一次：`run: python -m pip install --only-binary :all: mcp` 里
    `: ` 是 YAML 的映射指示符，整个工作流解析失败。GitHub 只会说
    "run failed" 并且 **0 个 job**，本地完全看不出问题。
    """
    wf_dir = os.path.join(ROOT, ".github", "workflows")
    if not os.path.isdir(wf_dir):
        return 0, 0
    try:
        import yaml
    except ImportError:
        print("  SKIP  工作流 YAML 校验（没装 pyyaml，pip install pyyaml 可启用）")
        return 0, 0

    ok = bad = 0
    for fn in sorted(os.listdir(wf_dir)):
        if not fn.endswith((".yml", ".yaml")):
            continue
        path = os.path.join(wf_dir, fn)
        try:
            d = yaml.safe_load(io.open(path, encoding="utf-8").read())
            if not isinstance(d, dict) or "jobs" not in d:
                raise ValueError("缺少 jobs 段")
            print("  PASS  %-28s 工作流 YAML 合法（jobs: %s）"
                  % (fn, ", ".join(d["jobs"])))
            ok += 1
        except Exception as e:                              # noqa: BLE001
            print("  FAIL  %-28s 工作流 YAML 非法：%s" % (fn, e))
            bad += 1
    return ok, bad


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

    print("\n-- 键族匹配 --")
    k_ok, k_bad = check_key_families()
    passed += k_ok
    failed += k_bad

    print("\n-- explain_actions 规则 --")
    e_ok, e_bad = check_explain()
    passed += e_ok
    failed += e_bad

    print("\n-- 缓存与增量 --")
    c_ok, c_bad = check_cache()
    passed += c_ok
    failed += c_bad

    print("\n-- 工作流 --")
    w_ok, w_bad = check_workflows()
    passed += w_ok
    failed += w_bad

    print("\n%d PASS / %d FAIL" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
