#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
game_loadtest.py —— 把模组丢进游戏里做"能不能加载"的自动化测试

两种模式
--------
**attach（默认，游戏开着时）**
    运行中的实例自带 FileChangeEngine：模组文件一变，它会重新解析并写进
    `lastrun.log`，报错格式和冷启动一模一样。所以只要读日志增量 —— 不启动游戏、
    不复制探针、不动 preferences.ini。秒级出结果，也不打扰玩家正在打的局。

**headless（游戏没开时）**
    用 `-nodisplay` 冷启动一个实例，完整解析 `mods/units/` 下所有模组。

    ⚠️ 两者不能同时跑：headless 会往 `mods/units/` 扔 `_probe_*` 目录，
    正在跑的实例会把它当新模组热重载一遍，跑完又删 —— 白折腾两轮，
    日志还会互相污染。所以 auto 模式下检测到游戏在跑就只走 attach。

原理
----
加载失败时游戏会把**完整异常栈 + 出错文件路径**写进日志。所以只要
「让游戏解析一次 → 读日志 → 抓错误」，就能在不开窗口、不选地图的情况下
知道"游戏认不认这个模组"。

能抓到
------
  - 缺图 / 缺文件（`IO Error: Failed to open: ...`）
  - 解析异常（`RuntimeException` + 栈）
  - 引擎侧校验失败（如 hiddenAction 里写 isVisible、冷却 < 5 没开关）
  - 模组被自动禁用（`Disabling mod due to error: ...`）

抓不到
------
  - 运行时行为（逻辑对不对、数值平不平衡）—— 那只能真玩。

用法
----
    python tools/game_loadtest.py <模组目录>                  # auto
    python tools/game_loadtest.py <模组目录> --mode attach    # 强制读日志
    python tools/game_loadtest.py <模组目录> --mode headless  # 强制冷启动
    python tools/game_loadtest.py <模组目录> --keep-log

退出码
------
    0 = 加载通过
    1 = 有加载错误（或 attach 模式下日志没有新增内容）
    2 = 环境问题（找不到游戏 / java / 模组目录）
