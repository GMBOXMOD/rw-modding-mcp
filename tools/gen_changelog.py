#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_changelog.py —— 从 git 历史生成「What's Changed」发布说明。

为什么要有这个
--------------
GitHub 的自动发布说明（`--generate-notes`）只在网页端生成，`gh` 没登录就用不了。
但只要**用 squash 合并**，PR 标题就会原样落进提交信息，形如：

    game_loadtest：加 attach 模式，游戏开着时不再冷启动 (#12)

于是纯本地也能还原出同样的列表。

约定（见 CONTRIBUTING.md）
--------------------------
1. 一个 PR 只做一件事。
2. **PR 标题就是 changelog 那一行**——面向用户写"做了什么"，不写"修了 #5"。
3. 用 squash 合并，让标题进主线。

用法
----
    python tools/gen_changelog.py                      # 上个 tag → HEAD
    python tools/gen_changelog.py --from v0.1.0        # 指定起点
    python tools/gen_changelog.py --from v0.1.0 --to HEAD --heading "v0.2.0"
    python tools/gen_changelog.py --plain              # 不带 markdown 标题

退出码
------
    0 = 有内容
    1 = 区间内没有可发布的提交
    2 = 不是 git 仓库 / ref 不存在
"""

import argparse
import re
import subprocess
import sys

# 这些提交不进 changelog：它们是簿记或合并动作，不是面向用户的变更
SKIP_PATTERNS = [
    re.compile(r"^Merge (pull request|branch|remote)"),
    re.compile(r"^Revert\s"),
    re.compile(r"^CHANGELOG[：:]"),          # 版本号/变更日志本身的维护
    re.compile(r"^(chore|docs|ci|build)[:：]", re.I),
]

# squash 合并后：`标题 (#123)`
PR_RE = re.compile(r"^(?P<title>.+?)\s*\(#(?P<num>\d+)\)\s*$")


def git(*args):
    p = subprocess.run(["git"] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace")


def last_tag():
    out = git("describe", "--tags", "--abbrev=0")
    return out.strip() if out else None


def rev_exists(ref):
    return git("rev-parse", "--verify", "--quiet", ref + "^{commit}") is not None


def collect(rev_range):
    """返回 [(标题, 作者, PR号或 None), ...]，按时间正序。"""
    out = git("log", "--no-merges", "--reverse", "--format=%an\t%s", rev_range)
    if out is None:
        return None

    entries, seen_pr = [], set()
    for line in out.splitlines():
        if "\t" not in line:
            continue
        author, subject = line.split("\t", 1)
        subject = subject.strip()
        if not subject:
            continue
        if any(p.search(subject) for p in SKIP_PATTERNS):
            continue

        m = PR_RE.match(subject)
        if m:
            title, num = m.group("title").strip(), m.group("num")
            if num in seen_pr:      # 同一个 PR 的多个提交只留一条
                continue
            seen_pr.add(num)
            entries.append((title, author, num))
        else:
            entries.append((subject, author, None))
    return entries


def render(entries, heading=None, markdown=True):
    lines = []
    if heading:
        lines.append(("## %s" % heading) if markdown else heading)
        lines.append("")
    if markdown:
        lines.append("### What's Changed")
    else:
        lines.append("What's Changed")

    for title, author, num in entries:
        tail = " by @%s" % author
        if num:
            tail += " in #%s" % num
        lines.append(("* %s%s" % (title, tail)) if markdown else ("- %s%s" % (title, tail)))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="从 git 历史生成 What's Changed")
    ap.add_argument("--from", dest="start", help="起点 ref（默认：最近的 tag）")
    ap.add_argument("--to", dest="end", default="HEAD", help="终点 ref（默认 HEAD）")
    ap.add_argument("--heading", help="额外输出的版本标题，如 v0.2.0")
    ap.add_argument("--plain", action="store_true", help="输出纯文本，不带 markdown 标记")
    args = ap.parse_args()

    if git("rev-parse", "--git-dir") is None:
        print("[环境] 当前目录不是 git 仓库", file=sys.stderr)
        return 2

    start = args.start or last_tag()
    if start is None:
        # 一个 tag 都没有：从第一个提交算起
        start = git("rev-list", "--max-parents=0", "HEAD").strip().split("\n")[0]
    if not rev_exists(start):
        print(f"[环境] ref 不存在：{start}", file=sys.stderr)
        return 2
    if not rev_exists(args.end):
        print(f"[环境] ref 不存在：{args.end}", file=sys.stderr)
        return 2

    entries = collect(f"{start}..{args.end}")
    if entries is None:
        print("[环境] git log 执行失败", file=sys.stderr)
        return 2
    if not entries:
        print(f"[空] {start}..{args.end} 之间没有可发布的提交", file=sys.stderr)
        return 1

    print(render(entries, args.heading, markdown=not args.plain))
    return 0


if __name__ == "__main__":
    sys.exit(main())
