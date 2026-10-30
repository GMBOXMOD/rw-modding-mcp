---
name: rusted-warfare-modding
description: 指导《铁锈战争》(Rusted Warfare) 模组开发，使用 "luke 语"（[section]+key:value 配置语言）编写单位、建筑、武器、特效、行动逻辑、UI 与非战斗模组。当用户提到铁锈战争 / Rusted Warfare mod、luke 语、.ini/.template 单位定义、[core]/[turret_N]/[projectile_N]/[action_N]/[hiddenAction_N]/[decal_*]/[resource_*] 等节、copyFrom 继承、${...}/%{...} 插值、残骸 wreak、模组双语与 mod-info.txt、键名版本与 minVersion、以及"这个键叫什么 / 该不该这么写 / 为什么会静默失效"时，使用本技能。
agent_created: true
---

# 铁锈战争模组开发（指南）

**本技能只负责判断力：怎么写、为什么这么写、哪里会静默失效。**

事实查询和代码校验交给 **`rusted-warfare` MCP**（`lookup_key` / `get_ref` / `lint` / `explain_actions` / `search_source`）。
两边不重复——MCP 回答"这个键叫什么、有没有、从哪版起"，本技能回答"该不该这么写、什么时候会坏"。

## 分工

| 你要做的事 | 用什么 |
|---|---|
| 查键名 / 版本 / 取值 / 例子 / 拼错建议 | MCP `lookup_key` |
| 查事件、函数、枚举、内存类型、硬限制 | MCP `get_ref` |
| 查某段逻辑在引擎源码里怎么实现 | MCP `search_source` |
| 检查语法、引用、双语、minVersion、键放错节 | MCP `lint` |
| 看动作链、循环变量、不可达、内存读写 | MCP `explain_actions` |
| **真把游戏跑起来**（缺图、引擎侧校验） | 本仓库的 `tools/game_loadtest.py`（命令行脚本，不是 MCP 工具） |
| 该不该这么写 / 有哪些坑 / 技法分级 / 设计范式 | 本技能 + `references/铁锈战争模组开发Agent指南.md` |

MCP 没装时怎么办：见文末「降级路径」。

## 一条总铁律

**先查，再写；查真实文件，不要凭记忆。**

luke 语的节名 / 键名**区分大小写**，拼错不报错、只会静默失效。动手前先打开最近邻的真实节，照抄它的节名、键名、大小写、缩进，再改。注释、他人指南乃至本参考都可能滞后于引擎版本——涉及名字、清单、继承关系、具体行为时，一律以真实代码的实际表现为准。

> **引用真实模组代码的一条铁律：一律中性化，不直接照搬。**
>
> 从任何模组（包括社区高手的作品）里提炼可复用结构时，**必须抹掉具体模组的私有单位名 / 节名 / 标签 / 数值 / 文案 / 业务规则**，改写为中性占位名（`myunit`、`mycontroller`、`mycell`、`nano_proxy` 等）。
>
> 原因：**照搬会让 Agent 写出"某位作者的味道"**——继承他的个人命名习惯、他的补丁式绕行技巧和他的业务规则，而这些往往既不是通用做法、也随版本过时。**学习的是"结构"，不是"源码"**。

> **⚠️ 最关键的一条：高超 ≠ 常见 ≠ 推荐。** 真实模组里的高超技法**不一定是通用最佳实践**——很多是当年**绕引擎限制**的产物（手搓 if/else、手搓 PRNG、手工 for 循环、隐形代理扩展范围……），有些**随版本已过时**。**绝不要把这类 hack 当"标准做法"推广给用户。** 引用任何范例前先自问：**"这是通用规律，还是绕限制的 hack？"** 技法分三级：🟢 通用规律（可借鉴）/ 🟡 可用但有更优解 / 🔴 已过时（勿照搬）。**新版本有官方写法时一律用官方的。**

## 工作流程