"""

import io
import os
import json
import hashlib
import re
import sys
import time
import shutil
import argparse
import subprocess

DEFAULT_GAME = r"D:\steam\steamapps\common\Rusted Warfare"

# 日志每行都带 "2026-11-01 10:33:32.865: " 前缀。ERR_PATTERNS 全部用 ^ 锚定，
# 不先剥掉时间戳，这些规则一条都匹配不到 —— 实测漏报过
# "Error while loading unit" 和 "Disabling mod due to error"。
_TS = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}[.][0-9]+: ", re.M)

# 日志里这些行说明有问题
ERR_PATTERNS = [
    (re.compile(r"^Error while loading unit:(.+)$", re.M), "单位加载失败"),
    (re.compile(r"^Disabling mod due to error: (.+)$", re.M), "模组被禁用（有单位加载失败）"),
    (re.compile(r"^Adding error for mod:.*?: (.+)$", re.M), "模组错误"),
    (re.compile(r"^alert:Error loading mod '([^']*)': (.+)$", re.M), "模组加载失败"),
    (re.compile(r"^(\S*(?:Exception|Error): .+)$", re.M), "引擎异常"),
    (re.compile(r"^(com\.corrodinggames\.\S+: .+)$", re.M), "引擎异常（混淆类名）"),
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


# ============================================================== attach 模式
#
# 游戏开着的时候不要再起一个 headless：冷启动要 10–20 秒，还会往 mods/units
# 扔一个 _probe_* 目录，正在跑的实例会把它当新模组热重载一遍，跑完又删 ——
# 白折腾两轮。
#
# 运行中的实例本身就有 FileChangeEngine：模组文件一变，它会重新解析并写进
# lastrun.log，报错格式和冷启动完全一致。所以 attach 模式只要读日志增量。

def _run_quiet(cmd):
    try:
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              timeout=10).stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def find_running_game():
    """正在跑的游戏进程名列表（空 = 没在跑）。

    只认 GUI 客户端。我们自己起的 `java.exe -nodisplay` 不算，否则 attach
    会把上一次 headless 残留误判成「玩家开着游戏」。
    """
    if os.name == "nt":
        out = _run_quiet(["tasklist", "/FO", "CSV", "/NH"])
        names = []
        for line in out.splitlines():
            m = re.match(r'"([^"]+)"', line)
            if m and "rusted warfare" in m.group(1).lower():
                names.append(m.group(1))
        return names
    out = _run_quiet(["ps", "-eo", "comm"])
    return [l.strip() for l in out.splitlines() if "rusted" in l.lower()]


def _state_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        ".loadtest_attach.json")


def _load_state(log_path):
    try:
        d = json.load(io.open(_state_path(), encoding="utf-8"))
        if d.get("log") == log_path:
            return d
    except Exception:
        pass
    return None


def _save_state(log_path, offset):
    try:
        io.open(_state_path(), "w", encoding="utf-8", newline="\n").write(
            json.dumps({"log": log_path, "offset": offset}, ensure_ascii=False))
    except Exception:
        pass


def wait_log_growth(log_path, start, settle=0.6, timeout=8.0):
    """等到日志不再增长，返回 (end_offset, grew)。

    `settle`：大小连续这么久不变才算稳定。热重载是一批一批来的，
    不设沉降时间会读到写了一半的批次。
    """
    t0 = time.time()
    last = os.path.getsize(log_path) if os.path.isfile(log_path) else 0
    stable_since = time.time()
    while time.time() - t0 < timeout:
        time.sleep(0.2)
        try:
            cur = os.path.getsize(log_path)
        except OSError:
            break
        if cur != last:
            last = cur
            stable_since = time.time()
        elif last > start and time.time() - stable_since >= settle:
            break
    return last, last > start


def slice_mod_section(text, mod_name):
    """attach 模式下没有探针，按「日志块」筛出属于本模组的行。

    日志块 = 一条带时间戳的行 + 紧随其后的无时间戳行（异常消息、`\tat ...` 栈）。
    判断归属只看块首那条时间戳行，不能逐行看 —— 否则别的模组的异常消息
    （不带模组名）会被误收进来。
    """
    keep = []
    keep_block = False
    for ln in text.split("\n"):
        if _TS.match(ln):
            keep_block = mod_name in ln
            if keep_block:
                keep.append(ln)
        elif keep_block:
            keep.append(ln)          # 栈/异常消息，跟着块首走
    return "\n".join(keep)


def _sd_to_real(path, game):
    """/SD/ 是游戏根目录的虚拟前缀，换成真实路径才能查 mtime。"""
    if path.startswith("/SD/") and game:
        return os.path.join(game, *path[len("/SD/"):].split("/"))
    return path


def detect_halfwritten(problems, game=None, max_age=2.0):
    """把「报错文件刚刚被改过」的条目标出来。

    热重载可能读到写了一半的文件：引用已加、定义还没加，于是报
    "Failed to find custom effect" 这种假错。实测踩过。
    """
    now = time.time()
    flagged = []
    for kind, msg in problems:
        for raw in re.findall(r"(/SD/[^\s:]+|[A-Za-z]:\\[^\s:]+\.ini)", msg):
            try:
                age = now - os.path.getmtime(_sd_to_real(raw, game))
            except OSError:
                continue
            if age <= max_age:
                flagged.append((kind, msg))
                break
    return flagged


def run_attach(game, mod, wait_timeout):
    """读运行中实例的 lastrun.log 增量。返回 (problems, grew, log_path)。"""
    log_path = os.path.join(game, "lastrun.log")
    if not os.path.isfile(log_path):
        return None, False, log_path

    size = os.path.getsize(log_path)
    state = _load_state(log_path)
    # 上次读到哪就从哪继续；日志被截断（游戏重启过）就从头算
    start = state["offset"] if state and size >= state.get("offset", 0) else size

    end, grew = wait_log_growth(log_path, start, timeout=wait_timeout)

    with io.open(log_path, "rb") as f:
        f.seek(start)
        chunk = f.read(max(0, end - start))
    _save_state(log_path, end)

    text = chunk.decode("utf-8", errors="replace")
    mod_name = os.path.basename(mod.rstrip("\\/"))
    return parse_log(slice_mod_section(text, mod_name), mod_name), grew, log_path


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

    ★ 边界判断必须排除探针自己的行：游戏会把探针的每个子目录也记成
    `Note: Loading disabled mod: .../<probe>/defense`。旧实现把这些当成
    「下一个模组」的开头，段落被切得只剩开头几行，真正的
    `Error while loading unit` 全在切掉的部分里 —— 于是永远报「通过」。
    """
    lines = text.split("\n")
    begin = None
    for i, ln in enumerate(lines):
        if probe_name in ln and ("Loading units from mod: " in ln
                                 or "Note: Loading disabled mod: " in ln):
            begin = i
            break
    if begin is None:
        return text, False

    finish = len(lines)
    for j in range(begin + 1, len(lines)):
        ln = lines[j]
        if probe_name in ln:
            continue                      # 探针自己的子目录，属于本段
        if "Loading units from mod: " in ln or "Note: Loading disabled mod: " in ln:
            finish = j
            break
    return "\n".join(lines[begin:finish]), True


def parse_log(text, probe_name):
    problems = []
    text = _TS.sub("", text)

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


