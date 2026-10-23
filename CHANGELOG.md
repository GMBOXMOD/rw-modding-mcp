# 更新记录

README 只讲「现在是什么、怎么用」。改了什么记在这里。

## Unreleased

- README 只留用法，206 行 → 134 行。性能一节、局限一节、目录结构、法务说明、
  示例输出全部移出，两条会影响判断的局限挪进常见问题。

## v0.1.0 — 2026-10-23

首个公开版本。以下是建库三天的完整变更，可以直接当 release notes 用。

### 2026-10-23

性能（冷启动到首次 lint：6.14 s → 2.4 s）

- 依赖探活不再 `import mcp`。那一步会连带加载 pydantic 等依赖，实测 1.8 秒，
  而启动时这笔钱要付两遍（探活一次，服务进程再一次）。改用 `find_spec`。
- 新增 `.venv/.deps-ready` 标记。装好之后正常启动完全不起子进程；
  `REQUIRED_SPEC` 变化或 mcp 包目录消失时自动失效。
- 只有「刚 pip 装完」那一次用真 `import` 验证，确认不是装了个空壳。
- `cmd_check` 里 `has_module` 原来被调两次，合成一次。
- `rw_mcp_server.py` 的 import shim 先试 `MCPServer`（锁的是 2.x），
  省掉一次必然失败的导入。

性能（lint 1037 个文件：3300 ms → 605 ms）

- `check_file()` 内部又调了一次 `parse_file()`，每个文件被解析两遍。
  改为共用一份带 mtime 记忆的结果。
- 三份键名资料约 500 KB、解析约 50 ms，长驻服务每次 lint 都重付一遍。按文件指纹记忆化。
- 新增 `tools/rw_cache.py`：未改动的文件复用上次结论。
  跨文件依赖单独校验 —— 把四个聚合集合包成 `ProbeSet`，记录 `check_file` 做过的
  每一次 `in` / `len` / 遍历，缓存存「查询 + 答案」，复用前逐条重放，
  有一条变了就重算该文件。改 A 会让依赖 A 的 B 一起重算。
- 缓存落 `%LOCALAPPDATA%\rw-modding-mcp\lint`（非 Windows 走 XDG），
  不写模组目录；`--no-cache` / `RW_LINT_CACHE=0` 关闭；
  规则文件或数据表 mtime 变化时整份作废。

接口

- `lint` 返回 `elapsed_ms` / `scanned_files` / `cache`，支持 `paths` 批量。
- CLI 加 `--timing` / `--no-cache`，`--json` 带上耗时与缓存统计。

修复

- 「未知键」假阳性：`animation_*`、`mutator*`、`builtFrom_#_*`、`body_*` 这类
  带参数的键族在代码表里只有模板形式，按前缀和模板整族放行。
  依据是反编译里 `ab2.e("animation_")`、`f.java` 的 `startsWith("body")`。
- 新增 `references/二进制键名.txt`（1472 个键，从 `game-lib.jar` 常量池导出）。
  `showMiniHp`、`useAsAttacker` 是原版在用的合法键，两份代码表都没收录。
- `explain_actions`：`updateUnitMemory` 也算写（原来用它写的变量会被误报「只读不写」）。
- `explain_actions`：行尾 `#` 注释不再让边静默消失，新增 `trailing-comment`
  与 `unresolved-edge` 两条规则。
- `explain_actions`：`loop-counter` 的复位判断改为沿触发链向上找，
  不再因为文件别处有 `x= 0` 就放行。
- 删掉 `tools/impl.py` 与 `tools/selftest.py`。它们是 `rw_mcp/` 下同名文件的
  逐行副本，无人引用，导入路径本身也是错的。

文档

- README 精简到只讲现状，更新记录移到这里。

### 2026-10-22

新增

- `explain_actions` 工具与 `tools/rw_explain.py`：把
  事件/autoTrigger → 动作 → alsoTriggerAction 的调用图画出来，
  标 repeat 次数、门控条件、`@memory` 读写，并做四条静态检查。
- 坏样本回归测试 `tests/run_tests.py` + GitHub Actions。

修复

- Windows 下 `UnicodeEncodeError`。CI 加 `windows-latest` 后立刻暴露：
  中文输出在 en-US 的 cp1252 控制台上编不出来，本机 cp936 一直掩盖着。
- GitHub Actions 工作流解析失败。`run: pip install --only-binary :all: mcp`
  里的 `: ` 是 YAML 映射指示符，整个文件解析失败，GitHub 只显示 0 job。
- `selftest` 在 Linux 上必挂：断言要求 `game-lib.jar` 存在，CI 上没有。
- `dataset.py` 写死的 `D:\steam\...`，改为常见位置候选 + `RW_GAME_JAR`。
- 归一化匹配不再剥数字。`customTarget1` 和 `customTarget2` 会被混成一个，
  再按排序静默取第一个 —— 属于「查到了但答错」。命中多个候选时返回
  `match: "ambiguous"`，不猜。
- 两张代码表交叉校验：`agreement`（both / csv_only / cn_only / jar_only）
  与 `conflicts`（值类型粗类目互斥时才报，误报率 0.7%）。
- 锁 `mcp>=2.3,<3`。2.x 把 `FastMCP` 改名成 `MCPServer`，不锁主版本的话
  上游发 3.x 再改个名，用户装完就是 `ModuleNotFoundError`。
- `--stdio` 断言从 6 条扩到 19 条。原来只判 `bool(res.content)`，
  而 MCP 返回错误时 content 也非空，等于没验。

### 2026-10-21

首个可用版本

- 四个工具：`lookup_key` / `search_source` / `get_ref` / `lint`。
- `bootstrap.py`：自动建 venv、装依赖、检查数据，客户端只指向它。
  反编译源码缺失时可 `--decompile`，用玩家自己的 `game-lib.jar` 现场生成。
- 静态检查器 `tools/rw_lint.py`，也可单独当命令行用。
- 两份键名资料入库（官方 CSV 与中文代码表），反编译产物不入库。

修复

- Windows 上不能用 `os.execve` 做「进程替换」。它不是真替换，
  而是起子进程再退出父进程，MCP 客户端给的管道句柄会断，
  表现是 `initialize` 报 `Connection closed`。改用 `subprocess.run` 继承 stdio。