1. **核实结构**：打开目标工程里的真实单位文件，确认已有的节名、键名、`copyFrom` 链。参考工程的目录分工惯例（静态母版 `*.template` + 活体 `.ini` + 残骸 `w_*.ini` 三件套）。
2. **查键名**：`lookup_key`（要查多个就一次传 `keys=[...]`，省往返）。不确定能不能用某个键时，**先看它从哪个版本才有**，再对 `mod-info.txt` 的 `minVersion`。
3. **照抄再改**：复制最近邻真实写法，只改需要改的键。
4. **自检**：`lint`（改完一个文件就只查那个文件，别每次扫整包）。错误必修，警告要判断。
5. **看逻辑**：涉及动作链、循环、状态机时跑 `explain_actions`——它能画出 事件 → 动作 → alsoTriggerAction 的边，标出门控、repeat 次数、memory 读写。
6. **实测**：跑本仓库的 `tools/game_loadtest.py`，把游戏真加载一次。**lint 全绿 ≠ 能加载**——缺图、引擎侧校验失败只有这一步能抓到。
7. **查不到的留空**，写明"未验证"，交给用户进游戏实测。

## lint 规则号速查

`lint` 返回的 code 直接对应下表。错误（E）几乎肯定是 bug；警告（W）要结合上下文判断。

| 号 | 查什么 |
|---|---|
| E01 | 键名大小写 / 拼写错（附模糊匹配到的正确键） |
| E02 | 全角冒号 `：` 当半角用 |
| E03 | `"""` 数量为奇数（会吞掉后面整段配置） |
| E04 | `${` 与 `}` 不配对 |
| E06 | `projectile:` / `turret:` 引用了不存在的节 |
| E07 | 文件带 BOM |
| E08 | `displayType` / `movementType` / `layer` 取值不在枚举里 |
| E09 | 纯数字键填了非数字 |
| E10 | `autoTriggerOnEvent` 事件名不存在（18 个合法值） |
| E11 | `[hiddenAction_*]` 里写了 `isVisible`（加载期抛异常） |
| E12 | `addActionCooldownApplyToActions` 缺 `addActionCooldownTime` |
| E13 | `@memory` 类型不合法 |
| E14 | `canAttack: true` 缺三个目标类型键（引擎不给默认值） |
| E15 | `@memory` / `@global` / `@define` 行尾写了注释 |
| W01 | 未知键（三份资料都查不到，且没被 `${}` 引用） |
| W02 | 双语基键 / `_zh` 只写了一侧 |
| W03 | 用了 1.15p9+ 的键却没声明 `minVersion` |
| W04 | 键的版本高于 `mod-info.txt` 声明的 `minVersion` |
| W05 | `copyFrom` / `alsoTriggerAction` 引用了找不到的节 |
| W06 | 节里没有任何键 |
| W07 | 节头重复（键会合并 / 覆盖） |
| W08 | 同一节里重复写同一个键（后者静默覆盖前者） |
| W09 | `${x}` 找不到 `@global` / `@define` 声明（游戏里静默变空） |
| W10 | 插值用反：按钮文本用 `${}`，或 `setUnitMemory` 里用 `%{}` |
| W11 | `[canBuild_*] name:` 指向不存在的单位（原版名也算合法） |
| W12 | 键放错节 |
| W13 | `alsoTriggerActionRepeat` 没配 `alsoTriggerAction`（完全无效） |
| W14 | `alsoTriggerActionRepeat: 0`（不是"不重复"，是取消整个派生动作） |
| W15 | `alwaysSinglePress: true` 缺 `canPlayerCancel: false` / `allowMultipleInQueue: false` |
| W16 | 用了不存在的函数（`abs` / `floor` / `pow`…）或函数名疑似拼错 |

**已知不查**：表达式内容合法性、`copyFrom` 路径是否存在、继承链覆盖关系、逻辑对不对。

## 写之前必读的硬事实

