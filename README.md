# 铁锈战争模组 MCP

《铁锈战争》模组开发的 MCP 服务端，五个只读工具。

仓库 `https://github.com/GMBOXMOD/rw-modding-mcp`，变更见 [CHANGELOG.md](CHANGELOG.md)。

## 工具

| 工具 | 作用 |
|---|---|
| `lookup_key` | 按节查键，默认短释义与例子，保留来源、资料冲突和约束；完整资料按需取 |
| `search_source` | 批量搜 Java 源码，带有限上下文、分页、空结果诊断和内容预算 |
| `get_ref` | 按主题和名称查事件、函数、枚举、内存类型与规则；无参数保留完整速查表 |
| `lint` | 静态检查文件或目录；支持批量 `paths`，未改动的文件复用上次结论 |
| `explain_actions` | 画 事件/autoTrigger/按钮 → 动作 → alsoTriggerAction 的调用图，标 repeat、条件、memory 读写 |

全部只读，不改你的文件。

查多个键用 `lookup_key(keys=[...])`，检查多个文件用 `lint(paths=[...])`。
批量查询能减少模型往返，精简输出能减少进入上下文的资料量；实际费用取决于客户端、模型和缓存。
本地 lint 缓存只节省检查时间，不是模型的提示词缓存。MCP 也不能限制客户端的 Bash、子 agent 或模型请求预算。

## 定向查询与返回预算

下面是 MCP 工具参数示例，不需要在终端执行：

```python
lookup_key(keys=["isVisible", "isActive", "displayType"], section="action")
lookup_key(key="isVisible", section="action", detail="full")
get_ref(topic="events", name="killedAnyUnit")
get_ref(topic="enums", name="movementType")
get_ref(topic="rules", name="alwaysSinglePress")
search_source(patterns=["setUnitStats", "setUnitMemory"], path_filter="custom/")
search_source(pattern="EventSourceReference|teamId", mode="regex")
```

- `lookup_key` 默认 `detail="brief"`：每个节最多一条短释义/例子，最多展示三个节。
  长说明标 `truncated`，过长的例子用 `example_omitted` 标明省略，不返回半段配置；未展示的节标 `entries_omitted`。
  约束、资料冲突和重要说明保留。
  `section` 接受 `action`、`[action_btn]` 或 `M` 等节名/章节字母。
  `section_match=false` 表示资料没有确认指定节的用法，不等于该键在引擎里绝对不可用。
  一次最多 32 个不同的键，重复输入只查一次；`count` 是去重后的数量，`requested_count` 是输入数量。
- **返回形状变化**：默认模式不再返回原始 `csv` / `cn` 数组，改用 `entries`；依赖原始字段的程序
  请显式传 `detail="full"`。旧的位置参数保留，完整模式保留原有原始资料字段。
- `search_source` 默认 `10` 条匹配、前后各 `2` 行（`context_lines` 可设 `0–5`）。
  `patterns` 一次最多 8 个不同的查询，同一行匹配多个词只返回一次，计数见 `by_pattern`。
  `mode="literal"` 按原文匹配，找 `%{` 就直接传 `%{`，不要写 `%\{`。
  正则使用 `mode="regex"`；旧的 `regex=True` 仍可用，但不能与 `mode="literal"` 冲突。
  `path_filter` 是路径子串而非 glob。空结果看 `reason` / `hints`，不会擅自改模式或扩大范围。
- 搜索的 `max_chars` 默认 `8000`，范围 `1000–20000`，限制 `matches` 的紧凑 JSON 字符数，
  **不包含结果元数据，也不是 token 数**。数量或字符预算达到上限时，用 `next_offset` 作为下次的 `offset`。
  超长匹配行/上下文会标明截短；分页只在进程内源码索引不变时稳定，重新反编译后需重启服务。
