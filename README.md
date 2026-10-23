# 铁锈战争模组 MCP

给 AI 助手用的《铁锈战争》模组开发工具集，通过 [MCP](https://modelcontextprotocol.io) 接入。

`https://github.com/GMBOXMOD/rw-modding-mcp`

改了什么见 [CHANGELOG.md](CHANGELOG.md)。

## 五个工具

| 工具 | 作用 |
|---|---|
| `lookup_key` | 查 luke 键：规范拼写、所属节、版本、值类型、中英文说明与例子；拼错时给近似建议 |
| `search_source` | 搜反编译的 Java 源码，返回文件、行号、匹配行 |
| `get_ref` | 速查表：18 个事件、27 个逻辑函数、枚举、内存类型、必须配对的键、硬限制 |
| `lint` | 静态检查文件或目录；支持批量 `paths`，未改动的文件复用上次结论 |
| `explain_actions` | 画 事件/autoTrigger → 动作 → alsoTriggerAction 的调用图，标 repeat、条件、memory 读写 |

全部只读，不改你的文件。

## 安装

```bash
git clone https://github.com/GMBOXMOD/rw-modding-mcp.git
cd rw-modding-mcp
python bootstrap.py --check     # 看环境缺什么
```

客户端里指向 `bootstrap.py`，它会自己建 venv、装依赖：

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

Claude Desktop 用 `claude_desktop_config.json`，Cursor 用 `~/.cursor/mcp.json`，Cline 用 `cline_mcp_settings.json`，格式同上。VS Code 的 `.vscode/mcp.json` 外层键叫 `servers`，里面一样。

`command` 写 `python` 就行（PATH 里有），也可以给绝对路径。不用设 `cwd`。

首次启动装 `mcp` 要 20–60 秒，之后每次约 2.4 秒。

## 性能

| 场景 | 耗时 |
|---|---|
| 冷启动到第一次 lint | 约 2.4 s |
| lint 19 个文件 | 18 ms |
| lint 1037 个文件 | 605 ms |
| 1037 文件里改 1 个再 lint | 约 640 ms |

未改动的文件复用上次结论，跨文件依赖会一并校验：改 A 会让依赖 A 的 B 一起重算。

缓存放在 `%LOCALAPPDATA%\rw-modding-mcp\lint`（Linux/macOS 走 `~/.cache`），不写你的模组目录。`--no-cache` 或 `RW_LINT_CACHE=0` 关掉。

客户端要保持服务进程常驻。stdio 下进程每次都重起的话，2.4 秒会变成每次调用的固定成本。依赖装好之后可以跳过启动器，直接指向 venv 解释器，再省 0.6 秒：

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

只报"哪一行错了"不够，有时候要知道动作链怎么串起来的。

```bash
python tools/rw_explain.py "path/to/unit.ini"
python tools/rw_explain.py "path/to/unit.ini" --action scanThreatSlot   # 只看一条链
python tools/rw_explain.py "path/to/unit.ini" --json
```

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
    │   require: if memory.weight > 0 and (memory.existing >= 0 or memory.empty_i >= 0)
    │   gate   : if memory.scan_i == ${THREAT_SLOTS}
    │   write  : scan_i, threat_units, threat_value
    │   read   : empty_i, existing, scan_i, threat_value, weight
```

六条能静态判定的规则：

| 规则 | 查什么 |
|---|---|
| `loop-counter` | 同一触发链上、repeat 之前有没有把循环变量复位成常量；循环体里有没有推进 |
| `unreachable` | 动作定义了，但没入边也没触发，永远不会被调用 |
| `uninit-memory` | `@memory` 被读了但本文件从没写过（`setUnitMemory` 和 `updateUnitMemory` 都算写） |
| `index-bound` | 循环下标步长 > 1（跳格）或带偏移（可能越界） |
| `trailing-comment` | 行尾 `#` 注释——引擎不剥，值会带着注释一起解析 |
| `unresolved-edge` | `alsoTriggerAction` 指向的动作不存在 |

`loop-counter` 沿触发链向上找复位。文件别处写了 `scan_i= 0`，不算这条链复位过。

不检查的会列在输出末尾：运行时条件真假、运行时 `repeat`、`copyFrom` 和 `all-units.template` 带来的跨文件边、luke 数组的真实长度、单位最后到底会不会打人。

## 命令行

不装 MCP 也能用：

```bash
python tools/rw_lint.py "D:/path/to/yourmod"            # 静态检查（自动增量）
python tools/rw_lint.py "D:/path/to/yourmod" --timing   # 看耗时与缓存命中
python tools/rw_lint.py "D:/path/to/yourmod" --no-cache # 强制全量
python tools/rw_lint.py --ref                           # 速查表
python tools/rw_lint.py --json                          # 机器可读
python tools/rw_mcp/selftest.py                         # 自检
```

`game_loadtest.py` 会真的启一次游戏做加载测试（无窗口），需要本机装着游戏：

```bash
python tools/game_loadtest.py "D:/path/to/yourmod"
```

## 数据与反编译

`references/` 下三份键名资料，`lookup_key` 和 `lint` 都依赖它们：

- `官方代码表（Modding References）.csv` — 官方参考表
- `单位代码表Modding API Reference.txt` — 中文代码表
- `二进制键名.txt` — 从 `game-lib.jar` 常量池导出的 1472 个键

前两份人工维护，有漏。`showMiniHp`、`useAsAttacker` 是原版在用的合法键，两份表都没收，只靠它们会刷一屏假阳性。第三份补的就是这个。`animation_*`、`mutator*`、`builtFrom_#_*`、`body_*` 这类带参数的键族在表里只有模板形式，linter 按前缀和模板整族放行。

想换自己的副本，`lookup_key` 认 `RW_CSV` 和 `RW_CN` 两个环境变量（`lint` 命令行不读这两个）。

`search_source` 读的是反编译产物，仓库里没有。用自己游戏里的 `game-lib.jar` 生成一次：

```bash
python bootstrap.py --decompile
```

它会找游戏目录（或用 `--game` 指定）、下载 CFR（约 2 MB）、反编译到 `tools/jar/src/`，需要 JDK 17+。不做这步也能用，只是 `search_source` 返回空。

反编译结果是游戏厂商的代码，版权归原作者。仓库不含也不该含它，`.gitignore` 已排除，`cfr.jar` 同理（用的时候下载）。

## 目录结构

```
bootstrap.py            启动器（建 venv / 装依赖 / 检查数据）
tools/
  rw_mcp_server.py      MCP 服务入口
  rw_mcp/
    dataset.py          路径解析 + 数据缓存 + Java 源码索引
    impl.py             五个工具的实现
    selftest.py         自检（34 项）
  rw_lint.py            静态检查器
  rw_cache.py           两级缓存
  rw_explain.py         动作调用图
  game_loadtest.py      进游戏加载测试
references/             键名资料
```

## 局限

`lookup_key` 的权威性来自那两份第三方表。表本身有错、或者版本比你的游戏旧，它照样返回 `found: true` 配一段看着很自信的解释。返回里的 `agreement` 字段能看出是两张表都有还是只有一张，谁对得你自己判断。

`lint` 只管语法和引用。键名拼写、配对规则、资源引用、必填键它查；状态机断在第几步、仇恨值有没有累积、单位为什么不打人，它可能全绿。

`search_source` 跟你的游戏版本绑定，换版本要重新反编译。返回的是 Java 片段，适合问"引擎怎么做的"，不适合查键。

偶尔改一处，直接翻表比装这个快。MCP 的价值在频繁查证和结构化输出。

这个项目 0 star。`bootstrap.py` 会建 venv、装依赖、按需下载 CFR，代码只读、有回归测试，跑之前自己过一眼。

## 常见问题

启动失败看仓库根的 `bootstrap.log`，pip 输出和反编译命令都在里面。

装依赖失败多半是网络问题，换镜像：

```bash
.venv/Scripts/python -m pip install -i https://mirrors.aliyun.com/pypi/simple mcp
```

`lookup_key` 查不到东西，是 `references/` 里两份表缺了。

需要 Python 3.10+。装的是 `mcp>=2.3,<3`——2.x 把 `FastMCP` 改名成 `MCPServer`，不锁主版本的话上游发 3.x 再改个名，用户装完就是 `ModuleNotFoundError`。

## 许可

MIT，见 `LICENSE`。

`references/` 里的键名资料版权归各自作者，此处仅作分发便利，原作者有异议请提 issue 删除。
