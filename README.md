# 铁锈战争模组 MCP

《铁锈战争》模组开发的 MCP 服务端，五个只读工具。

仓库 `https://github.com/GMBOXMOD/rw-modding-mcp`，变更见 [CHANGELOG.md](CHANGELOG.md)。

## 工具

| 工具 | 作用 |
|---|---|
| `lookup_key` | 查 luke 键：规范拼写、所属节、版本、值类型、中英文说明与例子；拼错时给近似建议 |
| `search_source` | 搜反编译的 Java 源码，返回文件、行号、匹配行 |
| `get_ref` | 速查表：18 个事件、27 个逻辑函数、枚举、内存类型、必须配对的键、硬限制 |
| `lint` | 静态检查文件或目录；支持批量 `paths`，未改动的文件复用上次结论 |
| `explain_actions` | 画 事件/autoTrigger → 动作 → alsoTriggerAction 的调用图，标 repeat、条件、memory 读写 |

全部只读，不改你的文件。

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