- `get_ref()` 无参数仍返回完整速查表。常用主题：`events`、`functions`、`enums`、`memory`、
  `sections`、`rules`、`must_pair`、`hard_constraints`。`name` 按名称筛选，需同时指定 `topic`。
  这轮只查询已有资料；没有新增教程模板，也不把“名称收录”当作运行时语义已验证。

普通单位建议先定向查询，再写文件并检查；是否启动多 agent 或继续源码研究，应由客户端单独征得用户同意并设置预算。

## 安装

需要 Python 3.10+。

```bash
git clone https://github.com/GMBOXMOD/rw-modding-mcp.git
cd rw-modding-mcp
python bootstrap.py --check     # 看环境缺什么
```

首次启动会自动建 venv、装 `mcp`，约 20–60 秒。

## 客户端配置

```json
{
  "mcpServers": {
    "rusted-warfare": {
      "command": "python",
      "args": ["D:/path/to/rw-modding-mcp/bootstrap.py"]
    }
  }
}
```

Claude Desktop 写进 `claude_desktop_config.json`，Cursor 写进 `~/.cursor/mcp.json`，Cline 写进 `cline_mcp_settings.json`。VS Code 的 `.vscode/mcp.json` 外层键是 `servers`，里面一样。

不用设 `cwd`。`command` 写 `python` 或绝对路径都行。

启动约 2.4 秒，客户端要在会话期间保持进程存活。想再快一点可以跳过启动器：

```json
{
  "mcpServers": {
    "rusted-warfare": {
      "command": "D:/path/to/rw-modding-mcp/.venv/Scripts/python.exe",
      "args": ["D:/path/to/rw-modding-mcp/tools/rw_mcp_server.py"]
    }
  }
}
```

先跑一次 `python bootstrap.py --setup`。Linux/macOS 把 `Scripts/python.exe` 换成 `bin/python`。

## explain_actions

```bash
python tools/rw_explain.py "path/to/unit.ini"
python tools/rw_explain.py "path/to/unit.ini" --action scanThreatSlot   # 只看一条链
python tools/rw_explain.py "path/to/unit.ini" --json
```

MCP 里默认只返回文本图，要完整结构传 `fmt="json"`。

报这六条：

| 规则 | 查什么 |
|---|---|
| `loop-counter` | 同一触发链上、repeat 之前有没有把循环变量复位成常量；循环体里有没有推进 |
| `unreachable` | 动作定义了，但没入边也没触发，永远不会被调用 |
| `uninit-memory` | `@memory` 被读了但本文件从没写过（`setUnitMemory` 和 `updateUnitMemory` 都算写） |
| `index-bound` | 循环下标步长 > 1（跳格）或带偏移（可能越界） |
| `trailing-comment` | 行尾 `#` 注释——引擎不剥，值会带着注释一起解析 |
| `unresolved-edge` | `alsoTriggerAction` 指向的动作不存在 |

运行时条件真假、运行时 `repeat`、`copyFrom` 带来的跨文件边、数组真实长度，这些它不查，会在输出末尾列出来。

`lint` 的引用检查按当前单位及其本地继承链隔离，支持相对 `copyFrom`、`ROOT:`、基础 `CORE:` 和最近的
`all-units.template`。缺失或无法展开的继承（如无法定位原版目录、动态路径）列在 `skipped`，不能视为已经验证。
此继承支持只用于 `lint`，`explain_actions` 仍只分析单个文件。

## CORE: 基础支持

`copyFrom: CORE:tanks/tank.ini` 从游戏的 `assets/units/tanks/tank.ini` 读取原版配置，
不是从 `mods/units` 读取。只收集继承链中的节、常量等定义用于引用检查；不会修改、复制原版文件或启动游戏。

定位顺序：CLI 的 `--core-units` 参数、`RW_CORE_UNITS` 环境变量、指定的 game-lib.jar 所在目录
（`--jar` / `RW_GAME_JAR`）、被检查文件所在的游戏目录、常见安装位置。
显式 `--core-units` / `RW_CORE_UNITS` 路径无效时不悄悄换到另一份游戏。

