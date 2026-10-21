#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
game_loadtest.py —— 把模组丢进游戏里做"能不能加载"的自动化测试

原理
----
Rusted Warfare 支持 `-nodisplay` 无窗口启动，且会完整加载 `mods/units/` 下的模组。
加载失败时会把**完整异常栈 + 出错文件路径**写进日志。所以只要：

    复制模组 → 无头启动 → 读日志 → 抓错误

就能在不开游戏、不选地图的情况下知道"游戏认不认这个模组"。

能抓到
------
  - 缺图 / 缺文件（`IO Error: Failed to open: ...`）
  - 解析异常（`RuntimeException` + 栈）
  - 引擎侧校验失败（如 hiddenAction 里写 isVisible）
  - 模组被自动禁用（`Disabled mod at: ...`）

抓不到
------
  - 运行时行为（逻辑对不对、数值平不平衡）—— 那只能真玩。

用法
----
    python tools/game_loadtest.py <模组目录>
    python tools/game_loadtest.py <模组目录> --keep-log
    python tools/game_loadtest.py <模组目录> --game "D:/steam/steamapps/common/Rusted Warfare"

退出码
------
    0 = 加载通过
    1 = 有加载错误
    2 = 环境问题（找不到游戏 / java / 模组目录）
"""

import io
import os
import hashlib
import re
import sys
import time
import shutil
import argparse
import subprocess

DEFAULT_GAME = r"D:\steam\steamapps\common\Rusted Warfare"

# 日志里这些行说明有问题
ERR_PATTERNS = [
    (re.compile(r"^Error while loading unit:(.+)$", re.M), "单位加载失败"),
    (re.compile(r"^Adding error for mod:.*?: (.+)$", re.M), "模组错误"),
    (re.compile(r"^alert:Error loading mod '([^']*)': (.+)$", re.M), "模组加载失败"),
    (re.compile(r"^(\S*(?:Exception|Error): .+)$", re.M), "引擎异常"),
    (re.compile(r"^java\.lang\.\w+(?:Exception|Error): (.+)$", re.M), "Java 异常"),
]


def force_load_disabled_mods(prefs_path):
    """把 loadDisabledModData 打开。

    为什么用这个而不是伪造 modSettings：
    模组默认是 disabled，`loadSelection` 又在模组被发现之前就跑，
    伪造 `名称|SHA256(名称)|enabled` 实测无效。
    但 `loadDisabledModData: true` 会让游戏**照样解析被禁用模组的单位**，
    只是不把它们放进可用列表 —— 这正是加载测试需要的：
    解析会跑，错误会报，而且不影响玩家的启用状态（跑完还原）。
    """
    if not os.path.isfile(prefs_path):
        return False
    txt = io.open(prefs_path, encoding="utf-8", errors="replace").read()
    if "loadDisabledModData:false" in txt:
        txt = txt.replace("loadDisabledModData:false", "loadDisabledModData:true")
    elif "loadDisabledModData:true" not in txt:
        txt += "\nloadDisabledModData:true"
    io.open(prefs_path, "w", encoding="utf-8", newline="\n").write(txt)
    return True


def find_java(game):
    for rel in ("jvm64/bin/java.exe", "jvm/bin/java.exe"):
        p = os.path.join(game, *rel.split("/"))
        if os.path.isfile(p):
            return p
    return None


def run_headless(game, log_path, timeout):
    java = find_java(game)
    if not java:
        return None, "找不到游戏自带的 java（jvm64/bin/java.exe）"

    cmd = [
        java, "-Xmx1200M", "-Dfile.encoding=UTF-8",
        "-Djava.library.path=.",
        "-cp", "game-lib.jar" + os.pathsep + "libs/*",
        "com.corrodinggames.rts.java.Main",
        "-nodisplay", "-nosound", "-nologfile",
        "-log", log_path,
        "-printunits",
    ]
    try:
        p = subprocess.run(cmd, cwd=game, timeout=timeout,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return p.returncode, None
    except subprocess.TimeoutExpired:
        return None, f"启动超时（{timeout}s）"


def slice_probe_section(text, probe_name):
    """只截取探针模组自己那段日志。

    否则会把用户自己那些模组的错误也报进来 —— 第一次跑就被 151 条
    别人模组的错误淹了。
    """
    pats = [r"Loading units from mod: " + re.escape(probe_name),
            r"Note: Loading disabled mod: .*" + re.escape(probe_name) + r"/units"]
    start = -1
    for pat in pats:
        m = re.search(pat, text)
        if m:
            start = m.start()
            break
    if start < 0:
        return text, False

    tail = text[start + 1:]
    nxt = re.search(r"(?:Loading units from mod: |Note: Loading disabled mod: )", tail)
    end = start + 1 + nxt.start() if nxt else len(text)
    return text[start:end], True


def parse_log(text, probe_name):
    problems = []
    seen = set()

    # 探针模组是否被禁用 —— 后门模式下这是预期的，只在没开成功时才提示
    disabled = re.search(r"Disabled mod at:.*" + re.escape(probe_name), text) is not None
    if disabled and "Note: Loading disabled mod" not in text:
        problems.append(("模组未被解析",
                         "模组被禁用且 loadDisabledModData 后门没生效，单位没有被解析。"))

    for pat, kind in ERR_PATTERNS:
        for m in pat.finditer(text):
            msg = m.group(m.lastindex).strip() if m.lastindex else m.group(0).strip()
            if not msg or msg in seen:
                continue
            seen.add(msg)
            problems.append((kind, msg[:300]))

    # 补一条栈顶，方便定位
    m = re.search(r"^java\.lang\.\w+(?:Exception|Error):.*\n\tat ([\w.$]+)\(([^)]*)\)", text, re.M)
    if m:
        problems.append(("异常位置", f"{m.group(1)} ({m.group(2)})"))

    return problems


def main():
    ap = argparse.ArgumentParser(description="铁锈战争模组无头加载测试")
    ap.add_argument("mod", help="要测试的模组目录（需含 mod-info.txt）")
    ap.add_argument("--game", default=DEFAULT_GAME, help="游戏安装目录")
    ap.add_argument("--keep-log", action="store_true", help="保留日志文件")
    ap.add_argument("--timeout", type=int, default=300, help="启动超时秒数")
    args = ap.parse_args()

    mod = os.path.abspath(args.mod)
    game = os.path.abspath(args.game)

    if not os.path.isdir(mod):
        print(f"[环境] 找不到模组目录：{mod}", file=sys.stderr)
        return 2
    if not os.path.isfile(os.path.join(mod, "mod-info.txt")):
        print(f"[环境] {mod} 里没有 mod-info.txt —— 这不像一个模组根目录", file=sys.stderr)
        return 2
    if not os.path.isfile(os.path.join(game, "game-lib.jar")):
        print(f"[环境] 找不到游戏：{game}", file=sys.stderr)
        return 2

    # 每次用新名字：游戏对新模组会自动启用，但对"上次失败被禁用"的同名模组不会重试
    probe_name = f"_probe_{time.strftime('%H%M%S')}"
    units_dir = os.path.join(game, "mods", "units")
    os.makedirs(units_dir, exist_ok=True)
    probe_dir = os.path.join(units_dir, probe_name)

    log_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        f".loadtest_{probe_name}.log")

    print(f"探针模组：{probe_name}")
    print(f"源目录　：{mod}")
    print(f"启动中　：无窗口，约 10–20 秒…\n")

    prefs = os.path.join(game, "preferences.ini")
    prefs_backup = prefs + ".loadtestbak"

    try:
        shutil.copytree(mod, probe_dir)
    except Exception as e:
        print(f"[环境] 复制模组失败：{e}", file=sys.stderr)
        return 2

    # 备份 preferences.ini：跑测试会改动模组启用状态，必须还原
    prefs_saved = False
    if os.path.isfile(prefs):
        shutil.copy2(prefs, prefs_backup)
        prefs_saved = True
        force_load_disabled_mods(prefs)

    try:
        code, err = run_headless(game, log_path, args.timeout)
        if err:
            print(f"[环境] {err}", file=sys.stderr)
            return 2

        if not os.path.isfile(log_path):
            print("[环境] 没有生成日志，游戏可能启动失败", file=sys.stderr)
            return 2

        full = io.open(log_path, encoding="utf-8", errors="replace").read()
        text, section_found = slice_probe_section(full, probe_name)

        # 确认探针真的被加载了
        loaded = section_found
        units = len(re.findall(r'<div class="unit">', full))

        problems = parse_log(text, probe_name)

        print("=" * 56)
        if not problems and loaded:
            print("加载通过：游戏没有报任何错。")
        elif not problems and not loaded:
            print("未加载：模组没被游戏读进去（可能被禁用或路径不对）。")
        else:
            print(f"发现 {len(problems)} 个问题：")
            for kind, msg in problems:
                print(f"  [{kind}] {msg}")
        print("=" * 56)
        print(f"探针被加载：{'是' if loaded else '否'}　内置单位导出：{units} 个")
        if args.keep_log:
            print(f"日志保留：{log_path}")

        return 0 if (not problems and loaded) else 1

    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)
        if prefs_saved and os.path.isfile(prefs_backup):
            shutil.move(prefs_backup, prefs)
        if not args.keep_log and os.path.isfile(log_path):
            os.remove(log_path)


if __name__ == "__main__":
    sys.exit(main())