- **武器 = `[turret_N]` + `[projectile_N]` + `[effect_*]` 三件套，没有 `[arm_*]`。** 炮塔用 `projectile:` 指向弹丸节（数字对数字、自定义名对同名节）。
- **散布键是 `aimOffsetSpread`，不是 `aimOffsets`。**
- **继承 = 最后写入者获胜**：引擎默认 < `all-units.template`（按文件名自动套用）< `copyFrom` 链（按列出顺序）< 单位自身内联键；**节按键逐个合并、不整体替换**。
- **三种插值分清**：`${...}` 载入期展开一次（含编译期数学 `${int(...)}` / `${sqrt(...)}`）；`%{...}` 运行期每帧求值（UI 文本专用）；`${节.键}` 载入期复制另一节的键值。
- **`"""` 既是多行串又是块注释，必须偶数配对**；漏配对会吞掉后续整段配置。
- **双语成对**：单位 / 行动 / 资源文件里 **基键 = 英文、`_zh` = 中文**；但 **`mod-info.txt` 方向相反**（基键 = 中文、`_en` = 英文）。语言中立标签可单侧。
- **`IGNORE` 是万能占位值（必须全大写）**，任何键都能填，用于阻断从父层继承来的某个键。
- **静态进母版、动态留活体**：造价 / 血量 / 贴图等进 `.template`；`[movement]`、攻击逻辑等若残骸不该继承就留在活体 `.ini`。
- **残骸（wreak）只 `copyFrom` 静态母版**，不继承行为模板。
- **数组**自 1.15p11 加入（上限 10000，下标从 0）；**取长度用 `.size`**——`length(string)` 是字符串专用。跨单位读数组有重定向 bug，用 `.get(N)` 绕开。用 decal / 数组时 `minVersion` 必须声明对应最低版本。
- **混用 `and` / `or` 一律加括号**；`%` 优先级高于 `+`，取模回绕写 `(x + 1) % N`。
- **建筑 / 炮塔不可被推动**用质量哨兵 `mass: 2147483647`。
- **`movementType` 取值**：`NONE` / `LAND` / `BUILDING` / `AIR` / `WATER` / `HOVER` / `OVER_CLIFF` / `OVER_CLIFF_WATER`。
- **贴花不能跑逻辑**：`frame` / `basePosition` 只能读 `self.*` / `memory.*`——先用 action 把结果写进内存，贴花再读。
- **高频 `autoTrigger` 有性能 / 联机同步代价**；能用事件（`autoTriggerOnEvent`）或路径点就别每周期轮询。
- **纳米建造（nano）只在本单位 `nanoRange` 内生效**；要让建筑对全图任意点建造 / 修理，靠 `spawnUnits` 在 `activeWaypointTarget` 处生成**隐形代理单位**（见指南 6.8）。
- **`mutatorX_*` 家族的 X 不限数字**：既可是 `mutator1`…`mutator7`，也可是单词前缀（`mutatorPlate` / `mutatorShield` / `mutatorbio`…）。
- **地面武器只能用 `areaDamage`**：官方原文 `directDamage` — "Does not work with `targetGround:true`"。打地面写 `directDamage` 就是个哑弹。
- **`fireTurretXAtGround` 会绕过 `canShoot`**：它的值是**炮塔引用**（如 `1` 指 `[turret_1]`），不是数量。
- **action 上的 `autoTriggerCheckRate` 覆盖 `[core]` 的**，不是叠加。
- **`@define` 是节内局部**，官方明说 "best outside of template"——**写 `.template` 时优先用 `@global`**；同名时 `@define` 盖掉 `@global`。
- **注释只能独占一行，行尾 `#` 不是注释。** 引擎逐行读，只在「整行 trim 后以 `#` 开头」时跳过。行尾的 `#` 会原样进入值。唯一例外：`"""` 块内部以 `#` 开头的行原样成为字符串内容。
- **`self.timeAlive()` 带括号**（v1.15 返回秒）。
- **`setUnitMemory` 多赋值是严格顺序执行**——后面的赋值能看到前面刚写入的新值。"先算再用"成立，这是手写状态机 / 数组扫描的前提。
- **`[hiddenAction_*]` 里不能写 `isVisible`**：引擎解析时直接抛异常，模组加载失败。
- **`alwaysSinglePress` 必须配另外两个键**：引擎判断是 `!canPlayerCancel && !allowMultipleInQueue && alwaysSinglePress` 三者同时成立。后两个默认 `true`，所以只写它无效。
- **`displayType: infoOnly` 只管外观，`isActive: false` 才是禁用**。纯文本、无效果的动作还要 `isVisible: true` 才会注册。
- **`setUnitStats` 的字段名是全小写**（`movespeed` / `shootdelaymultiplier` / `maxshield`），和 ini 键名（`moveSpeed` / `maxShield`）不是一套。改 `maxattackrange` 不会同步到炮塔缓存的射程。
- **`[global_resource_*]` 是解析期注册的**：哪个文件先解析，哪个文件才能用这个资源；排在后面的文件写 `biomass = 2` 会直接报 `Could not find resource type`。把定义放 `all-units.template` 由每个单位 `copyFrom`，就不依赖文件名顺序。
- **`overrideAndReplace: commandCenter`** 是总转换模组的入口做法：让你的建筑顶替原版指挥中心，`builder` 同理。引擎解析单位名时先查替换表，再匹配原版。
- **资源路径三种前缀**：`ROOT:` = 模组自己的目录；`CORE:` = 游戏 `assets/units/`；`SHARED:` = `assets/units/shared/`。**引用原版贴图不用复制文件**。