```powershell
.venv/Scripts/python.exe tools/rw_lint.py "D:/path/to/mod" --core-units "D:/path/to/game/assets/units"
# MCP 客户端则在服务环境中设置 RW_CORE_UNITS，之后重启服务。
```

- 找不到原版目录时标记未解析；目录已定位但目标缺失、不可读或越界时报告 `E17`。
- CLI JSON 与 MCP 结果中的 `core` 列出原版目录、引用/已读取/未解析数量。
- **`core.mode="symbols_only"` 不代表完整单位验证通过**：不计算最终键值合并与覆盖，不执行运行时表达式。
  仍未检查的范围列在 `core.not_checked`。图片/音频中的 `CORE:`、`SHARED:` 资源路径也不在本轮范围内。
- 相关原版文件或目录配置变化会使依赖它的检查缓存失效，不让无关单位全部重算。

## 命令行

不装 MCP 也能用：

```bash
python tools/rw_lint.py "D:/path/to/yourmod"            # 静态检查（自动增量）
python tools/rw_lint.py "D:/path/to/yourmod" --timing   # 看耗时与缓存命中
python tools/rw_lint.py "D:/path/to/yourmod" --no-cache # 强制全量
python tools/rw_lint.py --ref                           # 速查表
python tools/rw_lint.py --json                          # 机器可读
python tools/rw_mcp/selftest.py                         # 自检
python tools/game_loadtest.py "D:/path/to/yourmod"      # 进游戏加载测试（无窗口）
```

## 可选测试依赖与外部模组

工作流 YAML 校验需要在运行测试的 Python 环境安装 `PyYAML`，例如：

```powershell
.venv/Scripts/python.exe -m pip install PyYAML
.venv/Scripts/python.exe tests/run_tests.py
```

真实样本 `示例`、`minesweeper`、`Kings of Cards` 会依次从 `RW_TEST_MOD_ROOTS`、仓库内部、仓库旁边查找。
其它位置可用环境变量指定多个父目录（Windows 用分号，Linux/macOS 用冒号）：

```powershell
$env:RW_TEST_MOD_ROOTS = "D:/path/to/collection;D:/path/to/game/mods/units"
.venv/Scripts/python.exe tests/run_tests.py
.venv/Scripts/python.exe tools/rw_mcp/selftest.py
```

这些测试只读取模组，验证缓存前后与 CLI/MCP 的结果一致，不代表模组诊断为零，也不等于游戏加载已通过。
`skipped` 中未展开的继承仍需单独处理；这里不会复制模组或启动游戏。

## search_source 需要反编译

```bash
python bootstrap.py --decompile
```

需要 JDK 17+，会自动找游戏目录（或用 `--game` 指定）。不做这步 `search_source` 返回空。

## 数据文件

`references/` 下三份，缺了 `lookup_key` 查不到东西：

- `官方代码表（Modding References）.csv`
- `单位代码表Modding API Reference.txt`
- `二进制键名.txt`

换自己的副本：`RW_CSV` / `RW_CN`（只对 MCP 生效，`lint` 命令行不读）。

## 常见问题

**启动失败** 看仓库根的 `bootstrap.log`。

**装依赖失败** 多半是网络，换镜像：

```bash
.venv/Scripts/python -m pip install -i https://mirrors.aliyun.com/pypi/simple mcp
```

**lint 全绿但单位不打人** 它只管语法和引用，逻辑对不对要自己跑。

**`lookup_key` 说的不对** 表是第三方维护的。返回里的 `agreement` 说明两张表都有还是只有一张，谁对得自己判断。

**缓存** 在 `%LOCALAPPDATA%\rw-modding-mcp\lint`（Linux/macOS 走 `~/.cache`），`--no-cache` 或 `RW_LINT_CACHE=0` 关掉。

## 许可

MIT，见 `LICENSE`。`references/` 里的键名资料版权归各自作者，原作者有异议请提 issue 删除。
