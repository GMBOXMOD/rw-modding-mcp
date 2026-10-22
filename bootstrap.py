#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""铁锈战争模组 MCP —— 通用启动器

用法
----
    python bootstrap.py                 # 自动装依赖后启动 MCP 服务（stdio）
    python bootstrap.py --check         # 只检查环境，不启动
    python bootstrap.py --setup         # 只装依赖，不启动
    python bootstrap.py --decompile     # 反编译 game-lib.jar，生成 tools/jar/src
    python bootstrap.py --game "D:/steam/steamapps/common/Rusted Warfare"

客户端里直接把 command 指向本文件即可，它会自己建 venv、装 mcp、检查数据，
然后把自己替换成真正的 MCP 服务进程。

⚠️ 重要：stdio 模式下 **stdout 是 MCP 的通信通道**。
   本脚本所有诊断信息都写到 stderr 和 bootstrap.log，绝不污染 stdout。
"""

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(HERE, ".venv")
SERVER = os.path.join(HERE, "tools", "rw_mcp_server.py")
CFR_JAR = os.path.join(HERE, "tools", "jar", "cfr.jar")
JAR_SRC = os.path.join(HERE, "tools", "jar", "src")
LOG_PATH = os.path.join(HERE, "bootstrap.log")
CFR_URL = "https://repo1.maven.org/maven2/org/benf/cfr/0.152/cfr-0.152.jar"
REQUIRED_PKG = "mcp"
# 锁定主版本：mcp 2.x 把 FastMCP 改名成 MCPServer，1.x 到 2.x 是破坏性变更。
# 不锁的话，哪天上游出 3.x 改个名，用户装完就是 ModuleNotFoundError。
REQUIRED_SPEC = "mcp>=2.3,<3"

# 常见 Steam 安装位置
GAME_CANDIDATES = [
    r"D:\steam\steamapps\common\Rusted Warfare",
    r"C:\Program Files (x86)\Steam\steamapps\common\Rusted Warfare",
    r"C:\Program Files\Steam\steamapps\common\Rusted Warfare",
    os.path.expanduser(r"~\Steam\steamapps\common\Rusted Warfare"),
]


# ---------------------------------------------------------------- 输出

def _say(msg, quiet=False):
    """诊断信息一律走 stderr —— stdout 留给 MCP 协议。"""
    if not quiet:
        sys.stderr.write("[bootstrap] %s\n" % msg)
        sys.stderr.flush()


def _append_log(msg):
    try:
        with io.open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except OSError:
        pass


def _fail(msg, code=1):
    _say("错误：" + msg)
    _append_log("ERROR " + msg)
    return code


# ---------------------------------------------------------------- venv

def venv_python():
    """返回本仓库 .venv 里的 python 路径（可能尚不存在）。"""
    if os.name == "nt":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


def in_our_venv():
    try:
        return os.path.normcase(os.path.abspath(sys.executable)) == \
               os.path.normcase(os.path.abspath(venv_python()))
    except OSError:
        return False


def ensure_venv(quiet=False):
    py = venv_python()
    if os.path.isfile(py):
        return py
    _say("首次运行，正在创建虚拟环境（约 10 秒）…", quiet)
    _append_log("creating venv at " + VENV_DIR)
    r = subprocess.run([sys.executable, "-m", "venv", VENV_DIR],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if r.returncode != 0 or not os.path.isfile(py):
        detail = (r.stdout or b"").decode("utf-8", "replace")[-800:]
        _fail("创建虚拟环境失败。请确认 Python 自带 venv 模块。\n" + detail)
        return None
    return py


def has_module(py, name):
    r = subprocess.run([py, "-c", "import %s" % name],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0


def ensure_deps(py, quiet=False):
    """确保 venv 里有 mcp。pip 的输出写日志，不占 stdout/stderr。"""
    if has_module(py, REQUIRED_PKG):
        return True
    _say("正在安装依赖 %s（首次约 20–60 秒）…" % REQUIRED_SPEC, quiet)
    _append_log("pip install " + REQUIRED_SPEC)
    cmd = [py, "-m", "pip", "install", "--only-binary", ":all:", REQUIRED_SPEC]
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    with io.open(LOG_PATH, "a", encoding="utf-8") as log:
        log.write("\n$ %s\n" % " ".join(cmd))
        log.flush()
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
    if r.returncode != 0 or not has_module(py, REQUIRED_PKG):
        _fail("安装依赖失败，详情见 %s" % LOG_PATH)
        return False
    _say("依赖安装完成。", quiet)
    return True


# ---------------------------------------------------------------- 数据

def data_status():
    csv = None
    cn = None
    for d in (os.path.join(HERE, "references"), HERE):
        if csv is None:
            for fn in ("官方代码表（Modding References）.csv",):
                p = os.path.join(d, fn)
                if os.path.isfile(p):
                    csv = p
        if cn is None:
            try:
                for fn in sorted(os.listdir(d)):
                    if "代码表" in fn and fn.lower().endswith(".txt"):
                        cn = os.path.join(d, fn)
                        break
            except OSError:
                pass
    n_java = 0
    if os.path.isdir(JAR_SRC):
        for _dp, _dn, fns in os.walk(JAR_SRC):
            n_java += sum(1 for f in fns if f.endswith(".java"))
    return {"csv": csv, "cn": cn, "java_files": n_java}


def find_game(explicit=None):
    if explicit:
        return explicit if os.path.isfile(os.path.join(explicit, "game-lib.jar")) else None
    env = os.environ.get("RW_GAME_JAR")
    if env and os.path.isfile(env):
        return os.path.dirname(env)
    for d in GAME_CANDIDATES:
        if os.path.isfile(os.path.join(d, "game-lib.jar")):
            return d
    return None


def find_java():
    exe = "java.exe" if os.name == "nt" else "java"
    jh = os.environ.get("JAVA_HOME")
    if jh:
        p = os.path.join(jh, "bin", exe)
        if os.path.isfile(p):
            return p
    p = shutil.which("java")
    if p:
        return p
    for d in (r"D:\Java\bin", r"C:\Program Files\Java\jdk-17\bin"):
        p = os.path.join(d, exe)
        if os.path.isfile(p):
            return p
    return None


def download_cfr(quiet=False):
    if os.path.isfile(CFR_JAR) and os.path.getsize(CFR_JAR) > 1_000_000:
        return CFR_JAR
    os.makedirs(os.path.dirname(CFR_JAR), exist_ok=True)
    _say("下载 CFR 反编译器（约 2 MB）…", quiet)
    try:
        with urllib.request.urlopen(CFR_URL, timeout=60) as r, \
                open(CFR_JAR, "wb") as fh:
            shutil.copyfileobj(r, fh)
    except Exception as e:                                    # noqa: BLE001
        _fail("下载 CFR 失败：%s" % e)
        return None
    if os.path.getsize(CFR_JAR) < 1_000_000:
        _fail("下载的 CFR 不完整")
        return None
    return CFR_JAR


def do_decompile(game, quiet=False, force=False):
    """从玩家自己的 game-lib.jar 反编译出 tools/jar/src。

    注意：反编译产物是游戏厂商的代码，**不要提交到仓库**（已在 .gitignore 里排除）。
    """
    if not game:
        return _fail("找不到游戏目录。请用 --game 指定 Rusted Warfare 安装路径。")
    jar = os.path.join(game, "game-lib.jar")
    if not os.path.isfile(jar):
        return _fail("找不到 %s" % jar)

    st = data_status()
    if st["java_files"] > 0 and not force:
        _say("已有 %d 个 .java，跳过（要重做加 --force）" % st["java_files"], quiet)
        return 0

    java = find_java()
    if not java:
        return _fail("找不到 java。请安装 JDK 17+ 或设置 JAVA_HOME。")

    cfr = download_cfr(quiet)
    if not cfr:
        return 1

    _say("反编译中（约 1 分钟）…", quiet)
    _append_log("cfr %s -> %s" % (jar, JAR_SRC))
    cmd = [java, "-Xmx2g", "-jar", cfr, jar, "--outputdir", JAR_SRC, "--silent", "true"]
    with io.open(LOG_PATH, "a", encoding="utf-8") as log:
        log.write("\n$ %s\n" % " ".join(cmd))
        log.flush()
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)

    st = data_status()
    if r.returncode != 0 or st["java_files"] == 0:
        return _fail("反编译失败，详情见 %s" % LOG_PATH)
    _say("反编译完成：%d 个 .java" % st["java_files"], quiet)
    return 0


# ---------------------------------------------------------------- 检查

def cmd_check(args):
    """--check 模式：输出给人看的状态表（此时不是 MCP 模式，可以用 stdout）。"""
    py = venv_python()
    st = data_status()
    game = find_game(args.game)

    rows = [
        ("Python", "%s (需要 ≥3.10)" % sys.version.split()[0],
         sys.version_info >= (3, 10)),
        ("虚拟环境", VENV_DIR if os.path.isfile(py) else "未创建（首次启动会自动建）",
         os.path.isfile(py)),
        ("依赖 mcp", "已装" if os.path.isfile(py) and has_module(py, REQUIRED_PKG)
                     else "未装（首次启动会自动装）",
         os.path.isfile(py) and has_module(py, REQUIRED_PKG)),
        ("官方代码表", st["csv"] or "缺失", bool(st["csv"])),
        ("中文代码表", st["cn"] or "缺失", bool(st["cn"])),
        ("反编译源码", ("%d 个 .java" % st["java_files"]) if st["java_files"] else
                       "缺失（search_source 不可用，可跑 --decompile）",
         st["java_files"] > 0),
        ("游戏目录", game or "未找到（可选，只有 --decompile 需要）", bool(game)),
        ("java", find_java() or "未找到（可选，只有 --decompile 需要）", bool(find_java())),
    ]
    print("铁锈战争模组 MCP —— 环境检查\n")
    for name, val, ok in rows:
        print("  %s %-12s %s" % ("[OK]  " if ok else "[--]  ", name, val))
    print("\n必需项：Python / 官方代码表 / 中文代码表。")
    print("mcp 与 .venv 会在首次启动时自动补齐。")
    print("反编译源码只有 search_source 需要，用 --decompile 生成。")
    return 0


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(
        description="铁锈战争模组 MCP 通用启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="只检查环境，不启动")
    ap.add_argument("--setup", action="store_true", help="只装依赖，不启动")
    ap.add_argument("--decompile", action="store_true", help="反编译 game-lib.jar")
    ap.add_argument("--force", action="store_true", help="配合 --decompile 强制重做")
    ap.add_argument("--game", default=None, help="Rusted Warfare 安装目录")
    ap.add_argument("--quiet", action="store_true", help="少输出")
    args = ap.parse_args()

    if args.check:
        return cmd_check(args)

    if args.decompile:
        return do_decompile(find_game(args.game), args.quiet, args.force)

    if sys.version_info < (3, 10):
        return _fail("需要 Python 3.10 或更高，当前是 %s" % sys.version.split()[0])

    py = ensure_venv(args.quiet)
    if not py:
        return 1
    if not ensure_deps(py, args.quiet):
        return 1

    if args.setup:
        st = data_status()
        _say("环境就绪。数据：代码表 %s / 中文表 %s / 反编译 %d 个 .java"
             % ("有" if st["csv"] else "缺", "有" if st["cn"] else "缺", st["java_files"]),
             args.quiet)
        return 0

    st = data_status()
    if not st["csv"] or not st["cn"]:
        _say("警告：代码表缺失，lookup_key 会查不到东西。把 CSV 和中文表放进 references/ 即可。",
             args.quiet)
    if st["java_files"] == 0:
        _say("提示：search_source 不可用（没有反编译源码）。跑 --decompile 可生成。",
             args.quiet)

    if not os.path.isfile(SERVER):
        return _fail("找不到服务入口 %s" % SERVER)

    # 用 venv 里的 python 跑服务，**继承当前进程的 stdin/stdout/stderr**。
    #
    # 这里刻意不用 os.execve：Windows 上它不是真正的进程替换，
    # 而是"起个子进程再退出"，MCP 客户端给的那对管道句柄会断掉，
    # 表现就是 initialize 时报 Connection closed。
    # 用 subprocess 显式继承 stdio（三个参数都传 None）反而稳。
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
               RW_PROJECT_ROOT=HERE)
    _append_log("launch %s %s" % (py, SERVER))
    try:
        r = subprocess.run([py, SERVER], env=env,
                           stdin=None, stdout=None, stderr=None)
        return r.returncode
    except OSError as e:
        return _fail("启动失败：%s" % e)


if __name__ == "__main__":
    sys.exit(main())
