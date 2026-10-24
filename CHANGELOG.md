# 更新记录

README 只讲「现在是什么、怎么用」。改了什么记在这里。

## Unreleased

- `tests/run_tests.py` 的 bootstrap 用例改为「找不到 bootstrap.py 就跳过」。
  原来硬编码 `ROOT/bootstrap.py`，在仓库里跑没问题，在项目根跑就红。

CORE: 基础支持

- `lint` 能从原版 `assets/units` 读取 `copyFrom: CORE:` 的定义；支持自动定位、`RW_CORE_UNITS` 与 CLI `--core-units`。
- 原版目录不可用时明确未完成；目标缺失、不可读或路径越界报告 E17。不修改或复制原版配置。
- 返回 `core.mode=symbols_only` 和未检查范围，不把定义解析当作完整的继承合并或运行时验证。
- 原版目录和继承文件指纹加入相关单位的缓存依赖；新增 12 项回归及不依赖游戏安装的 MCP 协议样本。

可选外部测试

- 真实模组样本支持从 `RW_TEST_MOD_ROOTS`、仓库内部与仓库旁边定位，不再因为样本在相邻目录而跳过。
- 外部模组可能独立变更，工具自检改为比较 CLI/MCP 计数；固定 fixtures 继续断言精确规则。
  缓存一致性测试同时要求执行成功，并展示未展开/跳过数量，不把不完整分析冒充完整验证。
- 新增 3 项外部样本定位测试，并补充 PyYAML 安装与外部模组配置说明。

定向查询与上下文控制（第一轮）

- `lookup_key` 默认短输出，支持 `section` 和 `detail=full`。短输出保留约束、资料冲突、来源和重要说明；
  原始 `csv` / `cn` 数组仅在 full 模式返回，旧参数顺序不变。批量去重并限制为 32 个不同键。
- CSV 条目保留所属节，同名键按节筛选，避免把其它节的版本/类型混进来。
- `search_source` 增加 literal/regex 明确模式、最多 8 词批量、有限上下文、offset 分页和字符预算。
  默认最多 10 条结果；旧 regex 布尔参数仍可用。空结果区分无源码、路径无文件与无命中，提示常见模式误用。
- `get_ref` 可按 topic/name 查询已有速查数据，无参数保持完整返回；未知条目不冒充引擎不支持。
- 新增 27 项定向查询回归；真实 stdio 协议测试使用合成源码，并检查实际返回字符数、分页和旧参数兼容。
- 修正文档中“每次都重发整个上下文，所以必然更省钱”的笼统说法：本地缓存、模型缓存、返回体积和请求预算分开说明。

静态分析正确性

- `lint` 不再用整个目录的节/常量判断单个单位的引用。按本文件、本地 `copyFrom`
  继承链和最近的 `all-units.template` 建立作用域；其它单位的同名节不会再掩盖缺失引用。
- 扫描范围外的本地模板也参与引用解析与缓存校验；缺失或无法展开的继承列入 `skipped`。
- 单行和多行三引号值统一解析，块内的 memory 表达式不再跳过检查；独立块注释不作为代码。
  `lint` 与 `explain_actions` 共用逻辑行解析，并正确处理 CRLF。
- 插值括号按逻辑值独立配对，修复 `${x} ${y` 漏报未闭合以及不同配置行互相抵消的问题。
- `explain_actions` 记录触发条件、门控、repeat 和赋值下标中的 memory 读取，支持条件里的
  `readUnitMemory(...)`；按钮动作作为默认入口展开，不再被列为未引用链。
- 修复启动器标记测试多拼一层目录的问题，导入失败改为 FAIL 而非静默 SKIP。
- 新增 29 项标准库回归测试，覆盖引用隔离、本地继承、外部模板缓存失效、三引号、插值和动作图。

MCP 往返次数

- `lookup_key` 支持 `keys=[...]` 批量查询。写一个单位通常要查七八个键，
  逐个查就是七八次往返，而每次往返都要把整个上下文重发一遍 ——
  单次返回只有几百 token，重发的是十万级的上下文。
  批量后内容不变（2357 vs 2310 token），往返从 6 次降到 1 次。
- `lint` 上一版已有 `paths` 批量，这次配套补齐。

MCP 返回体积

- `lint` 的 issues 不再每条重复完整绝对路径。改成 `issue_files` 表 + 下标 `f`，
  路径只出现一次。实测 FanWar（1037 文件、4063 条问题）从 17592 token 降到 5181。
- `lint` 默认 `max_issues` 从 200 降到 100，并新增 `by_code` 汇总 ——
  被截断时也能看出问题分布，决定要不要缩小范围再查。
- `explain_actions` 默认只返回文本图（`fmt="text"`），不再同时给 `text` 和整份 `nodes`。
  同一张图付两遍钱，实测 3078 → 683 token。要完整结构传 `fmt="json"` 或 `"both"`。
- 新增体积回归测试：给三类调用钉了 token 上限，并断言 issues 里不能再出现路径字段。

文档

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