## 已用游戏二进制核实的结论

以下几条过去只能靠坊间说法，现已通过反汇编 `game-lib.jar` + 官方 CSV 交叉确认：

| 结论 | 证据 |
|------|------|
| **数组取长度用 `.size`** | 官方收录 `memory.NAME.size`（1.15，"包含空位"）；真实工程 `.size` 221 次 vs `.length()` 6 次 |
| **冷却键新名是 `addActionCooldownTime` / `addAllActionCooldownsTime`** | 新旧名都在二进制里注册，但唯一校验文案只提新名 |
| **`addActionCooldownApplyToActions` 必须配 `addActionCooldownTime`** | 那条校验文案就是硬约束 |
| **AI 优先级键官方拼写是 `noneInBaseExtraPriority` / `noneGlobalExtraPriority`** | `non*` 变体在二进制里也有，但代码表只认 `none*` |
| **`autoTriggerCooldownTime: NaNs` 不是哨兵值** | `NaN` 会污染浮点比较，属隐患写法。要"永不冷却"就写一个很大的秒数 |
| **`friendlyFire: only-ignoreEnemy` 是真值** | 该字符串存在于游戏二进制中 |
| **`killedAnyUnit` 事件发给击杀者，事件单位是死者** | `game/f.java:566` `am2.a(af.d, am3)`；同段 `++am2.cU` 就是 `self.kills`，**不区分友军 / 建筑** |

> **查不到就留空**：官方 CSV 不是全集——二进制里有 44 个键是"游戏认、中文表有、CSV 没有"。判定规则：**三份资料有其二即可用**，都查不到才留空。这条规则 MCP 的 `lookup_key` 已经内置（返回里的 `agreement` 字段会说明是几张表都有）。

## 参考文件

按需读取，不要整份塞进上下文——用 Grep 定位。

- **`references/铁锈战争模组开发Agent指南.md`** —— 完整开发指南（9 章 + 附录 A/B/C），本技能的主体。
  - 第 0 章：角色与 Agent 行为准则
  - 第 1 章：工程结构与继承体系（`mod-info.txt`、目录分工、`copyFrom`、残骸三件套）
  - 第 2 章：单位 / 建筑 / 武器定义结构（节名总表、`[core]`、`[graphics]`、`[decal_*]`、武器三件套）
  - 第 3 章：运行时脚本与逻辑（行动 / 触发 / 条件 / 内存 / 数组 / 单位引用 / 消息 / 性能护栏）
  - 第 4 章：非战斗 / UI 驱动模组（控制器 + 被驱动单位、网格、PRNG、按钮系统、分页 UI、**末节实战范式**）
  - 第 5 章：双语、UI 展示与模组元数据
  - 第 6 章：进阶技法示例库（概率变身、弧形血条、伤害统计、雷达盘、**6.8 隐形代理单位**）
  - 第 7 章：验证、调试与常见坑
  - 第 8 章：权威速查（版本门槛、API 站、维基、章节 A–U 对照）
  - **附录 C：分节键名速查**（按 `[section]` 归类，写某个节前先在这里定位）

- **`references/反编译发现_运行时语义.md`** —— 反编译 `game-lib.jar` 得到的**实现层面事实**：`setUnitMemory` 执行顺序、`isVisible` 在 hiddenAction 里的硬限制、`alwaysSinglePress` 三键条件。附复现命令与源码路径。

