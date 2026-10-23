# 铁锈战争模组 MCP

`https://github.com/GMBOXMOD/rw-modding-mcp`

给 AI 助手用的《铁锈战争》(Rusted Warfare) 模组开发工具集，通过 [MCP](https://modelcontextprotocol.io) 暴露五个**只读**工具，让助手不用每次翻文档、翻反编译源码就能回答"这个键怎么用"。

## 五个工具

| 工具 | 作用 |
|---|---|
| `lookup_key` | 查一个 luke 键：规范拼写、所属节、版本、值类型、中英文说明与例子；拼错时给近似建议 |
| `search_source` | 在反编译的 Java 源码里搜索，返回文件、行号、匹配行 |
| `get_ref` | 结构化速查表：18 个合法事件、27 个逻辑函数、枚举、内存类型、必须配对使用的键、硬限制 |
| `lint` | 对模组文件或目录跑静态检查；支持批量 `paths`，未改动的文件复用上次结论 |
| `explain_actions` | 画出 事件/autoTrigger → 动作 → alsoTriggerAction 的调用图，标 repeat / 条件 / memory 读写，并做四条静态检查 |

**全部只读**，不会改你的文件。

## 快速开始

```bash
git clone https://github.com/GMBOXMOD/rw-modding-mcp.git
cd rw-modding-mcp
python bootstrap.py --check     # 看环境缺什么
```

然后把这个 `bootstrap.py` 配到你的客户端里即可，**它会自己建虚拟环境、自己装依赖**。

首次启动会花 20–60 秒装 `mcp`，之后都是秒开。

## 客户端配置

不同客户端的配置文件位置和键名不一样，但内层三项是通用的：`command` / `args` / `env`。

**Claude Desktop**（`claude_desktop_config.json`）：

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

**Cursor**（`~/.cursor/mcp.json`）与 **Cline**（`cline_mcp_settings.json`）格式同上。

**VS Code**（`.vscode/mcp.json`）外层键是 `servers`：

```json
{
  "servers": {
    "rusted-warfare": {
      "command": "python",
      "args": ["D:/path/to/rw-modding-mcp/bootstrap.py"]
    }
  }
}
```

> `command` 用 `python` 就行（PATH 里有即可），也可以用绝对路径。
> 不需要设 `cwd` —— 启动器从自身位置推断仓库根目录。

## 性能

改完一个文件就想立刻看到结果，所以这部分单独说明。

### 实测（Windows 11 / 180–1000 文件的模组）

| 场景 | 优化前 | 优化后 |
|---|---|---|
| 冷启动到第一次 lint 返回（19 文件） | 6.14 s | **约 2.4 s** |
| 其中 `initialize` | 5.88 s | **2.30 s** |
| lint 5 个文件（示例集） | 53 ms | **7 ms** |
| lint 19 个文件（minesweeper） | 86 ms | **18 ms** |
| lint 1037 个文件（FanWar） | 3300 ms | **605 ms** |
| 1037 文件里改 1 个再 lint | 3300 ms | **约 640 ms** |

### 做了什么

**1. 探活不再 import 包。** 原来 `has_module()` 用真 `import mcp` 探依赖，而
`import mcp` 会连带加载 pydantic 等依赖，实测 1.8 s —— 启动时这笔钱要付两遍
（探活用一次，服务进程再用一次）。现在探活只用 `find_spec`，并且装好之后落一个
`.venv/.deps-ready` 标记，正常启动完全不启子进程。

**2. 每个文件不再被解析两遍。** `check_file()` 内部又调了一次 `parse_file()`，
现在共用一个带 mtime 记忆的解析结果。

**3. 数据表记忆化。** 三份键名资料共约 500 KB，解析约 50 ms。
长驻服务每次 lint 都要付一遍，现在表没变就直接复用。

**4. 逐文件结果缓存。** 未改动的文件直接复用上次结论。
危险的地方在于**跨文件依赖**：改 A 文件可能让 B 文件的结论变化
（比如 B 的 `[canBuild] name:` 指向 A 里定义的单位）。
所以缓存里存的是「这个文件上次对跨文件集合做过的每一次查询及其答案」，
复用前逐条重放，有一条答案变了就重算那个文件。
改 A 会让依赖 A 的 B 一起重算，改一个无关文件则只有那一个重算。

**5. 缓存位置**（不写进你的模组目录）：

| 平台 | 位置 |
|---|---|
| Windows | `%LOCALAPPDATA%\rw-modding-mcp\lint` |
| 其它 | `$XDG_CACHE_HOME/rw-modding-mcp/lint` 或 `~/.cache/rw-modding-mcp/lint` |

关闭方式：命令行加 `--no-cache`，或设环境变量 `RW_LINT_CACHE=0`。
规则文件或数据表一变，整份缓存自动作废（指纹里带了它们的 mtime）。

### 客户端应保持服务进程常驻

这一点很重要：**stdio 模式下每次调用都可能重起一个进程**，
那样 2.5 s 的启动成本会变成每一次调用的固定开销。

主流客户端（Claude Desktop / Cursor / Cline / VS Code）在会话期间会保持进程存活，
所以只有第一次慢。如果你的客户端每次都重起，建议改用下面的「快速启动」配置
把启动成本再压一截。

### 快速启动（跳过启动器）

`bootstrap.py` 负责自动建 venv 和装依赖，但它自己也要起一个 Python 进程（约 0.6 s）。
依赖装好之后，可以让客户端直接指向 venv 里的解释器：

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

先跑一次 `python bootstrap.py --setup` 确保依赖就绪，再换成这个配置。
Linux / macOS 把 `Scripts/python.exe` 换成 `bin/python`。

## explain_actions

把一段单位配置里的动作链画出来，而不是只报"哪一行错了"。

```bash
python tools/rw_explain.py "path/to/unit.ini"
python tools/rw_explain.py "path/to/unit.ini" --action scanThreatSlot   # 只看某一条链
python tools/rw_explain.py "path/to/unit.ini" --json
```

输出长这样：

```
=== hiddenAction_onHit ===
├─ hiddenAction_onHit
│   trigger: event tookDamage
│   require: if eventSource != nullUnit
│   write  : empty_i, existing, scan_i, weight
  ├─ hiddenAction_scanThreatSlot   ← alsoTriggerAction
  │   repeat : ${THREAT_SLOTS} (=4) 次
  │   write  : empty_i, existing, scan_i
  │   read   : empty_i, existing, scan_i, threat_units
    ├─ hiddenAction_applyThreat   ← alsoTriggerAction
    │   gate   : if memory.scan_i == ${THREAT_SLOTS}
```

**六条能静态判定的规则**：

| 规则 | 查什么 |
|---|---|
| `loop-counter` | 同一触发链上、repeat 之前有没有把循环变量复位成常量；循环体里有没有推进 |
| `unreachable` | 动作定义了，但没有任何入边也没有触发，永远不会被调用 |
| `uninit-memory` | `@memory` 声明了、被读了，但本文件里从没被写过（`setUnitMemory` 与 `updateUnitMemory` 都算写） |
| `index-bound` | 循环下标步长 > 1（跳格）或带偏移（可能越界） |
| `trailing-comment` | 行尾 `#` 注释 —— 引擎不剥，值会带着注释一起解析 |
| `unresolved-edge` | `alsoTriggerAction` 指向的动作不存在 |

`loop-counter` 的复位判断是**沿触发链向上找**的：文件别处写了 `scan_i= 0`，不代表这条链进循环前复位过。

**明确不检查的**（工具会把这些列在输出末尾，不假装能查）：

- 条件表达式在运行时成不成立（只认字面量 `true` / `false`）
- `repeat` 是运行时表达式的情况（只认字面量与 `@global` 常量）
- 跨文件继承（`copyFrom` / `all-units.template`）产生的调用边
- luke 数组的真实长度（引擎自动扩容，没有声明可查）
- 单位最终会不会真的打人

## 数据文件

`references/` 下有三份键名资料，`lookup_key` 和 `lint` 依赖它们：

- `官方代码表（Modding References）.csv` —— 官方 modding 参考表
- `单位代码表Modding API Reference.txt` —— 中文代码表
- `二进制键名.txt` —— 从 `game-lib.jar` 常量池导出的键名（1472 个），补前两份没收录的键

前两份是人工维护的，**必然有漏**。实测 `showMiniHp`、`useAsAttacker` 都是原版在用的合法键，
但两份表都没有 —— 只靠它们会产生大量「未知键」假阳性。第三份就是为此存在的。

另外，`animation_*`、`mutator*`、`builtFrom_#_*`、`body_*` 这类**带参数的键族**
在代码表里只有模板形式、查不到具体拼写，linter 按前缀/模板整族放行
（依据是反编译里 `ab2.e("animation_")`、`f.java` 的 `startsWith("body")` 这些写法）。

如果缺失，`lookup_key` 会查不到东西。你可以放自己的副本进去，或用环境变量指定：

```
RW_CSV=/path/to/官方代码表.csv
RW_CN=/path/to/单位代码表.txt
```

## search_source 需要反编译

`search_source` 读的是**反编译产物**，仓库里**不包含**它（见下面的法务说明）。
你需要用自己游戏里的 `game-lib.jar` 生成一次：

```bash
python bootstrap.py --decompile
```

它会：
1. 自动找游戏安装目录（或用 `--game` 指定）
2. 下载 CFR 反编译器（约 2 MB，来自 Maven 中央仓库）
3. 把 `game-lib.jar` 反编译到 `tools/jar/src/`

需要 JDK 17+（`JAVA_HOME` 或 PATH 里有 `java`）。

没做这一步也能用，只是 `search_source` 会返回空。

## 关于反编译产物

`tools/jar/src/` 是**游戏厂商代码的反编译结果**，版权属于原作者。
本仓库**不包含**也不应包含它，`.gitignore` 已排除。

同理，`tools/jar/cfr.jar` 也不入库（用的时候自动下载）。

## 目录结构

```
bootstrap.py            通用启动器（自动建 venv / 装依赖 / 检查数据）
tools/
  rw_mcp_server.py      MCP 服务入口
  rw_mcp/
    dataset.py          路径解析 + 数据缓存 + Java 源码索引
    impl.py             五个工具的实现
    selftest.py         自检（34 项）
  rw_lint.py            静态检查器（也可单独当命令行用）
  rw_cache.py           两级缓存：解析记忆 + 带依赖校验的逐文件结果缓存
  game_loadtest.py      进游戏加载测试（无窗口，需要本机装游戏）
references/             键名资料
```

## 单独用命令行

这些工具不装 MCP 也能用：

```bash
python tools/rw_lint.py "D:/path/to/yourmod"        # 静态检查（自动增量）
python tools/rw_lint.py "D:/path/to/yourmod" --timing  # 顺便看耗时与缓存命中
python tools/rw_lint.py "D:/path/to/yourmod" --no-cache # 强制全量重算
python tools/rw_lint.py --ref                        # 打印速查表
python tools/rw_lint.py --json                       # 机器可读输出
python tools/rw_mcp/selftest.py                      # 自检
```

`game_loadtest.py` 会真的启动游戏做加载测试（无窗口），需要本机装了 Rusted Warfare：

```bash
python tools/game_loadtest.py "D:/path/to/yourmod"
```

## 局限（先说清楚，免得误用）

这个工具**不能替你做判断**，它只负责把资料摆出来。

**1. 它不知道表对不对。**
`lookup_key` 的权威性完全来自 `references/` 里那两张第三方表。表本身有错、或者版本比你的游戏旧，
它照样会返回 `found: true` 加一段看着很自信的解释。
为了缓解这一点，返回里带 `agreement` 字段：`both` 表示两张表都收录，`csv_only` / `cn_only`
表示只有一张有 —— 那通常意味着表有缺口或版本不同步，值得你自己复核一眼。
**它没法判断谁对。**

**2. 查不到会明说，多个候选会拒绝猜。**
兜底匹配只忽略下划线和大小写，**不剥数字**（`customTarget1` 和 `customTarget2` 是两个键）。
如果一个查询同时匹配多个键，它会返回 `match: "ambiguous"` 并列出候选，而不是随便挑一个。

**3. lint 只管语法和引用。**
键名拼写、配对规则、资源引用、必填键 —— 这些它查。但**逻辑对不对它不知道**。
一个状态机断在第几步、仇恨值到底有没有累积、单位为什么不打人，linter 可能全绿。

**4. `search_source` 依赖你自己反编译。**
产物和你的游戏版本绑定；换了游戏版本要重新 `--decompile`。
返回的是 Java 源码片段，上下文噪声大，适合回答"引擎怎么做的"，不适合查键。

**5. 只改一两个文件时，直接读表更快。**
MCP 的价值在"频繁查证 + 结构化输出 + 省上下文"。偶尔改一处，打开编辑器翻文档比装这个快。

**6. 它是 0 star 的新项目。**
`bootstrap.py` 会自动建 venv、pip 装依赖、按需下载 CFR。代码是只读的、有坏样本回归测试，
但跑之前你自己过一眼总没坏处。

## 常见问题

**启动失败，日志在哪？**
仓库根目录的 `bootstrap.log`。pip 的输出、反编译的命令行都在里面。

**提示"安装依赖失败"？**
多半是网络问题。试试换镜像：

```bash
.venv/Scripts/python -m pip install -i https://mirrors.aliyun.com/pypi/simple mcp
```

**`lookup_key` 什么都查不到？**
`references/` 里的两份表缺了，或者文件名不对（代码会做归一化匹配，但至少要有一份）。

**`search_source` 返回空？**
还没反编译，跑 `--decompile`。

**Python 版本？**
需要 3.10+（`mcp` SDK 的要求）。

**为什么不装最新的 `mcp`？**
`bootstrap.py` 装的是 `mcp>=2.3,<3`。因为 2.x 把 `FastMCP` 改名成了 `MCPServer`（破坏性变更），
不锁主版本的话，上游哪天发 3.x 再改个名，用户装完就是 `ModuleNotFoundError`。
服务端代码里做了 1.x / 2.x 双兼容的 import shim，但依赖本身还是锁住更稳。

## 许可

MIT。见 `LICENSE`。

`references/` 里的键名资料版权归各自作者，此处仅作分发便利，如原作者有异议请提 issue 删除。
