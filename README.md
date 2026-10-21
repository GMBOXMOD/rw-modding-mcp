# 铁锈战争模组 MCP

`https://github.com/GMBOXMOD/rw-modding-mcp`

给 AI 助手用的《铁锈战争》(Rusted Warfare) 模组开发工具集，通过 [MCP](https://modelcontextprotocol.io) 暴露四个**只读**工具，让助手不用每次翻文档、翻反编译源码就能回答"这个键怎么用"。

## 四个工具

| 工具 | 作用 |
|---|---|
| `lookup_key` | 查一个 luke 键：规范拼写、所属节、版本、值类型、中英文说明与例子；拼错时给近似建议 |
| `search_source` | 在反编译的 Java 源码里搜索，返回文件、行号、匹配行 |
| `get_ref` | 结构化速查表：18 个合法事件、27 个逻辑函数、枚举、内存类型、必须配对使用的键、硬限制 |
| `lint` | 对模组文件或目录跑静态检查，返回结构化错误/警告 |

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

## 数据文件

`references/` 下有两份键名资料，`lookup_key` 和 `lint` 依赖它们：

- `官方代码表（Modding References）.csv` —— 官方 modding 参考表
- `单位代码表Modding API Reference.txt` —— 中文代码表

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
    impl.py             四个工具的实现
    selftest.py         自检（22 项）
  rw_lint.py            静态检查器（也可单独当命令行用）
  game_loadtest.py      进游戏加载测试（无窗口，需要本机装游戏）
references/             键名资料
```

## 单独用命令行

这些工具不装 MCP 也能用：

```bash
python tools/rw_lint.py "D:/path/to/yourmod"        # 静态检查
python tools/rw_lint.py --ref                        # 打印速查表
python tools/rw_lint.py --json                       # 机器可读输出
python tools/rw_mcp/selftest.py                      # 自检
```

`game_loadtest.py` 会真的启动游戏做加载测试（无窗口），需要本机装了 Rusted Warfare：

```bash
python tools/game_loadtest.py "D:/path/to/yourmod"
```

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

## 许可

MIT。见 `LICENSE`。

`references/` 里的键名资料版权归各自作者，此处仅作分发便利，如原作者有异议请提 issue 删除。