- **`references/反编译_字段对照表.md`** —— **混淆字段 → luke 键** 对照表（8 个类 / 581 个字段）。读反编译源码时对照它：`d2.v` 就是 `isVisible`。

- **`references/锁步联机与动态帧率补偿.md`** —— 联机 / 锁步 / 帧率补偿专项。30 帧基准与 `C = 30 / F_action`、补偿的四个副作用、`rnd()` 确定性、`autoTriggerCheckRate` 三档枚举。

- **`tools/game_loadtest.py`（在同仓库的 `tools/` 下，不随本技能分发）** —— **进游戏加载测试**（无窗口）。把模组复制进游戏的 `mods/units/`，用 `-nodisplay` 启动，抓日志里的加载错误后清理。**MCP 没有把它做成工具，只作为脚本随仓库提供**——本技能因此也不重复打包一份。
  ```bash
  python "<MCP仓库>/tools/game_loadtest.py" <模组目录> --game "D:/steam/steamapps/common/Rusted Warfare"
  ```

## 降级路径（MCP 没注册时）

MCP 是本技能的事实来源，但它不随技能分发。没装时：

1. 先确认 `~/.workbuddy-ai/mcp.json` 里有 `rusted-warfare`，且客户端已信任；有的话重启客户端就能用。
2. 实在没有，去 `https://github.com/GMBOXMOD/rw-modding-mcp` 拿一份——`tools/` 下的 `rw_lint.py`（静态检查）、`rw_explain.py`（动作图）、`game_loadtest.py`（真加载测试）、`rw_mcp_server.py`（MCP 本体）都能直接跑，键名资料在 `references/` 下。
3. 临时应急：在线代码表 `https://rwapicode.spldream.com/`（查分类与例子）＋ 维基「mod的坑」（进阶机制）。
4. **不要凭记忆补键名。** 查不到就留空并标注未验证，这比猜一个能过 linter 但游戏里静默失效的键要好。

## 推荐编辑器插件（用户用 VS Code 时主动提）

**RustedWarfare Mod Support**（作者 `xingwangzhe`）—— 市场 ID `xingwangzhe.RustedWarfareModSupport`，开源 `https://github.com/xingwangzhe/RustedWarfareModSupport`（AGPL-3.0）。提供节属性键补全（附说明 / 示例 / 版本 / 弃用）、属性值按类型补全、`@memory` 上下文补全、`mod-info.txt` 补全、悬停文档、十六进制颜色与图片预览、`Format INI File` 右键格式化、节折叠、ZIP/RWMOD 导出、14 语言界面。提醒先把 VS Code 更新到最新版，并把 `.template` 加进自定义后缀。

## 在线权威出口

- **代码 API 站**：`https://rwapicode.spldream.com/` —— 分类索引式代码表（`/src/Unit/core`、`/src/UnitNDT/index`、`/src/Map/all`、`/src/RW-Engine/quick-start`）。查分类说明与在线例子用此站；**查全量键名与值类型用 MCP `lookup_key`**。
- **维基「mod的坑」**：`https://rustedwarfare.org/wiki/mod的坑` —— 进阶机制索引。子页：`变量`、`自定义内存`、`数组`、`注解`、`复制`、`特殊值`、`单位引用`、`随机数`、`概率与随机偏移`、`多单位排序`。常用依赖插件：`rnd`、`clipboard`、`RW-Engine`、`PCMOD`。

## 查询优先级

1. **最近邻真实代码** —— 打开同目录 / 同类单位，照抄节名、键名、大小写、缩进再改。真实代码永远比文档新。
2. **MCP `lookup_key`** —— 判有无、判版本（返回里带 `versions` 与 `agreement`）。多个键一次传 `keys=[...]`。
3. **MCP `get_ref`** —— 事件 / 函数 / 枚举 / 内存类型 / 必须配对的键 / 硬限制。
4. **`references/` 里的指南与反编译笔记** —— 补"怎么用、和谁互斥、有什么坑"。
5. **维基 / 在线站** —— 进阶机制与社区补丁。
6. **仍不确定就留空**，写清"未验证"。

**永远不要靠猜补语法。**
