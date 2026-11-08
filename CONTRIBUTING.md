# 贡献与发版约定

> 目标：**CHANGELOG 不用手写**。PR 标题就是发布说明的那一行，发版时自动汇总。

## 三条约定

**1. 一个 PR 只做一件事**

"顺便修了个 typo" 会变成发布说明里一条没人看得懂的条目。拆开。

**2. PR 标题 = changelog 那一行**

写**做了什么**，面向使用这个工具的人，不写"修了 #5"。

| ✅ 好 | ❌ 差 |
|---|---|
| `game_loadtest：游戏开着时直接读日志，不再冷启动` | `update loadtest.py` |
| `lint：修掉 canBuild 指向原版单位时的误报` | `fix bug` |
| `lookup_key 支持批量查询` | `refactor impl.py` |

标题里不要带 `(#123)`——GitHub 会自动加。

**3. 用 squash 合并**

只有 squash 才会把 PR 标题原样写进主线提交（`标题 (#123)`），
发布说明才还原得出 PR 编号。merge commit 拿不到标题，rebase 会丢编号。

## 发版流程

```bash
# 1. 确认区间内没有未合并的改动
python tools/gen_changelog.py --from v0.2.0

# 2. 生成条目，贴进 CHANGELOG.md，把 "Unreleased" 改挂成版本号
python tools/gen_changelog.py --from v0.2.0 --heading v0.2.1

# 3. 提交版本号
git commit -am "CHANGELOG：Unreleased 段落改挂到 v0.2.1"

# 4. 打 tag 并推送
git tag -a v0.2.1 -m "v0.2.1"
git push origin main --tags
```

`gen_changelog.py` 会自动跳过合并提交、`Revert`、`CHANGELOG：` 版本簿记，
以及 `chore:` / `docs:` / `ci:` / `build:` 开头的提交。

## CHANGELOG 的写法

```markdown
## v0.2.1 — 2026-11-09

### What's Changed
* game_loadtest：游戏开着时直接读日志，不再冷启动 by @someone in #12
* lint：修掉 canBuild 指向原版单位时的误报 by @someone in #13
```

一行一条。**「为什么」放提交信息或 PR 描述里**，CHANGELOG 只回答"变了什么"。
需要长篇解释的，在段首加一段，像 v0.2.0 的里程碑说明那样。

## 提交信息

标题行会被 squash 时的 PR 标题覆盖，所以**标题写 PR 那一行就够了**；
正文写根因、踩过的坑、实测结果——这些是给以后排查的人看的，不进 CHANGELOG。