def cleanup_stale(units_dir, prefs, max_age=3600):
    """清理上次被中断（Ctrl-C / kill / 断电）留下的东西。

    实测踩过：11-01 那次跑到一半被打断，`finally` 没执行，于是
      - `mods/units/_probe_HHMMSS` 一直躺在玩家的模组目录里
      - `preferences.ini` 的 `loadDisabledModData:true` 没还原 ——
        这会让游戏**一直解析被禁用模组的单位**，等于悄悄改变玩家的游戏内容
    这里在每次开跑前自愈一次。`max_age` 是为了不误删正在并发跑的探针。
    """
    # 1) 上次还原失败留下的备份，优先还原
    bak = prefs + ".loadtestbak"
    if os.path.isfile(bak):
        try:
            shutil.move(bak, prefs)
            print("[清理] 还原上次中断留下的 preferences.ini")
        except OSError:
            pass

    # 2) 老探针目录
    if not os.path.isdir(units_dir):
        return
    now = time.time()
    for name in os.listdir(units_dir):
        if not name.startswith("_probe_"):
            continue
        p = os.path.join(units_dir, name)
        try:
            if now - os.path.getmtime(p) < max_age:
                continue
            shutil.rmtree(p, ignore_errors=True)
            print(f"[清理] 残留探针目录 {name}")
        except OSError:
            pass


    # 3) 老的测试日志
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        for name in os.listdir(repo):
            if not (name.startswith(".loadtest_") and name.endswith(".log")):
                continue
            p = os.path.join(repo, name)
            if now - os.path.getmtime(p) >= max_age:
                os.remove(p)
                print(f"[清理] 残留日志 {name}")
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser(description="铁锈战争模组加载测试")
    ap.add_argument("mod", help="要测试的模组目录（需含 mod-info.txt）")
    ap.add_argument("--game", default=DEFAULT_GAME, help="游戏安装目录")
    ap.add_argument("--keep-log", action="store_true", help="保留日志文件")
    ap.add_argument("--timeout", type=int, default=300, help="headless 启动超时秒数")
    ap.add_argument("--mode", choices=("auto", "attach", "headless"), default="auto",
                    help="auto=游戏开着就只读日志(默认)；attach=强制读日志；headless=强制冷启动")
    ap.add_argument("--attach-wait", type=float, default=8.0,
                    help="attach 模式等日志新内容的最长秒数（默认 8）")
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

    units_dir = os.path.join(game, "mods", "units")
    prefs = os.path.join(game, "preferences.ini")

    # 先自愈上次中断留下的残留，再决定怎么测
    cleanup_stale(units_dir, prefs)

    # ---- 选模式 --------------------------------------------------------
    running = find_running_game()
    mode = args.mode
    if mode == "auto":
        mode = "attach" if running else "headless"

    if mode == "attach":
        if os.path.normcase(os.path.dirname(mod)) != os.path.normcase(units_dir):
            print("[环境] attach 模式要求模组已经放在 %s 下（当前：%s）" % (units_dir, mod),
                  file=sys.stderr)
            print("       改跑 headless。", file=sys.stderr)
            mode = "headless"
        elif not running:
            print("[环境] 没有检测到运行中的游戏，attach 模式无从读起。改跑 headless。",
                  file=sys.stderr)
            mode = "headless"

    if mode == "attach":
        print("模式　　：attach（读运行中实例的 lastrun.log，不启动游戏）")
        print("模组　　：%s" % os.path.basename(mod))
        print("游戏进程：%s" % "、".join(running))
        print("等待中　：最多 %.0f 秒，等热重载写入日志…\n" % args.attach_wait)

        problems, grew, log_path = run_attach(game, mod, args.attach_wait)
        if problems is None:
            print("[环境] 找不到 lastrun.log —— 游戏可能还没写过日志", file=sys.stderr)
            return 2

        print("=" * 56)
        if not grew:
            print("日志没有新增内容：说明这次没有触发重新解析。")
            print("常见原因：文件没改动、改的是图片等不触发重载的资源，")
            print("或者模组在游戏里已经被禁用（禁用后不会再解析，需要重启游戏）。")
            print("=" * 56)
            return 1
        if not problems:
            print("加载通过：增量日志里没有任何错误。")
        else:
            print(f"发现 {len(problems)} 个问题：")
            for kind, msg in problems:
                print(f"  [{kind}] {msg}")
            flagged = detect_halfwritten(problems, game)
            if flagged:
                print()
                print("⚠️  其中 %d 条涉及的 .ini 在 2 秒内被改过，可能是读到了写了一半的文件。" % len(flagged))
                print("   等 1 秒后重跑一次；仍然报同样的错才是真错。")
        print("=" * 56)
        return 0 if not problems else 1

    # ---- headless（原流程） ---------------------------------------------
    if running:
        print("⚠️  检测到游戏正在运行，但仍按 --mode headless 冷启动。")
        print("    探针目录会被运行中的实例当成新模组热重载一遍，两边日志会互相污染。")
        print("    建议改用 --mode attach（默认 auto 会自动选它）。\n")

    probe_name = f"_probe_{time.strftime('%H%M%S')}"
    os.makedirs(units_dir, exist_ok=True)
    probe_dir = os.path.join(units_dir, probe_name)

    log_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        f".loadtest_{probe_name}.log")

    print(f"探针模组：{probe_name}")
    print(f"源目录　：{mod}")
    print(f"启动中　：无窗口，约 10–20 秒…\n")

    prefs_backup = prefs + ".loadtestbak"

    try:
        # 跳过版本库和编辑器目录：它们会被游戏当成"子模组"逐个枚举，
        # 一个 .git 就能刷出上千行 "Loading disabled mod: .../.git/objects/xx"。
        shutil.copytree(mod, probe_dir, ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".claude", ".vscode", ".idea", "*.log", "*.pyc"))
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
