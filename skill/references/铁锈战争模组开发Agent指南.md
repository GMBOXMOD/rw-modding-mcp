# 铁锈战争模组开发 Agent 指南

> 面向 AI Agent 的《铁锈战争》(Rusted Warfare) 模组开发通用参考。涵盖工程结构与继承、单位/建筑/武器定义、luke 语运行时逻辑、非战斗/UI 模组技法、双语与元数据、进阶技法、验证与排坑，以及权威查询入口。
>
> 本指南力求通用：不绑定任何具体工程，所有结论都基于《铁锈战争》引擎与 luke 语的真实行为。

## 适用对象

- **写给谁**：在任意 RW 模组里动手的 AI Agent（以及模组作者本人）。
- **怎么读**：第 0 章定角色与准则；第 1–3 章是地基（结构/定义/逻辑），必读；第 4 章做非战斗/UI 模组时读；第 5 章碰文案/元数据时读；第 6 章要炫技时翻；第 7 章动手前后对照自检；第 8 章是遇到不确定语法时的权威出口；附录 C 是「按 `[section]` 归类」的全量键名索引，写某个节前先在这里定位分类。

## 一条总铁律

**先查，再写；查代码表 / 维基 / 真实文件，不要凭记忆。** 动手前先打开最近邻的真实节，照抄它的节名、键名、大小写、缩进，再改。luke 语节名/键名**区分大小写**，拼错不报错、只会静默失效。注释、他人指南乃至本指南都可能滞后于引擎版本——涉及名字、成员清单、继承关系、具体行为时，一律以真实代码的实际表现为准。

## 目录

-
-
-
-
-
-
-
-
-
- 附录 A：常用代码片段
- 附录 B：关键事实速查
- 附录 C：分节键名速查（按 `[section]` 归类）

## 0. 角色、协作理念与 Agent 行为准则

### 0.1 两种工作模式

Agent 协助 RW modding 有两种角色，按用户当下的需要切换：

- **协助者 / 老师**：帮用户理解 luke 语、查代码表、设计机制、排查错误。**优先给方向、给关键词，不代写**，让用户学会自己查、自己试。
- **建模者 / 执行者**：当用户**明确要求实现**时，直接写 / 改文件——但绝不凭空造结构：镜像最近邻的兄弟定义，复用共享模板，保持双语，提交前验证每一处引用。

判断用哪种：用户在**学习 / 设计 / 排错** → 老师模式，给思路与查法；用户**明确说「帮我加 / 建 / 改某单位」** → 建模者模式，按第 1–2 章的继承约定落地，并按第 7 章自检。拿不准就先问「主语和宾语」——谁对谁做什么。

### 0.2 教学与提问（老师模式）

1. **先问清主宾**：谁对谁做什么？拒绝模糊需求。
2. **要原码、报错、截图**：不接受「它坏了」式描述。
3. **给关键词，不给整段代码**：路铺好，让用户自己走——引导去代码表、维基（第 8 章）。
4. **分型对待**：愿意学的耐心指路；伸手党直接给答案但不深入；「不查不试」者可严厉指出；模糊需求要求澄清。

### 0.3 Agent 行为准则

1. **不猜。** 不确定就查代码表 / 真实文件，或让用户查。宁可说「不知道」，也不给错误信息。
2. **不臆造结构。** 建模一律镜像最近邻兄弟 + 复用共享模板。
3. **只做静态工作。** Agent 跑不了游戏——改完要说清「改了什么、静态验证了什么、还需进游戏实测什么」。
4. **保持双语。** 任何玩家可见串都中英成对（方向见第 5 章）。
5. **不惯着「不查不试」，但对事不对人。** 批评行为，不攻击人格；尊重用户的最终选择与边界。
6. **授人以渔。** 让用户学会自己解决问题。
7. **改动日志要诚实。** 不要用占位内容更新版本号或更新日志；只在改动真实、面向玩家时更新，若有意跳过要说明。

### 0.4 luke 语是什么（30 秒速写）

《铁锈战争》用一种基于「节 `[section]` + `键: 值`」的配置语言（社区称 **luke 语**）定义一切游戏对象。它**没有函数、没有真正的 `if-else`（1.16 前）、没有 `for`**：所有「逻辑」都由 `[action_*]` / `[hiddenAction_*]` 节 + 触发链 + 内存 + 消息 + 贴花拼出来。核心概念——行动、自动触发、事件、内存(`@memory`)、资源(`self.resource`)、标签(`tags`)、单位引用(`self` / `nearestUnit` / …)、消息(`sendMessage*` / `newMessage`)、贴花(`[decal_*]`)——在后续各章都有真实代码示例。

### 0.5 群里提问的艺术（教用户如何提问）

RW modding 高度依赖社区互助。当用户要去群里 / 论坛求助时，Agent 应按下面这套礼仪引导他们——会提问的人才问得到答案。

**提问之前，你要做什么？**

1. **先查最新代码表。** 以群里 / 社区**最新版**代码表为准，查到符合预期的代码；别拿过时资料或凭记忆开问。
2. **先自己试。** 确认自己真的尝试过解决，而不是一遇到问题就伸手。
3. **把问题梳理清楚、备齐材料。** 提供能复现问题的视频、截图、相关文件；需要时附上**报错信息**与**已经试过的方法**。不要擅自翻译 / 转述原始信息，也不要以「不能外传」为由拒绝提供——信息不全，神仙也难帮。
4. **摆正心态，接受可能没人回。** 提前做好无人回应的准备，不因没人理会就恼羞成怒。

**别人帮你时，你要做什么？**

1. **态度别太轻浮。** 认真对待愿意花时间帮你的人。
2. **积极提供材料。** 对方要什么就给什么，别挤牙膏。
3. **别半途消失。** 问了就跟进到底，不要抛出问题后人间蒸发。
4. **先配合再质疑。** 对方给的解法即便不符合你的认知，也先照着试，别当场否定——很多坑只有试了才知道。

**问题解决后，你要做什么？**

- **记得道谢。** 一句真诚的感谢，是对帮助者最基本的尊重，也让你下一次求助更顺。

> Agent 提示：用户带着模糊、未经尝试、无材料的问题来时，按本节先引导他补齐这几步（呼应 0.2「先问主宾、要原码报错截图」），而不是直接代劳——这既是礼仪，也是让问题真正可解的前提。

### 0.6 推荐工具链：VS Code + 铁锈战争插件

**用户用 VS Code 写 luke 语时，主动推荐装这个插件：**

> **RustedWarfare Mod Support** —— 作者 `xingwangzhe`
>
> 安装：VS Code 扩展市场搜 `RustedWarfareModSupport`，或官网
>
> `https://marketplace.visualstudio.com/items?itemName=xingwangzhe.RustedWarfareModSupport`
>
> 开源：`https://github.com/xingwangzhe/RustedWarfareModSupport`（AGPL-3.0）
>
> 交流群：GMBOX 的 mod 群 `1006360455`

它把"查代码表"这件事搬进了编辑器，能显著减少拼写错误，正好补上 luke 语"拼错不报错、只静默失效"这个最大痛点：

- **智能补全**：绝大部分节的属性键自动补全（附说明 / 示例 / 版本 / 弃用提示）；属性值按类型补全（布尔、逻辑布尔表达式、单位生成、列表 / 枚举）；`@memory` 变量的定义与使用上下文感知补全；`mod-info.txt` 自动识别并补全。
- **文档提示**：属性键悬停显示说明 / 示例 / 版本 / 弃用标记；逻辑布尔函数与 `self.` 方法的悬停文档。
- **颜色 / 图片预览**：`#AARRGGBB` / `#RRGGBB` 十六进制颜色在编辑器内着色并可悬停预览；`image` 路径的图片悬停预览（支持相对路径与 `ROOT:` 前缀）。
- **代码格式化**：右键 `Format INI File`，对齐键值、规范化分隔符与括号空格，**保留注释 / 空行 / 节结构 / 键顺序**（保守格式化，不乱动你的排版）。
- **节折叠 / 大纲**：快速定位大型单位文件里的各个节。
- **Mod 导出**：一键导出 ZIP / RWMOD 包。
- **多语言界面**：内置 14 种语言，跟随 VS Code 显示语言。
- **侧边栏**：管理自定义文件后缀（含如 `.template` 等）。

> 提示：安装前先把 VS Code 更新到最新版，避免插件兼容性过期。该插件的参考资料里也用到了 **NDT 代码表**、**Google 代码表** 与 **GMBOX 提供的部分枚举属性**——与本章第 8 章的两张权威出口同源，可交叉印证。

**用法建议**：把插件补全当"第一道防线"，但它补全的键仍以代码表为准；Agent 自己查键名走 MCP `lookup_key`，查不到再看第 8 章的在线站与维基。写 `.template` 这类非默认后缀前，先在插件侧边栏把它加进自定义后缀，补全才会生效。

## 1. 工程结构与继承体系

> 铁律先行：下文每条结论都对应可在真实文件里核对的事实。你在任何 RW 模组里动手前，务必先用 `Glob`/`Grep`/`Read` 打开目标文件再下结论，绝不臆造节名/键名/函数名——尤其注意文件头注释与随附文档里的路径示例可能已过时（见本章末「坑位清单」）。

### 模组是什么：mod-info.txt 作清单

一个 RW 模组以根目录下的 `mod-info.txt` 作为清单。多个模组可以并排放在同一个收藏目录里，彼此独立、互不依赖——每个模组各写各的 `mod-info.txt`，`copyFrom` 里的 `ROOT:` 前缀各自解析到**本模组的根目录**（下文详述）。

`mod-info.txt` 用 `[mod]` 节声明标题/描述/缩略图/最低版本；需要背景音乐时可再加一个 `[music]` 节：

```ini
[mod]
title: My Mod v0.1
description: My mod description
description_zh: 我的模组描述
thumbnail: mythumb.png
minVersion: v1.15

[music]
sourceFolder: sounds/music
whenUsingUnitsFromThisMod_playExclusively: true
```

不要假设两个模组的清单结构一致——`[music]` 节、双语描述、缩略图各模组可有可无。核对清单时的坑：`thumbnail` 指向的图标文件可能是从别处复制清单时残留的失效占位（磁盘上并不存在）。编写/核对清单时，务必用 `Glob` 确认 `thumbnail`（以及任何资源引用）指向的文件真实存在。

### 推荐的目录分工（结构化 RTS 模组）

下表是一种可行的结构化布局，核心价值在于「静态数据 / 共享行为 / 活体单位 / 残骸」各自分家：

| 目录                                       | 职责                                             |
| ---------------------------------------- | ---------------------------------------------- |
| `units/`                                 | 单位【静态母版】`.template`（名称/文案/造价/血量/质量/半径/贴花等静态属性） |
| `scripts/`                               | 共享【行为】骨架 `.template`（建造者、移动、隐身等可复用行为）          |
| `factory/`（可按族再分子目录）                     | 各单位的活体 `.ini`                                  |
| `wreak/`（残骸）                             | 残骸单位 `.ini` + 残骸专用 `all-units.template`        |
| `defense/ economy/ intel/ commanders/` 等 | 按功能分组的建筑/单位                                    |
| `projectile/ subunit/ superweapon/`      | 投射物/子单位/超级武器（可各自带一份嵌套 `all-units.template`）    |
| `icons/ images/ sounds/`                 | 资产                                             |

根目录放一份自动套用的 `all-units.template`（见下）。

### 继承优先级：最后写入者获胜

某个键的最终值按下列顺序逐层覆盖，**后者覆盖前者**：

| 优先级   | 来自哪一层                                                 |
| ----- | ----------------------------------------------------- |
| 1（最低） | 引擎默认值                                                 |
| 2     | `all-units.template`（凭特殊文件名自动套用到每个单位）                 |
| 3     | `copyFrom: ROOT:x.template` 列表（按列出顺序依次套用，逗号分隔，靠后覆盖靠前） |
| 4（最高） | 单位自身内联键（活体 `.ini` 里直接写的键）                             |

**节是按键逐个合并、不整体替换。** 当子层重声明 `[core]`/`[decal_img]`/`[movement]` 等节时，只覆盖/新增它列出的键，其余键仍从父层继承。

示例——「最后写入者获胜」：基础母版设一个 `@global`，变体活体内联覆写成更大值，最终取后者：

```ini
# 基础静态母版
@global my_range = 1000
```

```ini
# 变体活体 .ini
@global my_range = 3000
@global my_power = 3
```

示例——「节按键合并」：同一个 `[decal_img]` 最终由两处拼起来——`image/dirOffset` 来自静态母版、`color` 来自残骸基础层，合并成同一个 decal：

```ini
# 静态母版：只有 image/dirOffset/teamColors，无 color
[decal_img]
image: ROOT:path/to/sprite.png
dirOffset: 90
teamColors: true
```

```ini
# 残骸基础层：只补 color
[decal_img]
color: #555555
teamColors: true
```

### all-units.template：按文件名自动套用的基础层

根目录的 `all-units.template` 凭特殊文件名自动套用为每个单位的基础层（无需任何 `copyFrom`）。常见做法是用极小的默认值 + 一整套通用机制奠基：

```ini
mass: 1000
radius: 10
maxHp: 100
metalCost: 0
fogOfWarSightRange: 5
[attack]
canAttack: false
[movement]
movementType: NONE
```

除基础数值外，它还适合集中承载全模组通用的机制：各类 buff 的资源与逻辑（`[resource_*]`）、死亡爆炸（如 `[projectile_explode_onDeath]`）、残骸转换（如 `[hiddenAction_wreak]`）、以及可被各处 `@copyFromSection` 复用的通用动作骨架 `[template_]`。buff 之类用户可见名建议中英成对：

```ini
displayName: My Buff
displayName_zh: 我的增益
```

**注意**：「凭特殊文件名自动套用 / 就近目录遮蔽」属于引擎行为，文件本身无法证实叠加/遮蔽的精确规则——涉及叠加顺序时需进游戏核实。

### copyFrom：显式继承

`copyFrom:` 是在 `[core]` 里写的显式继承指令，支持逗号分隔多个，**按列出顺序依次套用，靠后覆盖靠前**：

```ini
copyFrom: ROOT:scripts/const.template, ROOT:scripts/cloak.template, ROOT:units/myunit.template
```

两种写法：

- **`ROOT:` 前缀**——从本模组根解析，最常用。
- **不带前缀的相对路径**——按「被引用文件自身所在目录」解析，可指向同目录的 `.txt` 片段，也可指向同目录的另一个 `.ini`：

```ini
# 相对的 .txt 片段（与本文件同目录）
copyFrom: my_list.txt, ROOT:units/myunit.template
```

```ini
# 相对的另一个 .ini（与本文件同目录），用于复用其逻辑
copyFrom: mybase.ini, ROOT:units/myvariant.template
```

### 节内继承：@copyFromSection 与 @copyFrom_skipThisSection

- `@copyFromSection: otherSection` 把另一节的键拉进本节（节内继承）。例如派生资源可从另一资源拷贝字段：

```ini
[global_resource_metalCost]
@copyFromSection: global_resource_metal
```

也可用它派生贴花——如 `[decal_shadow]` 先 `@copyFromSection: decal_img` 再改图层/颜色/透明/偏移。

- `@copyFrom_skipThisSection: true` 丢弃从父层继承来的整节。例如某单位要主动跳过基类里的某个 `[hiddenAction_*]`：

```ini
[hiddenAction_freeFactory]
@copyFrom_skipThisSection: true
```

该指令用于「我继承了基类，但这一节我不要」的场景。

### `IGNORE`：万能占位值（必须全大写）

`IGNORE` 是 luke 语的一个**特殊值**，**任何键都能填**，填了「什么都不发生」，常用于**阻断从父层继承来的某个键**——只删想删的那一行，不用整节跳过：

```ini
[hiddenAction_ok]
autoTrigger: IGNORE
requireConditional: IGNORE
spawnUnits: IGNORE
```

若整节都不要，用上文的 `@copyFrom_skipThisSection`；若只要废掉其中几个键，就在活体里把它们逐个改写成 `IGNORE`（比 `@copyFrom_skipThisSection` 更精细）。

### 变量：`@define` / `@global` 与引用

| 写法               | 作用域 | 说明                                        |
| ---------------- | --- | ----------------------------------------- |
| `@define X: 值`   | 本节内 | 节内局部变量，优先级高于全局                            |
| `@global X: 值`   | 全文件 | 全文件可见，本文件内所有节都能引用                         |
| `${X}`           | —   | 引用上两者的值（载入期展开一次）                          |
| `${section.key}` | —   | 引用**另一节**某键的值（如 `${core.price * 2 + 10}`） |

约束（写错静默失效，不报错）：

- **禁止变量套娃引用**：`@define a: ${b}` 非法。
- 变量名禁止含 `= } $ . { - + : (`，且**不能以数字开头**。
- `${...}` 与 `${section.key}` 是**唯二支持 `^` 幂运算符的区域**；`sqrt` / `cos` / `sin` 也只在 `${}` 里可用。
- 变量引用有**引用上限**，别做超深链式引用。

### 特殊内置单位（`[comment]` 里列出的、可直接 `spawnUnits` 的引擎单位）

引擎内置一批「虚拟单位」，不需自己定义，直接当普通单位名用：

| 名称               | 作用                              | 用法示例                                                                     |
| ---------------- | ------------------------------- | ------------------------------------------------------------------------ |
| `damagingBorder` | 生成圆形安全区，区域外单位持续掉血直到死亡           | `spawnUnits:damagingBorder(techLevel=4,offsetRandomX=1,offsetRandomY=1)` |
| `zonemarker`     | 指示伤害边界移动/缩放目标（`techLevel` 控大小）  | `spawnUnits:zonemarker(techLevel=2,...)`                                 |
| `setRally`       | 作 `[canBuild]` 项：设置新单位集结点       | `canBuild_1_name:setRally`                                               |
| `reclaim`        | 作 `[canBuild]` 项：回收建筑并返还 75% 资金 | `canBuild_1_name:reclaim`                                                |
| `repair`         | 作 `[canBuild]` 项：主动维修建筑         | `canBuild_1_name:repair`                                                 |

### 资产前缀

| 前缀        | 含义       | 示例                                    |
| --------- | -------- | ------------------------------------- |
| `ROOT:`   | 本模组根     | `iconImage: ROOT:icons/myicon.png`    |
| `SHARED:` | 原版共享基础资产 | `image: SHARED:blank.png`             |
| `CORE:`   | 原版基础游戏贴图 | `image: CORE:path/to/core_sprite.png` |
| `IGNORE`  | 刻意置空     | `iconImage: IGNORE`                   |


写任何 `ROOT:` 路径前，先 `Glob` 确认磁盘上真的存在该文件。

### 核心模式：静态母版 / 活体 .ini / 残骸三件套

结构化模组常把一个单位拆成三份，各司其职：

**① 静态母版 `units/<name>.template`**——存名称/文案/造价/数值/贴花，活体与残骸共用它：

```ini
name: ${core.altNames}
altNames: myunit
displayText: My Unit
displayText_zh: 我的单位
maxHp: 120
mass: 500
metalCost: 40
radius: 10
```

**② 活体 `.ini`**——`copyFrom` 行为模板 + 静态母版，再补动态键（视野/attack/turret/projectile/movement）：

```ini
copyFrom: ROOT:scripts/veh.template, ROOT:units/myunit.template, ROOT:scripts/slow.template
fogOfWarSightRange: 26
[attack]
canAttack: true
maxAttackRange: 120
```

**③ 残骸 `wreak/w_<name>.ini`**——只 `copyFrom` 该单位静态母版 + 改名，不显式继承残骸基础层（靠文件名自动生效）：

```ini
[core]
copyFrom: ROOT:units/myunit.template
name: w_${core.altNames}
```

`scripts/*.template` 是共享行为骨架，例如一个建造者骨架：

```ini
isBuilder: true
canRepairBuildings: true
canRepairUnits: true
nanoRange: 120
canReclaimResources: true
```

`[template_]` 作为通用动作骨架，被各 `[action_*]` 用 `@copyFromSection` 复用：

```ini
[template_]
alwaysSinglePress: true
allowMultipleInQueue: false
canPlayerCancel: false
buildSpeed: 0
pos: 0
isVisible: true
```

```ini
[action_xxx]
@copyFromSection: template_
```

### 分层与分级：基座母版 + 变体覆写

**分层静态母版链**——变体母版先 `copyFrom` 共享静态基座，再按需覆写数值：

```ini
# 共享静态基座母版
metalCost: 700
maxHp: 4000
```

```ini
# 变体母版：copyFrom 基座后只覆写差异
copyFrom: ROOT:units/mybase.template
metalCost: 1200
maxHp: 2000
```

**分级变体**——进阶变体的静态母版 `copyFrom` 基础母版；活体 `.ini` 则（用相对路径）`copyFrom` 基础活体 `.ini` 以复用其逻辑（如探测/开关机），只覆写更大的范围/耗电等差异：

```ini
# 进阶变体静态母版
copyFrom: ROOT:units/mybase.template
altNames: myvariant
displayText: My Advanced Unit
displayText_zh: 我的进阶单位
```

```ini
# 进阶变体活体 .ini：相对 copyFrom 基础活体，复用其隐藏动作
copyFrom: mybase.ini, ROOT:units/myvariant.template
[hiddenAction_detect]
takeResources_maxUnits: 5000
```

### 残骸（wreak）体系

残骸生成可完全集中在根 `all-units.template`，无需每个单位单独接线——用一个在 `tookDamage` 时触发、血量归零时把自己转换成残骸单位的隐藏动作：

```ini
[hiddenAction_wreak]
autoTriggerOnEvent: tookDamage
autoTrigger: true
requireConditional: if self.hp <= 0

setUnitStats: maxHp = self.maxHp * 2, hp += self.maxHp
switchToNeutralTeam: true

convertTo: w_${core.altNames}
convertTo_keepCurrentFields: maxHp

alsoTriggerAction: deleteWreakIfNotCompleted, explode_onDeath
```

`wreak/` 下另放一份残骸专用的 `all-units.template`，凭特殊文件名 + 目录范围把该目录内的残骸统一设为中立/惰性/暗色占位：

```ini
tags: wreak
createOnAggressiveTeam: true
stayNeutral: true

[decal_img]
color: #555555
teamColors: true
```

三个必须记牢的残骸约束：

- **`convertTo: w_${core.altNames}` 依赖活体真的在静态母版里设过 `altNames`。** 残骸只覆写 `name`，`altNames` 仍从母版继承（母版里写 `name: ${core.altNames}` / `altNames: myunit`）。没设 `altNames` → 转换断裂。
- **母版 `displayDescription` 插值用到的 `@global` 必须声明在母版链中。** 因为残骸只 `copyFrom` 静态母版、拿不到活体 `.ini`。把插值与 `@global` 声明放在同一母版文件里：

```ini
displayDescription: Detects units within range.\nRange is ${my_range}, consumes ${my_power} power per second.
@global my_range = 1000
@global my_power = 0.8
```

若 `@global` 只写在活体 `.ini`，残骸加载期解析 `${...}` 会失败。

- **只有被残骸基础层预置了 `#555555` 的那几个节名才会自动染暗**（见坑位清单）。

### 建造菜单集中管理

工厂建造菜单可集中在一个共享行为模板里：已解锁的放一个 `[canBuild_N]`，未完成的锁在另一个 `[canBuild_N]`：

```ini
[canBuild_5]
# 已解锁
name: factorya, factoryb, factoryc

[canBuild_6]
# 未完成
name: factoryd, factorye
isLocked: true
isLockedMessage: Coming soon
isLockedMessage_zh: 敬请期待
```

新增可造项时，把它的 `name` 加到对应列表即可。

**「免费首厂」之类全队一次性机制用全局标签实现**——用 `globalTeamTags` 判断、`addGlobalTeamTags` 置位：

```ini
[hiddenAction_freeFactory]
autoTriggerOnEvent: created
requireConditional: if not self.globalTeamTags(includes="free_factory")

setBuilt: 1

addGlobalTeamTags: free_factory
```

注意：标签是全队共享的，所以这类机制对全队**第一座**生效一次（可再叠加 `customTarget1 + globalTeamTags` 组合做二级条件）；某单位想绕过它时用 `@copyFrom_skipThisSection` 主动跳过该节。

### 非战斗 UI/逻辑模组的结构

纯 UI/逻辑模组几乎全是无实体对象——空贴图、不可攻击、不能移动、隐藏血条/选择框，用一个 `[template_*]` 作动作骨架：

```ini
[graphics]
image: SHARED:blank.png
showSelectionIndicator: false
showHealthBar: false

[attack]
canAttack: false

[movement]
movementType: NONE

[template_m]
alwaysSinglePress: true
```

**嵌套 all-units.template 不会自动继承上层**：子目录版本必须显式 `copyFrom` 根版本才能拿到基础层：

```ini
[core]
copyFrom: ROOT:all-units.template, ROOT:mysubdir/my_list.template
```

（对照：残骸目录的 `all-units.template` 可以反其道而行——不 `copyFrom` 根版本，而自成一套残骸基础层。`projectile/`、`subunit/` 等子目录也可各带一份嵌套 `all-units.template`。）

### 坑位清单（Pitfalls）

1. **随附文档/文件头注释里的路径示例可能已过时。** 文档可能指向磁盘上并不存在的旧文件名，部分文件头注释也会引用这些旧名。方法论/继承模型通常可信，但具体路径示例须先 `Glob`/`Grep` 核实再用。
2. **别信注释，以磁盘真实指令为准。** 文件头注释常写「copyFrom 某母版」，但真正生效的是 `[core]` 里那行真实的 `copyFrom`，两者可能矛盾。用 `grep` 排查时若只看 `head -1` 命中的注释行会被带偏——永远以真实指令行为准。
3. **残骸自动染暗只认特定节名。** 残骸基础层通常只对 `[decal_img]`、`[decal_turret]`、`[decal_img2]`、`[decal_img3]` 预置 `color: #555555`。若本体贴花用的是不在该集合里的编号节（如 `[decal_img1]`），该残骸本体很可能不会自动变暗。「只要是编号 decal 就会被染暗」并不准确——具体视觉需进游戏确认，且本体贴花建议用非编号的 `[decal_img]`。
4. **「目录范围自动套用 / 就近遮蔽」是引擎行为，文件证实不了叠加规则。** 残骸靠目录内 `all-units.template` 自动生效、嵌套模板的遮蔽/叠加顺序，都需进游戏核实，不要仅凭文件推断最终叠加结果。
5. **清单核对：`thumbnail` 等资源引用可能是失效占位。** 复制清单时容易残留指向不存在文件的引用，提交前用 `Glob` 校验每一处资源路径真实存在。

## 2. 单位 / 建筑 / 武器定义结构

《铁锈战争》(Rusted Warfare) 模组用一种「节 `[section]` + `键: 值`」的配置语言（社区称 "luke 语"）定义一切游戏对象。一个单位 / 建筑 / 武器就是一个由多个节拼装而成的文本定义。动手改任何定义前，先打开真实文件（Read / Grep / Glob）核实已有的节名与键名，**绝不凭记忆臆造节名或键名**。

### 节名总表（先认清有哪些节）

一份单位定义可用的节就下面这些。**每节的可用键极多（核心节就有 100+ 个），键名只在这里给出分类线索，写具体键前务必查代码表**（见第 8 章）：

| 节                                       | 作用                                                                                                           | 键数规模 |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ---- |
| `[core]`                                | 身份 / 数值 / UI / 运输 / 建造 / 死亡 / 动作等，事实上的主节（代码表再细分为通用、单位统计、UI 图形、仅构建、杂项、运输、资源节点、资源收集器、建筑工厂、死亡、动作、不建议使用共 12 个子类） | 100+ |
| `[canBuild_NAME]`                       | 建造菜单项（该单位能造什么 / 显示什么按钮）                                                                                      | 17   |
| `[graphics]`                            | 整体渲染（主图、炮塔图、阴影、行驶特效、动画帧）                                                                                     | 30+  |
| `[attack]`                              | 攻击能力（射程、可攻击类型、多炮塔、近战、散射）                                                                                     | 20+  |
| `[turret_NAME]`                         | 单个炮塔（关联弹丸、计时、定位控制、图形效果）                                                                                      | 40+  |
| `[projectile_NAME]`                     | 单个弹丸（伤害、运动、图形效果）                                                                                             | 60+  |
| `[movement]`                            | 移动（类型、速度、转向、高度）                                                                                              | 22   |
| `[ai]`                                  | AI 行为（建造优先级、数量推荐、用途标签）                                                                                       | 23   |
| `[leg_#]` / `[arm_#]`                   | 腿脚 / 胳膊（多足、机械臂）                                                                                              | 40+  |
| `[attachment_NAME]`                     | 附属子单位（挂载的独立单位）                                                                                               | 37   |
| `[effect_NAME]`                         | 特效（时间、移动、图形、动画）                                                                                              | 60+  |
| `[animation_NAME]`                      | 动画（关键帧、多向动画）                                                                                                 | 20+  |
| `[action_NAME]` / `[hiddenAction_NAME]` | 行动 / 隐藏行动（luke 逻辑的主体）                                                                                        | 300+ |
| `[placementRule_NAME]`                  | 放置规则（放置条件 / 放置代价）                                                                                            | 24   |
| `[global_resource_NAME]`                | 全局资源（跨单位共享的计数器 / HUD 条）                                                                                      | 27   |
| `[resource_NAME]`                       | 局部资源（每单位实例的身体护盾 / 能量 / buff 条）                                                                               | 24   |
| `[decal_NAME]`                          | 贴花（分层贴图、血条、进度条、线条）                                                                                           | 54   |
| `[template_NAME]`                       | 模板（纯复用容器，本身无效，靠 `copyFrom` 引用）                                                                               | —    |
| `[comment_NAME]`                        | 注释（无效果，放元信息）                                                                                                 | —    |
| `[mod]`                                 | **仅在 `mod-info.txt`**：模组元数据（title / description / tags / minVersion / thumbnail）                             | 5    |
| `[music]`                               | **仅在 `mod-info.txt`**：音频（sourceFolder 等）                                                                     | 3    |

> **命名易错点**：`[turret_NAME]` 官方建议填 1–31 的数字，但**实际可填非数字的自定义名**（如 `[turret_主炮]`），只要 `projectile:` 指向的节名与之对应即可。`[leg_#]` / `[arm_#]` 里的 `#` 才是**必须**为编号。

### 文件分工：静态母版 `.template` × 活体 `.ini`

一个常见且好用的约定是把每个单位拆成两层，再用 `copyFrom` 拼起来：

- **静态母版 `*.template`**：身份、造价、血量、质量、半径、贴图。活体与残骸（wreak）共用，保证两者静态数据永不漂移。
- **活体 `.ini`**：攻击、炮塔、移动、视野等动态行为。

```ini
# 活体：基础数值/贴图见 units/myunit.template；行为基类见 base.template。此文件仅留攻击/炮塔/过热/能量逻辑。
[core]
copyFrom: ROOT:scripts/base.template, ROOT:units/myunit.template
```

这不是引擎强制，而是便于维护的分层策略：静态数据只写一份，活体与残骸共享，不会漂移。

### `copyFrom` 多级继承

`copyFrom` 接受逗号分隔的多个来源，**按书写顺序依次应用，后者覆盖前者**：

```ini
copyFrom: ROOT:scripts/family.template, ROOT:units/myunit.template, ROOT:scripts/mixin.template
```

三类来源各司其职：家族行为模板（`scripts/family.template`）→ 单位静态母版（`units/myunit.template`）→ 功能混入模板（`scripts/mixin.template`）。来源既可用 `ROOT:` 等路径前缀，也可用**相对的 sibling 文件名**（同目录兄弟文件）：

```ini
copyFrom: sibling.ini, ROOT:units/myunit.template
```

来源很长时可用三引号包裹换行书写：

```ini
copyFrom: """
ROOT:scripts/base.template,
ROOT:scripts/moduledefs.template,
ROOT:scripts/list.template,
ROOT:units/myunit.template
"""
```

### 资源路径前缀

引用图片 / 音效 / 模板时路径前缀有几种，**写新定义时必须分清**：

| 前缀        | 含义                         |
| --------- | -------------------------- |
| `ROOT:`   | 本模组根目录                     |
| `SHARED:` | 引擎共享资源                     |
| `CORE:`   | 原版游戏基础资源                   |
| `IGNORE:` | 占位 / 忽略，表示「无资源」（用于显式留空某张图） |


例如 `image: ROOT:path/to/sprite.png`、`image: SHARED:blank.png`、`image: CORE:extractor/extractor_back.png`。无前缀的相对路径（如 `res/ui/icon.png`）须在磁盘上真实存在。

### `[core]` 节：身份与基础数值

#### 名称与双语文案

静态母版常用 `name: ${core.altNames}` 自引用，真实标识靠 `altNames`。用户可见文案成对给出中英文（基键为英文，`_zh` 后缀为中文，`\n` 为换行）。

```ini
name: ${core.altNames}
altNames: myunit

displayText: My Unit
displayText_zh: 我的单位

displayDescription: My scout vehicle
displayDescription_zh: 单位说明文案。\n支持用 \n 换行……
```

> 为什么母版都用 `name: ${core.altNames}`：这是「残骸转换」机制的锚点。活体死亡时由一个 `[hiddenAction_wreak]` 触发 `convertTo: w_${core.altNames}`（配 `autoTriggerOnEvent: tookDamage` + `requireConditional: if self.hp <= 0`），把活体转成对应的 `w_<altNames>` 残骸单位。母版名字统一，残骸才能对上号。

#### 基础数值

```ini
maxHp: 120
mass: 500
metalCost: 40
radius: 10
```

通常由一个全局母版（如 `all-units.template`）为全体单位设基线，并由 `metalCost` 推导造价 / 回收 / 建造时间：

```ini
mass: 1000
price: metal = ${core.metalCost}, power = ${core.metalCost}
radius: 10
maxHp: 100
reclaimPrice: metal = ${int(core.metalCost * 0.7)}
buildSpeed: ${core.metalCost}s
```

**`mass` 哨兵值**：建筑 / 炮塔用 `mass: 2147483647`（int 最大值）表示「不可被推动」。

```ini
maxHp: 1500
mass: 2147483647
```

#### 视野

`fogOfWarSightRange` 一般留在活体（残骸视野应为 0）：

```ini
fogOfWarSightRange: 5
fogOfWarSightRangeWhileNotBuilt: 0
```

炮塔母版还可把视野由攻击射程推导：

```ini
fogOfWarSightRange: ${int((attack.maxAttackRange * 1.1 + 48) / 20)}
```

#### 可写在 `[core]` 内的声明

- `@memory <名>: <类型>` 声明每单位实例的可变记忆（类型 `boolean` / `float` / `number` / `unit` / `string` 及其数组形式；**优先用 `@memory` 而非 `defineUnitMemory`**，因为后者可被继承覆盖而失效）
- `@global <名> = <值>` / `@global <名>: <值>` 声明定义级常量 / 表达式
- `@define <名>:<值>` 参数化（常用于贴花批量展开）

```ini
@memory stopFiring_timer: float
@global power_usage: 0.5
autoTriggerCooldownTime: 1
```

把探测范围、耗电之类的量声明为 `@global` 放在母版，可供文案（`displayDescription` 的 `${...}` 插值）与逻辑共用：

```ini
@global my_range = 1000
@global my_power = 0.8
```

### 建筑特有键

```ini
isBuilding: true
footprint: 0,0,1,1
constructionFootprint: 0,0,1,1
buildingToFootprintOffsetX: 20
buildingToFootprintOffsetY: 20
```

大尺寸建筑（如工厂）给出更大的 footprint 基线：

```ini
metalCost: 700
maxHp: 4000
mass: 2147483647
radius: 25
footprint: -1,-1,1,1
constructionFootprint: -1,-1,1,2
buildingToFootprintOffsetY: 0
isBuilding: true
```

> **坑**：`buildingToFootprintOffsetX` 与 `buildingToFootprintOffsetY` 是两个独立键，二者都真实存在，但不要以为每个建筑母版都同时带 X 和 Y——有的只写了 Y。改偏移前先确认目标文件里到底有哪个键。

只能建在资源池上的建筑（如资源提取器）用 `placeOnlyOnResPool`：

```ini
placeOnlyOnResPool: true
```

### `tags`：单位分类

`tags` 决定单位归属哪一类，供 AI、可建造列表、放置规则、攻击目标筛选引用。来源有两处：

- **家族行为模板**统一打标，如家族模板里的 `tags: veh`
- **经济 / 指挥官等活体**在自己 `.ini` 里打标，例如发电打 `tags: gen`、采矿打 `tags: mex`、指挥官打 `tags: comm`

> **坑**：某些 tag 必须留在活体 `.ini`，不能进母版。典型是 `tags: comm`：若写进母版，残骸会继承该 tag，被「禁止回收指挥官」之类的通用逻辑误挡。规律是——**按残骸是否应继承该标签来决定它写在母版还是活体**。

一些建筑 / 单位还会用到 `techLevel`、`borrowResourcesWhileAlive` 等键：

```ini
tags: comm
borrowResourcesWhileAlive: metal_uplimit= -500, power_uplimit = -500
techLevel: 2
```

### 经济建筑

发电建筑用 `generation_resources` 产出，`generation_active` 做条件开关：

```ini
generation_resources: power = 2
generation_active: if not memory.inactivate
```

蓄能型（如需要充能才能开火的能量炮塔）用 `energyMax` / `energyRegen`：

```ini
energyMax: 1
energyRegen: 0
```

本体贴图可做序列帧动画：母版用 `total_frames` 定义帧数，活体用 `frame` 表达式驱动（可用 `self.timeAlive`、`memory.*` 等驱动，按 `% total_frames` 取模循环）：

```ini
[decal_img]
frame: int(self.timeAlive * 3) % 3
```

### 建造者与可建造菜单

建造能力：

```ini
isBuilder: true
canRepairBuildings: true
canRepairUnits: true
nanoRange: 120
canReclaimResources: true
```

AI 侧用 `[ai] useAsBuilder: true` 标记建造者：

```ini
[ai]
useAsBuilder: true
```

可生产单位用 `[canBuild_N]` 的 `name:` 逗号列表声明：

```ini
[canBuild_1]
name: myunit1, myunit2, myunit3
```

建造者可用分页菜单：`isVisible` 按记忆切页、`pos` 排位、`forceNano` 强制纳米建造，还有 `reclaim` 这种特殊条目：

```ini
[canBuild_1]
name: reclaim
pos: -1
[canBuild_2]
name: mygen, mymex, mystorage
isVisible: if memory.menu_page == 1
pos: 1
forceNano: true
```

未完成 / 未解锁的条目用 `isLocked` + 双语锁定提示：

```ini
[canBuild_6]
name: myunit1, myunit2
isLocked: true
isLockedMessage: Coming soon
isLockedMessage_zh: 敬请期待
```

整组条目也可随开关量锁定：

```ini
[canBuild_1]
isLocked: if memory.inactivate
isLockedMessage:
isLockedMessage_zh: 构建已停止
forceNano: true
```

### `[movement]`：移动类型

`movementType` 的合法取值共 6 种：`NONE` / `LAND` / `AIR` / `HOVER` / `WATER` / `OVER_CLIFF`。全体默认 `NONE`：

```ini
[movement]
movementType: NONE
moveSpeed: 1
joinsGroupFormations: false
```

**`movementType` 通常由家族行为模板设定**：新增某一类移动单位时，直接 `copyFrom` 对应家族模板即可继承正确类型，不必在活体里重设。各模组的家族模板命名及其对应的 movementType 由该模组自己决定——不要假设某个模板名必然对应某个类型，用前先核实该模板。

移动细调键：

```ini
[movement]
moveSpeed: 2.036
moveAccelerationSpeed: 0.03
moveDecelerationSpeed: 0.06
maxTurnSpeed: 4
turnAcceleration: 0.5
```

倒车单位加 `reverseSpeedPercentage`，例如 `reverseSpeedPercentage: 0.75`。

### `[attack]`：攻击能力

全体默认不可攻击：

```ini
[attack]
canAttack: false
canAttackFlyingUnits: false
canAttackLandUnits: false
canAttackUnderwaterUnits: false
maxAttackRange: 0
```

活体打开对应开关并设射程 / 射击间隔：

```ini
maxAttackRange: 360
shootDelay: 0.15s
```

攻击条件可写**动态表达式**，并支持多目标炮塔：

```ini
canAttack: true
canAttackLandUnits: if not self.isInWater()
canAttackUnderwaterUnits: if self.isInWater()
turretMultiTargeting: true
```

炮塔是否随车身转向用 `turretRotateWithBody`：

```ini
turretRotateWithBody: false
```

「不攻击但有射程圈」的典型（如雷达）：`canAttack: false` + `showRangeUIGuide`：

```ini
[attack]
canAttack: false
maxAttackRange: ${my_range}
showRangeUIGuide: true
```

### 武器三件套：`[turret_N]` + `[projectile_N]` + `[effect_*]`

> **铁律**：luke 语里**没有 `[arm_*]` 节**。武器一律由「炮塔 `[turret_N]` + 弹丸 `[projectile_N]` + 命中 / 粒子特效 `[effect_*]`」实现。写武器时不要臆造 `[arm_*]`。

#### `[turret_N]` 炮塔

炮塔用 `projectile:` 关联弹丸——数字对数字节，自定义名对同名节：

```ini
projectile: 1
[projectile_1]
```

自定义名例：

```ini
[turret_1]
projectile: beam
delay: 12
```

炮塔常用键：挂载坐标 `x` / `y`、本炮塔冷却 `delay`、转速 `turnSpeed` / 转速加速 `turnSpeedAcceleration`、`size`、散布 `aimOffsetSpread`：

```ini
[turret_1]
delay: 1s
turnSpeed: 4.2
turnSpeedAcceleration: 0.3
aimOffsetSpread: 0.6
size: 5
```

> **散布键真名是 `aimOffsetSpread`**，不存在 `aimOffsets`。

开火表现：音效 / 音量 / 炮口焰 / 闪光 + 后坐：

```ini
shoot_sound: ROOT:path/to/sound.wav
shoot_sound_vol: 0.5
shoot_flame: small
shoot_light: #FFEECCCC
recoilOffset: -0.5
recoilOutTime: 6
recoilReturnTime: 12
```

开火时触发隐藏动作用 `onShoot_triggerActions`（值对应某个 `[hiddenAction_*]` 名）：

```ini
onShoot_triggerActions: attacking_target
```

其他炮塔特性：

- 开火角度限制 `canAttackMaxAngle: 20`
- 激光待机扫描 `idleSweepAngle` / `idleSweepDelay` / `idleSweepSpeed`
- 纳米建造主炮塔 `isMainNanoTurret: true`（不带 `image:`，常配 `warmup`）
- 多炮塔各带独立参数（`[turret_2]` 可有自己的 `image_drawOffsetY` / `x` / `y` / `idleDir` / `projectile` / `size` / `delay`）
- 炮塔耗能常由炮塔家族模板统一注入：

```ini
[turret_1]
resourceUsage: power = ${power_usage}
```

#### `[projectile_N]` 弹丸

弹丸的核心区分是 **`areaDamage`（范围伤害）** 对 **`directDamage`（直击伤害）**。

即时光束弹：

```ini
[projectile_1]
life: 20
instant: true
beamImage: ROOT:path/to/beam.png
explodeEffect: NONE
areaDamage: 40
areaRadius: 10
friendlyFire: true
```

飞行范围弹：

```ini
[projectile_1]
life: 60
speed: 6
frame: 5
areaDamage: 45
areaRadius: 96
targetGround: true
targetGroundSpread: 40
friendlyFire: true
explodeEffect: explosion_shake
```

直击弹 + 落点生成弹药单位（用 `spawnUnit` 在命中处生成一个独立单位，并通过 `addResources` 把伤害 / 速度等透传给它）：

```ini
[projectile_1]
directDamage: 210
speed: 1
life: 0
explodeOnEndOfLife: true
largeHitEffect: true
spawnUnit: """p_${core.altNames}(
    addResources=
        damage: ${section.directDamage}|
        speed: ${section.speed}
)
"""
```

> `spawnUnit` 生成的弹药单位（如 `p_<altNames>`）通常是独立定义文件（惯例命名 `p_*.ini`），其命中特效在该文件内部定义：

```ini
explodeEffect: explosion_cannon3
[effect_explosion_cannon3]
alsoPlaySound: ROOT:path/to/sound.wav
```

持续光束弹（跟随炮塔、复用上一发）：

```ini
[projectile_beam]
life: 15
instant: true
instantReuseLast: true
instantReuseLast_alsoChangeTurretAim: true
moveWithParent: true
beamImage: ROOT:path/to/beam.png
beamImageEnd: SHARED:beam1_end.png
beamImageStart: SHARED:beam1_start.png
beamImageOffsetRate: 3
shieldDamageMultiplier: 0.75
areaDamage: 15
areaRadius: 8
```

近战弹：`[attack]` 加 `isMelee` / `dieOnAttack`，弹丸加扩张 / 击退：

```ini
[attack]
isMelee: true
dieOnAttack: true
maxAttackRange: 1
shootDelay: 0
[projectile_1]
areaRadius: 115
areaExpandTime: 60
largeHitEffect: true
pushForce: 3000
```

> **`explodeEffect` 必须指向真实的 `[effect_*]` 节或 `NONE`**，否则无效。倍数可用 `*N` 后缀，例如 `explodeEffect: sparks*4`。

#### `[effect_*]` 特效

命中位移特效：

```ini
[effect_explosion_shake]
drawType: displacement
alsoPlaySound: ROOT:path/to/sound.wav:2
image: ROOT:path/to/sprite.png
life: 60
scaleFrom: 0
scaleTo: 10
yOffsetAbsolute: -1000
ySpeedAbsolute: 50
alpha: 0.02
```

物理粒子特效：

```ini
[effect_sparks]
attachedToUnit: false
life: 150
physics: true
xSpeedRelativeRandom: 0.8
ySpeedRelativeRandom: 0.8
hSpeed: 2
image: SHARED:spark.png
priority: verylow
alsoPlaySound: ROOT:path/to/sound.wav
```

> 粒子淡出键 `fadeOut: true` 真实存在，可按需加到对应的 `[effect_*]` 里。

### `[graphics]`：整体渲染

全局母版常把本体图设为空白并关掉低血特效：

```ini
[graphics]
image: SHARED:blank.png
disableLowHpFire: true
disableLowHpSmoke: true
showQueueBar: false
```

`[graphics]` 还承载行驶特效（活体追加）：

- 扬尘 `dustEffect: true`
- 经过水面时的溅水 `splastEffect: true`（注意键名就是 `splastEffect`，照抄原拼写）
- 护盾贴图 `image_shield`

### 贴花 `[decal_*]`：分层贴图

本体用 `[decal_img]`，阴影用 `@copyFromSection: decal_img` 复用后改层 / 颜色 / 偏移：

```ini
[decal_img]
image: ROOT:path/to/sprite.png
dirOffset: 90
teamColors: true
[decal_shadow]
@copyFromSection: decal_img
layer: shadow
color: #000000
alpha: 0.5
xOffsetAbsolute: 2
yOffsetAbsolute: 2
```

炮塔贴图用编号 `[decal_img2]` 并 `basePositionFromTurret: N` 跟随炮塔（活体 `[turret_N]` 因此不再带 `image:`）：

```ini
[decal_img2]
image: ROOT:path/to/turret.png
imageScale: 0.1
basePositionFromTurret: 1
teamColors: true
```

可用全局母版为 `decal_img` / `decal_img2` / `decal_img3` 统一种下 `teamColors: true`（团队染色种子，残骸随之染暗）。

`layer` 常见取值：`beforeBody` / `shadow` / `beforeUI`。

动态贴花用 `isVisible` 条件 + 表达式驱动 `basePosition`，并可用 `@define ord:N` 参数化后批量展开：

```ini
isVisible: if ${my_range ^ 2} > distanceBetweenSquared( self, memory.unitDetected[${ord}] ) > 0
image: SHARED:light_50.png
color: #ff0000
onlyWhenSelectedByOwnPlayer: true
```

炮塔家族模板往往自带炮塔阴影 `[decal_img2_shadow]` 与缺电图标 `[decal_power_failure]`（`image: ROOT:path/to/power_failure.png`）——`copyFrom` 该模板的炮塔自动获得「缺电图标」行为，无需自写。

### `[placementRule_N]`：放置规则

```ini
[placementRule_1]
searchTags: mytag
minCount: 1
searchDistance: 300
searchTeam: own
cannotPlaceMessage: You can't place this here
cannotPlaceMessage_zh: 不能放置在此处。
```


`maxCount: 0` 表示「禁止在该 tag 附近放置」：

```ini
[placementRule_stopPlaceOnSelf]
searchTags: mytag
searchDistance: 20
searchTeam: any
maxCount: 0
```

### `[attachment_N]`：附件单位

```ini
[attachment_1]
x: 0
y: 0
isUnselectable: true
isVisible: false
canBeAttackedAndDamaged: false
onCreateSpawnUnitOf: myattachment
```

### 同一语言的非战斗用法

同一套配置语言不止能做 RTS 战斗单位，也能做纯 UI / 逻辑模组。做这类模组时，可把单位当「UI 格子」用——复用 `[core]` / `name` / `tags` / `@memory` / `isUnselectable`，但不含武器移动：

```ini
[core]
name: mycell
showInEditor: false
tags: mycell
canOnlyBeAttackedByUnitsWithTags: mysweeper
isUnselectable: true
…
@memory mine: bool
```

两个可迁移技法：

- luke 语的 `[hiddenAction_*]` + 消息机制足以驱动纯逻辑 / UI 应用，不限于战斗单位。
- 做纯 UI / 逻辑模组时，可用**面积伤害当一对多广播**：配合 `canOnlyBeAttackedByUnitsWithTags` 限定接收方，用一发 `areaDamage` 命中范围内所有带指定 tag 的单位，实现一次性的群体通知 / 触发。

### 坑与铁律（必读）

- **多行块有两种定界符，都用于「注释掉大段配置」**：三引号 `"""` 与双引号 `""`。标记必须**偶数配对**；混用时极易漏配对、吞掉后续整段配置。改含大块注释的文件时，先数清每种定界符的配对。
- **注释 / 路径会漂移，别信注释里的旧名**：注释里写的活体路径、单位名可能早已过时。引用某个活体 / 文件前必须用 Glob / ls 实地核实它真的在那里。
- **巨型自动生成文件勿手改、勿整文件读入上下文**：有一种常见技法是用 `copyFrom` 引入一个由数千个参数化贴花（`@copyFromSection: decal_c` + `@define ord:N`）组成的自动生成文件，借此同时标记数千个被探测目标。这类文件动辄数百 KB、含数千节，手改极易出错，也不要整文件读进上下文——用参数化模板生成，不要逐节编辑。
- **武器永远是 `[turret_N]` + `[projectile_N]` + `[effect_*]`，没有 `[arm_*]`**。散布键是 `aimOffsetSpread` 不是 `aimOffsets`。
- **静态进母版、动态留活体**：`fogOfWarSightRange`、`tags: comm`、攻击 / 移动逻辑等，按「残骸是否应继承」来决定归属，别把动态行为写进 `.template`。

## 3. luke 语运行时脚本与逻辑

luke 语没有函数、没有真正的 `if-else`、没有 `for`。所有"逻辑"都由一堆 `[action_*]` / `[hiddenAction_*]` 节 + 触发链 + 内存 + 消息拼出来。写之前的铁律:**先打开你工程里最近邻的真实节,照抄它的键名、大小写、缩进,再改**——这门语言的大小写与写法不统一是常态(见文末坑),凭记忆硬写几乎必错。

### 行动的两种形态:`[action_]` 与 `[hiddenAction_]`

| 节                  | 有无按钮   | 触发方式                                            | 典型用途        |
| ------------------ | ------ | ----------------------------------------------- | ----------- |
| `[action_X]`       | 玩家可见按钮 | 玩家点击(也能 `autoTrigger`)                          | 开关、建造项、信息显示 |
| `[hiddenAction_X]` | 无按钮    | 事件 / `autoTrigger` / `alsoTriggerAction` / 建造队列 | 一切后台逻辑      |

`[action_*]` 是玩家点的按钮,靠 `text`/`text_zh`/`displayType` 显示,点击执行 `setUnitMemory`,并用 `alsoTriggerAction` 派生出 `[hiddenAction_*]` 真正干活。通用按钮行为(`isVisible`、不进队列等)由 `@copyFromSection` 从伪按钮模板继承:

```ini
[action_stop]
@copyFromSection: template_m

text: Stop
text_zh: %{select( memory.inactivate, "开始", "停止")}

description:
description_zh: 当资源不足以支撑建造时，可选择强制停止。

setUnitMemory: inactivate = not memory.inactivate

displayType: action

alsoTriggerAction: forceStop, forceStart
```

被继承的伪按钮模板(名字自定,下例叫 `[template_m]`)定义了"点一下即触发、不进建造队列"的骨架:

```ini
[template_m]
# 这三个键必须同时写。反编译 ag.java 确认：只有
#   !canPlayerCancel && !allowMultipleInQueue && alwaysSinglePress
# 三者同时成立，引擎才会把动作标记为"立即执行、不进队列"。
# 而且 canPlayerCancel / allowMultipleInQueue 的默认值都是 true ——
# 只写 alwaysSinglePress: true 是没用的。
alwaysSinglePress:true
allowMultipleInQueue:false
canPlayerCancel:false

buildSpeed:0


isVisible: true
```

`[hiddenAction_*]` 没有按钮,只能被事件/派生/队列触发,用 `requireConditional` 决定本次是否执行:

> **⚠️ `[hiddenAction_*]` 里不能写 `isVisible`。** 反编译 `ag.java` 确认，解析时会检查：
> 只要 `isVisible` 存在且**不是静态 `false`**，就直接抛异常
> `"isVisible doesn't make sense to use in hidden actions"`，整个模组加载失败。
> 引擎本来就会把 hiddenAction 的可见性强制设为 `false`——这是它的定义，不是可选项。

```ini
[hiddenAction_forceStop]
requireConditional: if memory.inactivate

setUnitMemory: last_product = activeWaypointTarget

clearAllWaypoints: true
```

> **别把二分法当铁律。** `[action_*]` 同样能 `autoTrigger`:`@copyFromSection` 继承伪按钮骨架 + `autoTrigger: true` 就是自触发按钮,`autoTrigger: if ...` 则是条件自触发。"action=按钮 / hiddenAction=事件专用"只是常态,不是语法限制。

### 触发时机:事件、轮询、派生

**`autoTriggerOnEvent`** 监听引擎事件,可逗号列多个:

```ini
[hiddenAction_onDestroy]
autoTriggerOnEvent: destroyed, teamChanged
```

常见事件名:

| 事件                                  | 语义                    |
| ----------------------------------- | --------------------- |
| `created`                           | 单位**生成**时(初始化)        |
| `completeAndActive`                 | **建造完成并激活**时          |
| `destroyed`                         | 被摧毁                   |
| `teamChanged`                       | 换队                    |
| `tookDamage(withTag="X")`           | 受到带该 tag 的伤害          |
| `newMessage(withTag="X")`           | 收到带该 tag 的消息          |
| `newWaypointGivenByPlayer`          | 玩家下达路径点               |
| `queueItemAdded(withActionTag="X")` | 带该 tag 的 action 进建造队列 |
| `queuedUnitFinished`                | 队列中单位造完               |

> `created` 与 `completeAndActive` **语义不同**:前者是单位一出现就触发(含放置瞬间),后者要等建造条走完、单位真正激活。初始化内存用 `created`,依赖"已经可用"的逻辑用 `completeAndActive`。

`queueItemAdded(withActionTag=)` 靠 action 自己的 `tags:` 关联,而非内存——监听侧写 `withActionTag`,对应 action 侧写同名 `tags:`:

```ini
autoTriggerOnEvent: queueItemAdded(withActionTag= "my_tag")
```

**`autoTrigger`** 是逐周期轮询:`true` 无条件每周期触发、`if <cond>` 满足才触发。

```ini
[hiddenAction_checkTimer]
autoTrigger: if self.timeAlive > memory.my_timer
```

轮询频率由 `[core]` 的节流键决定。高频(每周期)必须显式开 `_allowDangerousHighCPU`,否则引擎会压制:

```ini
autoTriggerCooldownTime: 1
autoTriggerCooldownTime_allowDangerousHighCPU:true
autoTriggerCheckRate: every8frames
```

注意实装 token 是小写 `every8frames`,照抄即可——大小写本身在引擎内不敏感,但不同文件写法不统一,别自作主张改成 `every8Frames`。

**双保险**:同一行动可同时写 `autoTriggerOnEvent` + `autoTrigger` + `requireConditional`,既在事件瞬间响应、又靠轮询兜底。下例是常见的"残骸化"技法——受击或轮询到 `hp<=0` 都能触发:

```ini
[hiddenAction_wreck]
autoTriggerOnEvent: tookDamage
autoTrigger: true
requireConditional: if self.hp <= 0

setUnitStats: maxHp = self.maxHp * 2, hp += self.maxHp
switchToNeutralTeam: true

clearAllWaypoints: true

convertTo: w_${core.altNames}
```

**派生**:`alsoTriggerAction: a,b,c` 本帧按顺序派生多个行动:

```ini
alsoTriggerAction: stepA, playSound, stepB, stepC
```

**充当 `for`**:`alsoTriggerActionRepeat: N` 把相邻的 `alsoTriggerAction` 重复 N 次,体内用内建 `index`(0..N-1);N 可以是运行期表达式:

```ini
[hiddenAction_initLoop]
alsoTriggerAction: initLoop_body
alsoTriggerActionRepeat: 16

[hiddenAction_initLoop_body]
setUnitMemory: myArray[index] = index + 1
```

N 取运行期量时,可直接写数组长度等表达式,例如 `alsoTriggerActionRepeat: memory.myArray.size`。

**递归/分帧**:`alsoTriggerOrQueueActionConditional: if <cond>` 让派生行动在满足条件时改走下一帧队列(避免本帧爆栈):

```ini
alsoTriggerAction: processNeighbor
alsoTriggerActionRepeat: 8
alsoTriggerOrQueueActionConditional: if memory.direction == 8 and memory.counter == memory.target
```

**扩展钩子**:在入口行动末尾内联 `${section.extraTriggerActions}`,继承者只需补一行 `extraTriggerActions:` 即可插入自定义行动(载入期展开):

```ini
[hiddenAction_entry]
alsoTriggerAction: stepA, stepB, stepC, ${section.extraTriggerActions}
```

覆写方只要在自己的 `[hiddenAction_entry]` 里加一行 `extraTriggerActions: myExtraAction` 即可挂钩。

### 条件与分支

`requireConditional: if ...` 支持 `and`/`or`/`not`、`==`/`!=`/`>=`/`>`/`<`,以及链式比较(`a >= b >= c`):

```ini
requireConditional: if ${maxW} >= ${w} >= 5 and ${maxH} >= ${h} >= 5 and ${w} * ${h} > ${count} > 0 and ( not memory.flags[0] or ${maxT} >= ${t} >= 1 )
```

> **优先级别靠猜。** 上面这行用显式括号把 `or` 子句包起来。混用 `and`/`or` 时**一律加括号**,别赌默认优先级。

没有真正的三元/`else`,唯一的条件取值是 `select(cond, a, b)`,靠嵌套实现多分支:

```ini
frame: """
    select(
        memory.stateA, select( memory.stateB, 12 + select( memory.stateC, 0, 2), memory.valueX),
        select( memory.stateD, 13, memory.valueY + 9 )
    )
"""
```

旧版本引擎没有真正的 `if-else`,`select` 嵌套就是多分支的标准写法;即使较新版本补了条件语句,`select` 仍是取值表达式的主力。

### 内存:per-unit 持久变量

`@memory name: type` 声明单位私有的持久变量,用 `memory.name` 读。类型含 `bool`/`boolean`/`float`/`string`/`unit`,加 `[]` 为数组:

```ini
@memory myFlag: bool
@memory myValue: float
@memory myList: unit[]
```

`setUnitMemory` **只写自己的**内存,支持逗号多重赋值与 `"""` 多行;**没有 `++`**,自增手写 `x = memory.x + 1`:

```ini
setUnitMemory: """
origin = getAsMarker,
size = ${size},
myArray[0] = ${myConst},
myFlags[1] = true
"""
```

> **🟢 多赋值是「严格顺序执行」，不是并行求值**（反编译 `VariableScope$CachedWriter.writeToUnit` 确认：它逐个调用 `WriterElement.writeToUnit`）。
> 所以**后面的赋值能看到前面刚写入的新值**，可以放心"先算再用"：
>
> ```ini
> # 先减仇恨，再按"减完的新值"决定要不要清空槽位 —— 这样写是对的
> setUnitMemory: """
> threat[i]= max(0, memory.threat[i] - 40),
> unit[i]= select( memory.threat[i] <= 10, null, memory.unit[i] )
> """
> ```
>
> 如果引擎是并行求值，第二行会读到旧值，槽位永远清不掉——**逻辑失效且不报错**。这条顺序保证是手写状态机、差分、扫描的前提。

读**别的单位**内存(自己也行)的唯一手段是 `readUnitMemory("name", type=...)`:

```ini
setUnitMemory: myFlag = customTarget1.readUnitMemory( "myData", type = "bool[]" )[eventData( "", type = "float" )]
```

### 数组操作

| 操作        | 写法                            |
| --------- | ----------------------------- |
| 下标读写      | `arr[i] = v`                  |
| 取长度       | `arr.size`（官方写法；`arr.length` 亦可） |
| 压掉 null 洞 | `shrinkArrays: arr`           |
| 清空        | `arr = null`                  |

```ini
setUnitMemory: myArray[eventData("id", type = "float")] = null, clear = 0

shrinkArrays: myArray

alsoTriggerAction: processItem
alsoTriggerActionRepeat: memory.myArray.size
```

**跨单位读数组**:两种写法在真实代码里**并存**,不是非此即彼——

- `.get(i)`:`customTarget1.readUnitMemory( "myData", type = "bool[]" ).get(0)`
- 直接 `[i]`:`customTarget1.readUnitMemory("myData", type="bool[]")[eventData("", type="float")]`

同一文件可能两者混用。遇到跨单位数组重定向取不到值时,`.get()` 是已知可用的绕法,但不要把"必须 `.get()`、不能 `[]`"当绝对规则。

### 载入期 vs 运行期:三种插值

| 语法       | 时机      | 用途                                |
| -------- | ------- | --------------------------------- |
| `${...}` | 载入期展开一次 | 常量、宏、`${int()}`/`${sqrt()}` 编译期计算 |
| `%{...}` | 运行期每帧求值 | 随状态变化的 UI 文本                      |
| `${节.键}` | 载入期     | 复制另一节的键值                          |

载入期 `${...}`(含编译期数学,只算一次):

```ini
areaRadius: ${int(sqrt((size / 2) ^ 2 * 2) * 2 + 0.5)}
```

运行期 `%{...}`(每帧实时,专用于 UI 文本;下例玩家可见,中英成对):

```ini
showMessageToPlayer: Level: %{substring("Low   Mid   High  ", memory.level * ${section.w}, (memory.level + 1) * ${section.w})}
showMessageToPlayer_zh: 等级：%{substring("低  中  高  ", memory.level * ${section.wz}, (memory.level + 1) * ${section.wz})}
```

**`${节.键}` 复制键值**:让一个节直接内联另一个节的键,保持两者一致(例如音效节复用主入口节的 `requireConditional`)——

```ini
[hiddenAction_playSound]
requireConditional: ${hiddenAction_doThing.requireConditional}
playSoundAtUnit: ROOT:path/to/sound.ogg
```

> **任意普通键都能被 `${节.键}` 读取**,不止 `@global`/`@define`。在节里写 `w= 6`,别处用 `${section.w}` 就能复用。普通键就是载入期可引用的命名常量。

#### `@global` / `@define` 声明

`@global name: value` 声明**文件级**常量/命名表达式,用 `${name}` 引用。它写在任意节里却文件全局可见:

```ini
[decal_bg]
@global bg= -10
...
yOffsetAbsolute: memory.count * memory.size / 2 + ${bg}
```

`@global` 还能把**运行期逻辑别名化**。常见做法是把"事件源是不是本实例"的判断别名成一个全局名,到处 `requireConditional: if ${isMine}`:

```ini
@global isMine: eventSource == select( customTarget1 == null, memory.customTarget1, customTarget1)
@global isMine2: eventSource.customTarget1 == customTarget1
```

`@define name= value` 是**节内**(可随 `@copyFromSection` 继承)的载入期文本宏:

```ini
[template_digit]
@define s= 19
@define d= 0
@define v= memory.value
...
frame: ${v} / ${10 ^ d} % 10
```

### 资源作为状态与 buff 条

读资源用 `self.resource.X`;声明 `[resource_X]`(私有)/`[global_resource_X]`(全队);写用 `setResourcesWithLogic` / `addResources` / `addResourcesWithLogic` / `takeResources*`:

```ini
setResourcesWithLogic: """
myRes = squareRoot(max(0, self.resource.power - self.resource.cap) / max(1, numberOfUnitsInTeam( withTag = "mytag" ))),
"""
```

载入期常量驱动的写法如 `addResourcesWithLogic: myRes = ${income}`。

**资源被当作 buff 条**用:受击事件往 `self.resource.slow` 之类加,`autoTrigger` 每周期减,再 `setUnitStats` 把它映射成减速/减射速:


```ini
[hiddenAction_buff_slow]
autoTriggerOnEvent: tookDamage(withTag="slow")

setResourcesWithLogic: slow = min( 50, self.resource.slow + eventSource.readUnitMemory("slow_rate", type = "float") )

[hiddenAction_buff_slow_recover]
autoTrigger: true

setResourcesWithLogic: slow = max(0, self.resource.slow - ${core.autoTriggerCooldownTime} * 0.125 )

setUnitStats: moveSpeed = ${movement.moveSpeed} / (self.resource.slow / 50 + 1)
```

> **语言支持复合赋值 `+=`**(至少 `setUnitStats`):`setUnitStats: maxHp = self.maxHp * 2, hp += self.maxHp`。但 `setUnitMemory` 自增样例仍是手写 `x = memory.x + 1`——不同指令支持度不同,照抄最近邻,别一概而论"有/无 `+=`"。

### 单位引用与搜索

内建单位引用关键字:

| 关键字                    | 含义           |
| ---------------------- | ------------ |
| `self`                 | 自己           |
| `eventSource`          | 事件/消息的来源单位   |
| `activeWaypointTarget` | 当前路径点目标      |
| `thisActionTarget`     | 逐目标处理时的当前目标  |
| `customTarget1`        | 生成者(spawner) |
| `parent`               | 挂载子单位的父体     |

就近搜索 `nearestUnit(withinRange=, withTag=, relation=)`,可链式 `.readUnitMemory(...)`:

```ini
setUnitMemory: myVal = nearestUnit(withTag = "mytag", withinRange = 20, relation = "neutral").readUnitMemory("myVal", type = "float")
```

全图找第一个匹配(常用于定位单例管理器):

```ini
@global myVal: globalSearchForFirstUnit(withTag = "manager", relation = "own").readUnitMemory("myVal", type = "float")
```

挂载子单位:`[attachment_X]` + `onCreateSpawnUnitOf` 生成,`attachment(slot="X")` 引用,父子互引用用 `parent`:

```ini
[attachment_sub]
...
onCreateSpawnUnitOf: mysubunit
```

引用方用 `sendMessageTo: attachment( slot = "sub" )`,子体用 `parent` 回引父体。

坐标/标记:`createMarker(x,y)`、`getOffsetAbsolute(...)`、`getAsMarker` 生成临时位置单位引用:

```ini
setUnitMemory: """
myMarker = createMarker((self.x - customTarget1.x - ${gap}) / ${gap}, (self.y - customTarget1.y - ${gap}) / ${gap}),
myList[0] = getOffsetAbsolute(x= -${gap}, y= -${gap})
"""
```

> `getOffsetRelative` 不如 `getOffsetAbsolute` 常见,是否可用、确切大小写请先查维基/代码表核实,别凭注释里的拼写照抄。

### 标签系统

读取/筛选用 `unitref.tags(includes="X")`,可对 `self`/`activeWaypointTarget`/`thisActionTarget` 等任意引用筛:

```ini
[hiddenAction_stopReclaim]
autoTriggerOnEvent: newWaypointGivenByPlayer
requireConditional: if self.hasActiveWaypoint(type = "reclaim" ) and activeWaypointTarget.tags(includes = "mytag" )

clearActiveWaypoint: true
```

**队伍级**标志位用 `globalTeamTags(includes=)` / `addGlobalTeamTags`——每队一份,适合"全队第一个单位享受一次性效果"这类全局状态:

```ini
[hiddenAction_firstOne]
autoTriggerOnEvent: created
requireConditional: if not self.globalTeamTags(includes="first_built")

setBuilt: 1

addGlobalTeamTags: first_built
```

### 消息传递:点对点、广播、协同

点对点三件套:`sendMessageTo` + `sendMessageWithTags`(可多 tag) + `sendMessageWithData`(`=` 匿名 / `key=` 具名,可多项):

```ini
sendMessageTo: self
sendMessageWithTags: myTag1, myTag2
sendMessageWithData: = ${section.id}, key = select( memory.flags[${section.id}], "", "back" )
```

接收端用 `autoTriggerOnEvent: newMessage(withTag="X")` + `eventData("key"/"", type=...)` 取数据,`eventSource` 即发送者:

```ini
[hiddenAction_onMsg]
autoTriggerOnEvent: newMessage(withTag="mytag")

setUnitMemory: myArray[eventData("id", type = "float")] = null, clear = 0
```

**跨建筑协同(全局配置中枢)**:多个单位把配置发给一个单例管理器集中存储,别处再从它读回——

```ini
sendMessageTo: globalSearchForFirstUnit(withTag = "manager", relation = "own")
sendMessageWithTags: update_config
sendMessageWithData: my_value = memory.step
```

管理器侧落库:

```ini
[hiddenAction_update_config]
autoTriggerOnEvent: newMessage(withTag = "update_config")

setUnitMemory: myConfig = eventData("my_value", type = "float")
```

**一对多广播**:做纯 UI/逻辑模组、或需要"范围内全体同时响应"时,可向地面发一枚带 `tags` 的瞬时面伤投射物,范围内所有单位都收到 `tookDamage(withTag=)`,相当于一对多广播:

```ini
[projectile_1]
areaRadius: ${int(sqrt((size / 2) ^ 2 * 2) * 2 + 0.5)}
tags: broadcast
```

广播接收端**必须自过滤**,否则别的实例发出的广播也会误触(用上文的 `${isMine}` 之类判断过滤事件源):

```ini
[hiddenAction_onBroadcast]
autoTriggerOnEvent: tookDamage( withTag = "broadcast" )
requireConditional: if ${isMine}
```

**换皮子系统(attachment + convertTo + 消息)**:子单位收到换皮消息后 `convertTo` 原地切换成另一款,再回发消息通知父体:

```ini
[template_skin]
autoTriggerOnEvent: newMessage( withTag = "change_skin" )
requireConditional: if parent.readUnitMemory( "skin_id", type = "string" ) == "${skin}"

convertTo: skin_${skin}

sendMessageTo: parent
sendMessageWithTags: skin_changed
```

### 开火/建造钩子与逐目标处理

| 钩子                              | 时机  |
| ------------------------------- | --- |
| `onShoot_triggerActions: a, b`  | 开火时 |
| `whenBuilding_triggerAction: a` | 建造时 |

```ini
onShoot_triggerActions: myAction, playSound
```

**逐目标触发**:`takeResources_*`(搜索一批) + `takeResources_triggerActionForEach: <action>`,处理行动里用 `thisActionTarget` 指代当前单位:

```ini
takeResources_includeUnitsWithinRange: ${myRange}
takeResources_includeUnitsWithinRange_team: enemy
takeResources_maxUnits: 1000
takeResources_searchOnly: true
takeResources_triggerActionForEach: processTarget
```

对应的 `[hiddenAction_processTarget]` 里就能对 `thisActionTarget` 做判断,如 `thisActionTarget.isUnderwater()`。

### 调试与提示

| 指令                                | 去向    |
| --------------------------------- | ----- |
| `debugMessage`                    | 日志    |
| `showMessageToPlayer` / `_zh`     | 本玩家屏幕 |
| `showMessageToAllPlayers`         | 所有玩家  |
| `showQuickWarLogToPlayer` / `_zh` | 战报    |

```ini
showQuickWarLogToPlayer: Received unit from %{eventSource.playerName}: %{eventSource}!
showQuickWarLogToPlayer_zh: 收到 %{eventSource.playerName} 的单位: %{eventSource}!
```

### 块注释与多行

`"""` 是双重身份:既是多行字符串,也是块注释——成对包住整段 action 即可注释掉:

```ini
"""
[hiddenAction_old_logic]
autoTriggerOnEvent: tookDamage(withTag= "reset")
alsoTriggerAction: doThing
"""
```

**务必保持 `"""` 成对**,数量为偶数,否则后续内容会被整段吞掉。

`copyFrom` 也能用 `"""` 多行列出多个被继承模板(逗号分隔):

```ini
copyFrom: """
base.template,
weapons.template,
ui.template
"""
```

### 性能护栏:`[placementRule_*]`

限制同类单位可放置数量,超限给中英提示:

```ini
[placementRule_limited]

maxCount: 0

searchTags: ${core.name}
searchDistance: Infinity

cannotPlaceMessage: Too many of these units may affect performance.
cannotPlaceMessage_zh: 此类单位过多会影响游戏性能。
```

### 坑与告诫

- **坊间指南提到的 API 未必存在。** 像 `transporting()` / `transportDrop` 这类在某些二手资料里出现的函数,不一定存在于你的引擎版本。引用任何没在自己代码里跑通过的 API 前,**务必查代码表/维基核实**,别照别人的笔记抄。
- **数组长度用 `.size`（官方写法）。** 官方代码表把 `memory.NAME.size` 列为数组方法（1.15），语义是"数组大小，**包含空位**"。`arr.length` / `arr.length()` 在真实模组里也能用，但**官方文档没有把它定义为数组方法**（`length(string)` 是字符串专用的）。实测本工作区 1900+ 个文件：`.size` 出现 221 次，`.length()` 仅 6 次——**`.size` 才是事实标准**。
- **casing 不统一是实装常态。** `self.timeAlive`/`self.TimeAlive`、`sqrt`/`squareRoot`、`every8frames`、`bool`/`boolean`、`@global` 用 `:` 或 `=`,都在不同文件里出现过。**照抄最近邻,别据此推断"可随意大小写"。**
- **优先级永远加括号。** 没有依据表明 `and` 默认高于 `or`,混用时一律显式括号(见条件章)。
- **跨单位数组 `[]` 与 `.get()` 并存**,不是非此即彼(见数组章)。遇到重定向取不到值优先试 `.get()`,但别把它当硬性语法。
- **高频 `autoTrigger` 要显式开 `_allowDangerousHighCPU`**,并清楚联机同步/卡顿代价;能用事件(`autoTriggerOnEvent`)或路径点钩子就别每周期轮询。

## 4. 用引擎做非战斗 / UI 驱动模组

铁锈战争（RW）引擎可以完全脱离"造兵打仗"：只靠单位 + 内存 + 消息 + 贴花，用 luke 语就能写出带状态机、随机数、UI、音效、统计的完整小程序或小游戏。整套逻辑里没有一行"真·脚本"——所有行为都是 `[hiddenAction_*]` 触发链、`sendMessage`/`tookDamage` 通信、`@memory` 变量、`[decal_*]` 贴花拼出来的。本章把"把引擎当通用运行时"的手法逐一拆开，每一条都可迁移到任意 RW 模组。

> 这些写法大量依赖版本相关行为（见文末坑表）。动手前先确认目标引擎版本，并在自己的工程里核对实际键名/节名拼写——luke 语拼错不报错，只静默失效。

> **出处与致谢**：本章的骨架提炼自 **GMBOX** 的多个可玩模组（《扫雷 Mine Sweeper》《纸牌之王 Kings of Cards》《战车纷争 War\&Panzer》《非零博弈 Beyond Zero》），其中《扫雷》是一套完整的"非战斗 UI 游戏"范例。**经作者同意，本章末「实战范例：GMBOX《扫雷》原样代码」一节直接收录其真实代码（保留原命名、数值与文案），以留下作者痕迹**；本章正文的通用示例为便于迁移已做中性化，两者对照阅读即可。

### 总体架构：控制器 + 被驱动单位 + 攻击互锁

非战斗模组的典型骨架是两类单位：

- **控制器**：全局状态机 + UI 宿主 + 建造者，持有整局数据。
- **被驱动单位**：成百上千个"数据 + 像素"实体，只听控制器指挥。

两者用 `canOnlyBeAttackedByUnitsWithTags` 做双向互锁，保证"只有控制器能操作被驱动单位、被驱动单位只认自己的控制器"，不会误伤地图上别的东西：

```ini
# 控制器
name: mycontroller
canOnlyBeAttackedByUnitsWithTags: mycell

# 被驱动单位
name: mycell
canOnlyBeAttackedByUnitsWithTags: mycontroller
```

被驱动单位通常彻底藏起来、不可选、不进编辑器，纯粹作为被控制器驱动的容器存在：

```ini
showInEditor: false
tags: mycell
canOnlyBeAttackedByUnitsWithTags: mycontroller
isUnselectable: true
```

### 两层复用：目录级 all-units.template + copyFrom 模块拼装

务必分清**两层**复用：

1. **显式拼装（`copyFrom`）**——把一个单位拆成多个职责模板，再在 `[core]` 里拼起来。每个 `.template` 负责一块功能（新开局、UI、设置、统计、多人、帮助、随机数……）：

```ini
[core]
copyFrom: """
module_a.template,
module_b.template,
module_c.template
"""
name: mycontroller
```

1. **隐式套用（目录级 `all-units.template`）**——比 `copyFrom` 更隐蔽：RW 引擎会把名为 `all-units.template` 的文件**自动合并进同目录及其所有子目录下的每一个单位**，不需要任何 `copyFrom`。可以多级叠放：根目录放一份套到全模组，子目录再放一份套到该目录下的单位（子目录那份还能自己 `copyFrom` 根目录的模板）。

正因如此，一个只写了几行、**没有任何 `copyFrom`** 的单位文件，也可能自带一大堆逻辑：

```ini
[core]
@global character: mychar
displayText: My Unit
displayText_zh: 我的单位
```

> 坑：目录级 `all-units.template` 是"隐形继承"。排查某个单位莫名其妙多出的键时，先去它所在目录及各级父目录找 `all-units.template`，再找 `copyFrom`。

### 把单位当画布：零价零血的 UI 基底单位

所有 UI/逻辑单位都应调成"不可见、不可碰、不可动、不会死"的纯画布。把下面这组键集中放进目录级 `all-units.template`，一次性套给所有 UI 单位：

```ini
[core]
price:0
maxHp:0
disableDeathOnZeroHp: true
autoTriggerCooldownTime: 1
autoTriggerCooldownTime_allowDangerousHighCPU:true
autoTriggerCheckRate: every8frames
disableAllUnitCollisions: true

[movement]
movementType:NONE
moveSpeed: 0
```

要点：

- `maxHp:0` + `disableDeathOnZeroHp:true`：0 血也不死，单位只当容器用。
- `movementType:NONE` + `disableAllUnitCollisions:true`：不动、不互相挤。
- `autoTriggerCheckRate: every8frames`：所有自动触发每 8 帧跑一次——这是全局节流开关，调它就能平衡性能与响应。
- 同文件里再放一个按钮基模板（如 `[template_m]`），统一所有 UI 按钮 `[action_*]` 的公共键（`alwaysSinglePress`、`buildSpeed:0`、`isVisible:true` 等）。

> **真实工程交叉验证**：本工作区多个非战斗/UI 驱动工程的 `all-units.template` 用的都是**同一套画布基线**，可直接照抄：
>
> ```ini
> [core]
> displayDescription:            # 故意置空
> price:0
> maxHp:0
> mass:2147483467                # 注意：真实工程里是 2147483467（少一位 4），非标准哨兵 2147483647
> radius:10
> disableDeathOnZeroHp: true
> strictLevel: 1
> autoTriggerCooldownTime: 1
> autoTriggerCooldownTime_allowDangerousHighCPU:true
> autoTriggerCheckRate: every8frames
> disableAllUnitCollisions: true
> [graphics]
> image: SHARED:blank.png
> showSelectionIndicator:false
> showHealthBar:false
> showEnergyBar:false
> showQueueBar:false
> showShieldBar:false
> [attack]
> canAttack:false
> maxAttackRange:0
> [movement]
> movementType:NONE
> moveSpeed: 0
> maxTurnSpeed: 0
> joinsGroupFormations: false
> ```
>
> 另有 `mass: 2147483467` 与 `mass: 2147483647` 两种写法并存——前者是**工程里的真实笔误**，靠"数值大到不可能被推动"照样生效；新写时用标准 int 最大值 `2147483647`。
>
> `displayDescription:`（键后留空）是**故意清空继承来的描述**的常用手法。

### 全局状态机：@memory 变量集中管理

luke 语没有函数表、没有全局变量表。整局状态全塞在控制器的 `@memory` 里，各职责模板各自追加自己的字段，合起来就是一张"状态表"：

```ini
@memory game_over: bool
@memory first_click: bool
@memory rows: float
@memory cols: float
@memory item_index: float
@memory original_position: unit
```


模式：**数组 + 下标**模拟一切集合。`flags: bool[]`（每格一个布尔）、`available_pool: float[]`（候选位置池）、`buttons[]` / `buttonsVisible[]`（按钮状态）、`stats_score[]`（历史记录）。

> 坑：luke 语数组为空时 `length` 行为特殊，需要自己维护一个 `xxx_index` 计数器当下标；删元素后用 `shrinkArrays` 压缩数组。

### 玩家输入 = 攻击路径点

RW 没有"鼠标点击某个单位"的 API。通用做法是把**玩家下达的攻击指令**当成唯一输入通道：选中控制器 → 右键点某个被驱动单位 = 给控制器下一个 attack 路径点。控制器监听 `newWaypointGivenByPlayer`，校验路径点类型是 attack、目标带指定标签，记下被点的目标：

```ini
[hiddenAction_cellSelected]
autoTriggerOnEvent: newWaypointGivenByPlayer
requireConditional: if self.hasActiveWaypoint(type= "attack") and activeWaypointTarget.tags(includes= "mycell") and not memory.game_over
setUnitMemory: selected_target= activeWaypointTarget
alsoTriggerAction: onClickA, onClickB, onClickC
```

一次点击分流到多条动作，各自带 `requireConditional` 自行决定是否生效。这是"单输入、多响应、条件分流"的典型 luke 写法。

### 跨单位通信三件套

控制器与成百上千个被驱动单位之间通信有三种手段，用途不同务必分清：

**① 定向消息**（点对点）。`sendMessageTo` 把消息发给**某一个**单位，接收端用 `autoTriggerOnEvent: newMessage(withTag=...)` 收，可带 `sendMessageWithData` 传参、用 `eventData("key", type=...)` 取参：

```ini
[hiddenAction_cellClear]
requireConditional: if memory.first_click
sendMessageTo: memory.selected_target
sendMessageWithTags: cell_clear
clearAllWaypoints: true
```

**② 空间广播**（一对多）。要"通知一片范围内的所有单位"时，逐个 `sendMessageTo` 太慢——改用**面积伤害当广播**：给控制器挂一门隐形、瞬发、无特效、`areaDamage:1` 的炮，炮弹半径覆盖整个作用区，用 `tags` 区分频道：

```ini
[projectile_1]
life: 1
invisible: true
instant: true
areaDamage: 1
areaRadius: ${region_radius}   # 载入期算出的半径, 覆盖整个作用区
targetGround: true
friendlyFire: true
explodeEffect: NONE
areaExpandTime: 0
tags: broadcast_a
```

挂多门炮就是多个广播频道（各用不同 `tags`）；`fireTurretXAtGround: N` 一开炮即广播。接收端用 `tookDamage(withTag=...)` 收：

```ini
[hiddenAction_onBroadcastA]
autoTriggerOnEvent: tookDamage( withTag = "broadcast_a" )
requireConditional: if ${verifi}
setUnitMemory: ...
```

> 这招适用于任何"纯 UI/逻辑模组需要一对多广播"的场景：全盘重置、全体刷新、群体状态翻转等，都比逐个发消息快。

**③ 跨单位读内存 + 来源校验**。被驱动单位用内置 `customTarget1` 指回自己的控制器，`readUnitMemory` 直接跨单位读控制器的 `@memory`。必须配两条 `@global` 公式做来源校验，防止多实例/多局串台：

```ini
@global verifi: eventSource == select( customTarget1 == null, memory.customTarget1, customTarget1)
@global verifi2: eventSource.customTarget1 == customTarget1
```

`verifi` 校验"消息/伤害来源是我的控制器"，`verifi2` 校验"来源是同一控制器下的另一个兄弟单位"（兄弟间通信用）。几乎每个接收动作都要带 `requireConditional: if ${verifi}` 或 `${verifi2}`。跨单位读数据统一走这种形式：

```ini
customTarget1.readUnitMemory("rows", type="float")
```

> 坑：定向消息频道（`newMessage` 的 tag）和炮弹广播频道（`tookDamage` 的 tag）**可以同名但是两套机制**，不要混。

### 构建网格：teleportTo 铺点 + spawnUnits 生成

需要在场上批量铺一片规则网格时，让控制器**自己瞬移到每个格点，就地生成一个单位**。循环 `rows*cols` 次，每次按一维下标算出二维坐标并瞬移过去：

```ini
[hiddenAction_cellSet]
teleportTo: memory.original_position.getOffsetAbsolute(x= ((memory.item_index % memory.cols) + 1 ) * ${size}, y= (int(memory.item_index / memory.cols) + 1) * ${size})
```

生成前先用 `nearestUnit` 判空避免重复铺；控制器必须 `isBuilder: true` 才能 `spawnUnits`：

```ini
[hiddenAction_cellSet_1]
requireConditional: if nearestUnit(withinRange= ${size}, withTag= "mycell") == null
spawnUnits: mycell
```

`original_position` 是开局用 `getAsMarker` 存下的锚点；`${size}` 是格子像素尺寸（载入期常量）。

### 固化空间关系：createMarker + getOffsetAbsolute 预存邻居

每个单位出生时（`autoTriggerOnEvent: created`）用 `createMarker` 把自己相对控制器的像素位置换算成**行列坐标**存起来（marker 单位的 x/y 即行列号），并把 8 个邻居的**绝对偏移点**一次性预存进数组，之后找邻居直接复用：

```ini
setUnitMemory: """
cell_position= createMarker((self.x - customTarget1.x - ${c_size}) / ${c_size}, (self.y - customTarget1.y - ${c_size}) / ${c_size}),
neighboring_list[0]= getOffsetAbsolute(x= -${c_size}, y= -${c_size}),
neighboring_list[1]= getOffsetAbsolute(y= -${c_size}),
neighboring_list[2]= getOffsetAbsolute(x= ${c_size}, y= -${c_size}),
neighboring_list[3]= getOffsetAbsolute(x= ${c_size}),
neighboring_list[4]= getOffsetAbsolute(x= ${c_size}, y= ${c_size}),
neighboring_list[5]= getOffsetAbsolute(y= ${c_size}),
neighboring_list[6]= getOffsetAbsolute(x= -${c_size}, y= ${c_size}),
neighboring_list[7]= getOffsetAbsolute(x= -${c_size}),
customTarget1= customTarget1
"""
```

把"空间关系"固化成数据的通用技巧：用一次 `getOffsetAbsolute` 预算 8 个方向点，后续直接 `neighboring_list[dir].nearestUnit(...)` 找邻居，省得每次重算。

### 遍历邻居读内存（luke 语的 for 循环）

循环 8 个方向，对每个方向点 `nearestUnit` 找到邻居、`readUnitMemory` 读它的字段、`select(...,1,0)` 转数值累加：

```ini
[hiddenAction_getNeighboringMines]
setUnitMemory: """
neighbor_count = memory.neighbor_count + select(
    memory.neighboring_list[memory.direction].nearestUnit( withTag= "mycell", withinRange = 1 ).readUnitMemory( "flag", type = "bool" ), 1, 0
    ),
direction = memory.direction + 1
"""
```

`alsoTriggerActionRepeat: 8` 配一个自增的 `direction` 下标，就是 luke 语的"for 循环"。

### 回调式"函数调用"：${section.extraTriggerActions}

luke 语里实现"带回调的函数调用"：被调模板在动作链尾部留一个 `${section.extraTriggerActions}` 占位，跑完自己的步骤后把调用方指定的续作串接执行：

```ini
[hiddenAction_myCallable]
alsoTriggerAction: step1, step2, step3, ${section.extraTriggerActions}
```

调用方只需覆写**同名节**的 `extraTriggerActions`，填上自己的续作：

```ini
[hiddenAction_myCallable]
extraTriggerActions: myFollowUp
```

被调模板留尾巴、调用方填续作——这是 luke 语里复用一段逻辑并"回调"到不同后续的标准范式。

### 手搓随机数（PRNG）与无放回抽样

luke 语没有现成的高质量随机数，但你**可以纯用 action 链 + @memory 手搓一个确定性 PRNG**（例如 MT19937 梅森旋转）：用 `@memory` 存状态寄存器，`created` 时初始化种子，所有二进制/十六进制/异或/移位运算全部用一串 `[hiddenAction_*]` 实现。确定性是关键——同种子同序列，才能支撑多人同步。

把它和回调范式结合：随机数模板跑完生成 + 取数链后，用 `${section.extraTriggerActions}` 回调到调用方的续作，调用方拿到结果就能继续。

**无放回抽样**：维护一个候选位置池数组，每次取 `|RandNum| % 池长度` 当下标，用掉后把该元素置 0 再 `shrinkArrays` 剔除，下次就不会重复抽到：

```ini
[hiddenAction_performSwap]
setUnitMemory: """
    pick_index= max(memory.RandNum, -memory.RandNum) % memory.available_pool.size,
    result[(memory.available_pool[memory.pick_index] - 1)]= true,
    available_pool[memory.pick_index]= 0,
    swap_index= memory.swap_index + 1
"""
```

需要"排除某些位置再抽样"（如保证某片区域一定不被选中）时，先把那几格从池里置 0 + `shrinkArrays`，再开始抽。

### 连锁展开 / 洪水填充（局部广播）

需要"从一个点向相邻点连锁扩散"（flood fill）时，再次用**小半径面积伤害**做局部广播：满足条件的单位发一发半径刚好覆盖一圈邻居的小炮，邻居收到 `tookDamage` 后继续发自己的小炮，自然形成扩散：

```ini
# 发起端：满足条件就放小炮
[hiddenAction_spread]
requireConditional: if memory.neighbor_count == 0 and not memory.is_blocked
fireTurretXAtGround: 1
fireTurretXAtGround_withTarget: self

# 接收端：被小炮命中 → 继续展开
[hiddenAction_spreadRequest]
autoTriggerOnEvent: tookDamage( withTag = "cell_clear" )
requireConditional: if ${verifi2}
alsoTriggerAction: clearCell, unflag
```

### 批量遍历范围内的所有单位：takeResources_searchOnly

要"扫描一片范围内的所有单位，并对每个单位各跑一次动作"时，用 `takeResources_searchOnly` + `takeResources_triggerActionForEach` 做成一个批处理。这是 luke 语里"遍历范围内所有单位"最实用的模式，适合全盘校验、全体结算、批量刷新等。

### 多状态循环切换与计数

**取模循环切换状态**：用一个 `mark` 变量 + 取模实现"空 → A → B → 空"的循环，周期可由设置项动态决定：

```ini
[hiddenAction_flag]
setUnitMemory: mark = (memory.mark + 1) % (2 + select( customTarget1.readUnitMemory( "preferences", type = "bool[]" ).get(4), 1, 0 ))
```

**带校验的计数**：子单位状态变化时发一条带 ±1 增量的消息，控制器累加到一个计数器；发送前先校验边界（如"剩余量 + 增量 >= 0"）防止越界：

```ini
# 子单位端：校验后发送增量
[hiddenAction_receiveFlaggingRequest]
requireConditional: if customTarget1.readUnitMemory( "flags", type = "float" ) + select( memory.mark == 1, 1, -1 ) >= 0 and not memory.cell_clear

# 控制器端：累加
[hiddenAction_flagCount]
autoTriggerOnEvent: newMessage(withTag= "flag_count")
setUnitMemory: flags= memory.flags + eventData("", type= "float")
```

### 完成 / 终止条件的三种判定模式

| 模式       | 做法                                                                                         |
| -------- | ------------------------------------------------------------------------------------------ |
| 计数达标     | 子单位每完成一步发一条消息，控制器累加计数器并与目标值比较，达标即触发结束动作                                                    |
| 事件即时     | 子单位发生关键事件立刻发消息，控制器收到即切终止状态并广播                                                              |
| 全盘扫描逐个校验 | 用 `takeResources_searchOnly` + `takeResources_triggerActionForEach` 扫全盘，逐个单位验证某条件，统计满足数再判定 |

计数达标模式的典型写法——累加后用 `alsoTriggerOrQueueActionConditional` 判断是否达标：

```ini
[hiddenAction_countProgress]
autoTriggerOnEvent: newMessage(withTag="progress")
setUnitMemory: progress= memory.progress + 1
alsoTriggerAction: onComplete
alsoTriggerOrQueueActionConditional: if memory.progress == memory.target
```

### 分数结算与统计柱状图

结束时用嵌套 `select` 一次性算出分数、写进统计数组。把历史记录画成柱状图：每根柱子一个 `decal`，用 `imageScaleY` 表高度（值 / 最大值 * 基准），再叠一条横线表平均值：

```ini
[decal_stats_bar_0]
image: SHARED:white_pixel.png
imageScaleY: memory.stats_score[${bar}] / memory.stats_maxHeight * ${decal_stats_background.imageScaleX} / 2 * 0.8
...
[decal_avgBarHeight]
color: #0000ff
```

本地化定长名表可用 `substring` 查表：把等宽填充的多个译名拼成一长串，按 `索引 * 宽度` 切片取名（英文、中文各用一个宽度常量，因字符宽度不同）：

```ini
showMessageToPlayer: Result: %{substring("OptionA     OptionB     OptionC     ", (memory.index - 1) * ${section.en}, memory.index * ${section.en})}
showMessageToPlayer_zh: 结果：%{substring("甲 乙 丙 ", (memory.index - 1) * ${section.zh}, memory.index * ${section.zh})}
```

### UI 外观：white_pixel 贴花 + 单图多状态

整套 UI 外观（背景、边框、高光、阴影、倒角）可以**不用任何专门的 UI 图**，全靠 `SHARED:white_pixel.png` 一个白点贴花，用 `imageScale*` 拉伸、`color` 上色、`xOffsetAbsolute/yOffsetAbsolute` 定位画出来：

```ini
[decal_background]
layer: BEFOREUI
image: SHARED:white_pixel.png
imageScaleX: memory.cols * memory.size + 25
imageScaleY: memory.rows * memory.size + 75
color: #c0c0c0
```

倒角/斜边用 `dirOffset: 45` 把白点转 45°。

**一张图多状态**：用一张雪碧图配嵌套 `select`，按若干状态变量算出该显示第几帧：

```ini
[decal_visuals]
image: ROOT:path/to/spritesheet.png
frame: """
    select(
        memory.state_a, select( memory.state_b, 12 + select( memory.state_c, 0, 2), memory.neighbor_count),
        select( memory.state_d, 13, memory.mark + 9 )
    )
"""
```

**图层叠加**用 `imageStack` 把多张图叠起来，`stack_indexStart` 按变量选显示哪一层、`frame` 再选该层的帧：

```ini
[decal_button]
imageStack: ROOT:path/to/base.png, ROOT:path/to/overlay_a.png, ROOT:path/to/overlay_b.png
stack_indexStart: """
select( ${cv} "char_a", 1,
select( ${cv} "char_b", 2, 0 ) )
"""
frame: select( memory.game_over, select(memory.defeat, 2, 1), 0)
```

### 七段数码管（多位数字显示）

用一张数字雪碧图（含 11 帧：0-9 + 空）配一个模板，`frame: 值 / 10^位 % 10` 取出第 d 位，多个 decal 各取一位拼成多位数：

```ini
[template_digitals]
@define s= 19
@define d= 0
@define v= memory.my_number
image: ROOT:path/to/digits.png
xOffsetAbsolute: (-${d} * ${s}) + (${b})
total_frames: 11
frame: ${v} / ${10 ^ d} % 10
color: #ff0000
```

不同数字（如计数、计时）共用这个模板，各自覆写 `@define v=` 和位数 `d`；前导零靠每位的 `isVisible` 条件裁掉。

### 按钮系统：displayType / 互斥面板 / 软键盘输入

UI 按钮都是 `[action_*]`：`text/description/iconExtraImage` 管外观，`setUnitMemory` 翻转状态，`sendMessage*` 触发副作用，`displayType` 决定样式（`action` / `infoOnly` / `infoOnlyNoBox` / `rally` / `upgrade` 等）：


```ini
[action_toggle]
displayType: action
text: %{select( memory.buttons[${section.button}], "Back", "Start")}
text_zh: %{select( memory.buttons[${section.button}], "退出", "开始")}
description: Please select an option
description_zh: 请选择
setUnitMemory: buttons[${section.button}]= not memory.buttons[${section.button}]
sendMessageTo: self
sendMessageWithTags: buttonVisible, play_sound
iconExtraImage: ROOT:path/to/icon.png
```

**互斥面板**用两个数组：`buttons[]` 存逻辑状态、`buttonsVisible[]` 存显隐。点开一个面板时广播，控制器遍历所有按钮，只让被点那个可见、其余收起：

```ini
[hiddenAction_buttonVisible_update_iftrue]
requireConditional: if memory.buttons[eventData("", type= "float")]
setUnitMemory: buttonsVisible[memory.buttonVisible_index]= select( eventData("", type= "float") == memory.buttonVisible_index, true, false), ...
```

**软键盘数字输入**：`[action_*]` 每个数字按钮往当前输入项追加一位（`x*10+d`），退格做 `int(x/10)`，还能用 `self.TimeAlive % 1 > 0.5` 做光标 `▌` 闪烁：

```ini
[action_enterDigitals_0]
@define d= 0
setUnitMemory: customValue[(memory.custom_option - 1)]= min(memory.customValue[(memory.custom_option - 1)] * 10 + ${d}, 2147483647)

[action_enterDigitals_backspace]
@define d= ↩
setUnitMemory: customValue[(memory.custom_option - 1)]= int( memory.customValue[(memory.custom_option - 1)] / 10)
```

### 预设配置：@copyFromSection + @define + queueItemAdded

多个"预设"按钮都 `@copyFromSection` 同一个模板，各自用 `@define` 覆写参数；点击时一次 `setUnitMemory` 批量初始化整局，并打上一个 `tags`。控制器监听 `queueItemAdded(withActionTag=...)` 来感知"某个预设被选中了"并启动后续：

```ini
[action_preset_a]
@copyFromSection: template_preset
@define rows= 16
@define cols= 30
@define time= 1200
text: Preset A
text_zh: 预设甲
```

**计时 / 倒计时**：首次触发时用 `startTimer`，把倒计时锚点设成 `self.timeAlive + 时长`，之后比较 `锚点 - self.timeAlive` 得剩余时间。最后几秒让数字闪烁可用 `sin(timeAlive*90)` 取绝对值当 `alpha`：

```ini
alpha: select( memory.playTime - self.timeAlive < 10, max( sin( self.timeAlive * 90 ), -sin( self.timeAlive * 90 )), 1 )
```

### 可切换附属子系统：attachment + convertTo（如语音 / 皮肤）

需要一个可运行时切换的子系统（语音、皮肤、形态）时，给控制器挂一个 `[attachment_*]` 专管它，开局生成一个静音/空占位：

```ini
[attachment_character_voice]
# 反复创建销毁可能带来多余性能开销, 考虑使用单位池
onCreateSpawnUnitOf: cv_null
```

链路：

1. **路由**——任何事件发一条 `play_sound` 带 `key`，控制器把 `voice_key` 写下并转发给附属。
2. **播放**——附属里集中一个 `[template_sound]`：只有 `parent.voice_key == key` 且过了冷却才播 `sounds/${key}.ogg`。
3. **切换**——附属收到 `change_cv`、且 `parent` 的选择变量等于本身标识时 `convertTo: cv_${character}`（用变量拼目标单位名动态变形），再回发一条确认消息：

```ini
[template_character_voice]
autoTriggerOnEvent: newMessage( withTag = "change_cv" )
requireConditional: if parent.readUnitMemory( "voice_character", type = "string" ) == "${character}"
convertTo: cv_${character}
sendMessageTo: parent
sendMessageWithTags: character_changed
```

1. **闭环**——发送端设好选择变量并发 `change_cv`，收到 `character_changed` 回执后再触发后续（如播放新角色的开场白）。

每个变体单位可以写得极薄（只有 `@global` 标识 + 显示名），其余全靠目录级 `all-units.template` 注入。空占位单位覆写成不发声、跳过贴花：

```ini
[core]
@global character: null
[template_sound]
playSoundToPlayer: IGNORE
[decal_character]
@copyFrom_skipThisSection: true
```

### 变体单位：copyFrom 整个单位再覆写

要做一个"基础单位的变体"（如教程版、精简版），直接 `copyFrom` 整个基础单位文件，再覆写/隐藏个别节：

```ini
copyFrom: myunit.ini
name: myunit_variant
[action_someButton]
isVisible: false
```

### 分页 UI：imageStack + stack_indexStart 读变量

多页帮助/图鉴：一个按钮自增页码变量并通知配图附属；配图 decal 的 `imageStack` 装入各页图，`stack_indexStart` 读页码变量选图：

```ini
[decal_help]
imageStack: ROOT:path/to/page1.png, ROOT:path/to/page2.png, ROOT:path/to/page3.png, ROOT:path/to/page4.png
stack_indexStart: customTarget1.readUnitMemory( "page", type = "float" )
```

### 多人探测

真正的多人同步很难（要保证所有逻辑确定性、所有随机数同序列）。最低限度可以先做"探测"：`completeAndActive` 时用 `numberOfUnitsInAllTeams(withTag=...)` 判断场上是否有别的玩家实例，据此提示或禁用某些功能：

```ini
setUnitMemory: multiplayers = numberOfUnitsInAllTeams( withTag = "mycontroller" ) > 1
```

### 性能护栏

- 全局节流：前述 `autoTriggerCheckRate: every8frames` 把自动触发频率降下来。
- 限制实例数：用 `placementRule` 限制地图上只能放 N 个本模组实例，超量直接报错，避免大量单位拖垮性能：

```ini
[placementRule_singleton]
maxCount: 0
searchTags: ${core.name}
searchDistance: Infinity
cannotPlaceMessage: Too many instances might affect performance.
cannotPlaceMessage_zh: 实例过多会影响性能。
```

### 坑（pitfalls）

- **`+ 1 % N` 运算符优先级 bug**：想让计数器回绕写成 `counter = memory.counter + 1 % ${N}` 是常见错误。按标准优先级 `%` 高于 `+`，它实际等于 `counter + (1 % N) = counter + 1`，**模运算形同虚设、永不回绕**。要回绕必须显式加括号：`(counter + 1) % N`。
- **节名 / 键名区分大小写**：luke 语的节名、键名严格区分大小写（例如 `ShifTright` 和 `ShiftRight` 是两个完全不同的名字）。`${...}` 引用或 `alsoTriggerAction` 里拼错**不会报错，只会静默失效**——排查"动作莫名其妙没跑"时首先核对拼写。
- **没有真 else（1.16 之前）**：旧版本没有 if/else，全靠 `select(cond, a, b)` 和多个带互补 `requireConditional` 的动作模拟。新版本会引入官方 if/else，改代码前先确认目标引擎版本。
- **宏不能嵌套**：`@define` 宏不支持"宏套宏"，需要嵌套时只能复制粘贴成两份几乎一样的模板。
- **空数组 length**：数组为空时 `length` 行为特殊，务必自己维护计数器下标，并在删元素后 `shrinkArrays`。
- **广播要配来源校验**：面积伤害广播会打到范围内所有同类单位，不加 `${verifi}` 来源校验，多实例/多局会串台。
- **消息频道与炮弹频道同名**：`newMessage` 的 tag 和 `tookDamage` 的 tag 可以同名但是两套机制（点对点 vs 空间广播），命名时注意区分、心里清楚在用哪套。
- **隐形继承**：目录级 `all-units.template` 会自动套给同目录及子目录所有单位，排查"多出来的键"要先翻各级目录的这个文件。
- **占位 stub**：未完成的功能（空 `showMessageToPlayer`、`isVisible:false` 的半成品按钮）要在 `description` 明确标注"未实现"，别让占位内容随版本误发。

### 实战范式：非战斗模组的完整设计骨架（通用化示例）

> 本节把"一个用引擎做非战斗 / 小游戏模组"从零到成品的完整骨架，用**中性化、可直接改写复用**的例子串一遍。所有节名、变量名、资源名都是通用的占位命名（`mycontroller` / `mycell` / `mymod`），**不含任何特定模组的私有命名或业务规则**——你可以原样照抄结构，把 `my*` 前缀换成自己的名字。
>
> 这些手法的**思想**来自社区里若干成熟作品（前辈们在各类非战斗 UI 小游戏里趟出来的路），但下文是**重写过的通用范式**，不是任何源码的拷贝。思想可以学，代码请自己写。

> ## ⚠️ 阅读须知：什么是"通用规律"，什么是"特定做法"
>
> 引擎老玩家高手们的代码里，混着两类东西：一类是**今天依然成立的通用规律**，另一类是**当年为绕引擎限制而生的特殊技巧**（现在多半已有更好的官方写法）。照抄后者会被误导——**照搬还会让 Agent 学去某位作者的个人味道**。
>
> | 级别               | 含义                    | 怎么用                   |
> | ---------------- | --------------------- | --------------------- |
> | 🟢 **通用规律**      | 与具体模组无关、今天依然成立的定式     | 可放心借鉴、照搬结构            |
> | 🟡 **可用但有更优解**   | 思路对，但今天可能有更简单/更省的做法   | 理解思路，优先找更省的做法         |
> | 🔴 **已过时 / 勿照搬** | 绕早期引擎限制的 hack，官方已提供替代 | **只用官方新写法**，别学这类 hack |
>
> 下文每个片段都标了级别。**引用时务必带着级别，别把 🔴 当 🟢。**

### 🟢 ① 画布基线（`all-units.template`） —— 零价零血、隐形、关碰撞、只认 8 帧轮询：

```ini
[core]
displayDescription:

price:0
maxHp:0
mass:2147483467          # 质量哨兵：大到推不动

radius:10

disableDeathOnZeroHp: true
strictLevel: 1

autoTriggerCooldownTime: 1
autoTriggerCooldownTime_allowDangerousHighCPU:true
autoTriggerCheckRate: every8frames

disableAllUnitCollisions: true

[graphics]
image: SHARED:blank.png

showSelectionIndicator:false
showHealthBar:false
showEnergyBar:false
showQueueBar:false
showShieldBar:false
[attack]
canAttack:false
maxAttackRange:0
[movement]
movementType:NONE
moveSpeed: 0
maxTurnSpeed: 0

joinsGroupFormations: false

[template_m]              # 所有 UI 按钮的公共基模板
alwaysSinglePress:true
allowMultipleInQueue:false
canPlayerCancel:false

buildSpeed:0

isVisible: true
```

> 🟢 **这是通用定式**：零价零血 + 隐形 + 关碰撞 + 低频轮询，是把单位当"画布"的基线。数值哨兵 `2147483467`、`every8frames` 的用法可直接沿用。

### 🟡 ② 格子内存声明 + 初始化（`mycell.ini`） —— 每个格子用 `@memory` 存自己的状态，`neighbors: unit[]` 预存 8 个邻居的绝对位置标记：

```ini
[core]
name: mycell
showInEditor: false
tags: mycell
canOnlyBeAttackedByUnitsWithTags: mycontroller
isUnselectable: true
isUnselectableAsTarget: false
createOnAggressiveTeam: true

@memory marked: bool
@memory revealed: bool
@memory scan_dir: float
@memory neighbor_hits: float
@memory triggered: bool
@memory cell_index: float
@memory cell_pos: unit
@memory misflagged: bool
@memory neighbors: unit[]
@memory flag_state: float
@memory flag_count: float
@memory scan_index: float
@memory customTarget1: unit

@global cell_size: 24
@global max_field: 50

@global is_owner: eventSource == select( customTarget1 == null, memory.customTarget1, customTarget1)
@global same_owner: eventSource.customTarget1 == customTarget1

[hiddenAction_init]
@global g_cell: customTarget1.readUnitMemory("cell_size", type= "float")
# g_cell = 当前格子边长
autoTriggerOnEvent: created

setBodyRotation: -90
setUnitMemory: """
cell_pos= createMarker((self.x - customTarget1.x - ${g_cell}) / ${g_cell}, (self.y - customTarget1.y - ${g_cell}) / ${g_cell}),
neighbors[0]= getOffsetAbsolute(x= -${g_cell}, y= -${g_cell}),
neighbors[1]= getOffsetAbsolute(y= -${g_cell}),
neighbors[2]= getOffsetAbsolute(x= ${g_cell}, y= -${g_cell}),
neighbors[3]= getOffsetAbsolute(x= ${g_cell}),
neighbors[4]= getOffsetAbsolute(x= ${g_cell}, y= ${g_cell}),
neighbors[5]= getOffsetAbsolute(y= ${g_cell}),
neighbors[6]= getOffsetAbsolute(x= -${g_cell}, y= ${g_cell}),
neighbors[7]= getOffsetAbsolute(x= -${g_cell}),
customTarget1= customTarget1
"""
```

> 🟡 **思路好，但可简化**：`createMarker` / `getOffsetAbsolute` 预存 8 个邻居是省运行时计算的好办法。规模小（格子数不多）时，也可以不预存、用到时现算，代码更短。

### 🟡 ③ 遍历 8 邻居统计命中数（luke 语的 for 循环） —— `alsoTriggerActionRepeat: 8` 重复动作，用 `memory.scan_dir` 当下标：

```ini
[hiddenAction_scanNeighbors]
buildSpeed: 1
setUnitMemory: scan_dir= 0
alsoTriggerAction: scanNeighborsStep
alsoTriggerActionRepeat: 8
[hiddenAction_scanNeighborsStep]
setUnitMemory: """
neighbor_hits = memory.neighbor_hits + select(
    memory.neighbors[memory.scan_dir].nearestUnit( withTag= "mycell", withinRange = 1 ).readUnitMemory( "marked", type= "bool" ), 1, 0
    ),
scan_dir = memory.scan_dir + 1
"""
```

> 🟡 **能用，但今天有更省的写法**：用 `alsoTriggerActionRepeat: N` 当 for 循环是有效手段；若能在一次动作里用 `takeResources_*_triggerActionForEach` 扫过去，会更简洁。

### 🟡 ④ 洪水填充（区域连锁展开） —— 已揭开的格子若周围标记数 == 命中数，就向 8 邻居广播 `do_clear` 连锁展开：

```ini
[hiddenAction_areaOpen]
requireConditional: if memory.revealed and customTarget1.readUnitMemory( "prefs", type= "bool[]" ).get(0)
setUnitMemory: scan_dir = 0, flag_count = 0, scan_index = 0
alsoTriggerAction: countFlags
alsoTriggerActionRepeat: 8

[hiddenAction_countFlags]
setUnitMemory: """
flag_count= memory.flag_count + select(
    memory.neighbors[memory.scan_dir].nearestUnit( withTag= "mycell", withinRange = 1 ).readUnitMemory( "flag_state", type= "float" ) == 1, 1, 0
    ),
scan_dir= memory.scan_dir + 1
"""
alsoTriggerAction: openNeighbor
alsoTriggerActionRepeat: 8
alsoTriggerOrQueueActionConditional: if memory.scan_dir == 8 and memory.flag_count == memory.neighbor_hits

[hiddenAction_openNeighbor]
sendMessageTo: memory.neighbors[memory.scan_index].nearestUnit( withTag= "mycell", withinRange = 1 )
sendMessageWithTags: do_clear
alsoTriggerAction: openNeighborStep
[hiddenAction_openNeighborStep]
setUnitMemory: scan_index= memory.scan_index + 1
```

> 🟡 **链式广播思想通用**；本例把"计数 + 广播"拆成多个动作，是因为要逐邻居处理。动作数能合并就合并。

### 🟢 ⑤ 单图多帧状态机（`[decal_mycell_vis]`） —— 一张 `cell_vis.png` 靠 `frame:` 表达式在"揭开/标记/错标/命中"之间切帧：

```ini
[decal_mycell_vis]
layer: BEFOREUI
image: res/ui/cell_vis.png
isVisible: true
frame: """
    select(
        memory.revealed, select( memory.triggered, 12 + select( memory.marked, 0, 2), memory.neighbor_hits),
        select( memory.misflagged, 13, memory.flag_state + 9 )
    )
"""
frame_width: 24
frame_height: 24
```


> 🟢 **通用且省资源**：一张图靠 `frame:` 表达式切帧，比多图切换更高效，值得作为定式。

### 🟢 ⑥ 七段数码管基模板 + 多位展开 —— `@define s/d/v/b` 控制间距/位序/变量/基准，子节靠 `@copyFromSection` 复制并只改 `d`：

```ini
[template_digit]
# spacing 间距
@define s= 19
# digit 位数下标
@define d= 0
# variable 显示的变量
@define v= memory.score
# base 基准坐标
@define b= 0
layer: BEFOREUI
image: res/ui/digits.png
xOffsetAbsolute: (-${d} * ${s}) + (${b})
yOffsetAbsolute: ${bg} - 10
total_frames: 11
frame: ${v} / ${10 ^ d} % 10
color: #ff0000
alwaysStartDirAtZero: true

[decal_score_0]
@copyFromSection: template_digit
isVisible: if (${d} < 2 or length(str(memory.max_score)) > ${d}) and memory.rows > 0
@define d= 0
@define b= memory.size / 2 + 19 * max(1.5, (length(str(memory.max_score)) - 0.5))
[decal_score_1]
@copyFromSection: decal_score_0
@define d= 1
```

> 🟢 **数码管标准做法**：`@copyFromSection` + 每份只改 `@define d`，是"一位一节"展开的正统写法。

### 🟢 ⑦ 统计柱状图（`decal_bar_*`） —— 一整排柱子靠 `@define bar=N` 复制 10 份，高度 = 数值 / 历史最高 * 基准：

```ini
[decal_bar_0]
@define bar= 0
layer: BEFOREUI
isVisible: if memory.panel_open[${action_stats.button}] and memory.panel_vis[${action_stats.button}] and memory.scores[${bar}] > 0
image: SHARED:white_pixel.png
imageScaleX: 8
imageScaleY: memory.scores[${bar}] / memory.max_height * ${decal_bar_bg.imageScaleX} / 2 * 0.8
xOffsetAbsolute: ${bar} * ${section.imageScaleX} * 2 - ${decal_bar_bg.imageScaleX}
yOffsetAbsolute: -memory.scores[${bar}] / memory.max_height * ${decal_bar_bg.imageScaleX} / 4 * 0.8 + ${decal_bar_bg.imageScaleX} / 6
alwaysStartDirAtZero: true
[decal_bar_1]
@copyFromSection: decal_bar_0
@define bar= 1
```

> 🟢 **通用**：`@define bar` 复制 N 根柱子，是数据可视化的常用结构。

### 🟡 ⑧ 计分公式是"业务规则"，不是"通用公式"

计分/评分这类逻辑，**写法通用（一串 `setUnitMemory` 表达式），但具体公式完全属于你自己这款游戏**。别把别人的权重、难度系数当模板抄。骨架长这样：

```ini
[hiddenAction_record_stats]
setUnitMemory: """
games = memory.games + 1,
last_score[memory.games]= memory.this_score,
avg_score= (memory.avg_score * (games - 1) + memory.this_score) / games,
best= max(memory.best, memory.this_score),
this_score= 0
"""
```

> 🟡 **只借结构，不借公式**：`x[a]= y` 这种"按局数存数组 + 增量更新均值"的写法可以学；`this_score` 具体怎么算，是你自己的游戏规则。

### 🟢 ⑨ 性能护栏 —— 用 `[placementRule_*]` 限制同类单位数量，防止玩家刷爆影响性能：

```ini
[placementRule_fieldLimited]
maxCount: 0
searchTags: ${core.name}
searchDistance: Infinity
cannotPlaceMessage: Too many fields might affect the game performance.
cannotPlaceMessage_zh: 太多区域会影响游戏性能。
```

> 🟢 **通用且推荐**：用 `[placementRule_*]` + `maxCount` 限数量，是官方提供的性能护栏，放心用。

**几条来自实战的宝贵经验（通用教训）：**

- **宏不能嵌套**：luke 语不支持下层宏引用上层宏，需要复用只能复制子节 + `@copyFromSection`。
- **早期没有官方 if/else 时，人们用 `select` + 互补条件模拟分支**；新版引擎若有官方 if/else，**一律用官方的**，别无脑沿用模拟写法。
- **早期没有 `abs()`**，人们写 `max( sin(x), -sin(x) )` 取绝对值；新版有 `abs()` 就直接用。
- **反复创建销毁单位有性能开销**：高频生成/销毁的附属单位，考虑用"单位池"复用。

### ⑩ 两个值得知道的"进阶手法"（学思想，别照搬）

**(a) 🔴 用 `takeResources` 手搓 if/else（已过时，勿在新版照搬）** —— 这是早期引擎没有官方 if/else 时的绕行技巧：借 `takeResources_includeReference` 把条件表达式当"目标"传入，命中/未命中分别触发 `_triggerActionIfAnyCollected` / `_triggerActionIfNoneCollected`，配合 `@define` 注入 if / else 分支。**新版引擎请直接用官方 if/else，不要学这个 hack：**

```ini
[template_if_else]
@define condition:"""

"""
@define if:
@define else:
@define target: self

takeResources_searchOnly: true
takeResources_includeReference: select(${condition}, ${target}, ${target})
takeResources_triggerActionIfAnyCollected: ${if}
takeResources_triggerActionIfNoneCollected: ${else}
```

**(b) 🟡 带衰减的"掉血"血条** —— 用一个显示用血量 `disp_hp` 每帧向真实血量衰减，`decal` 画两层：残影 + 实血，实现"受伤瞬间掉一截、慢慢褪去"的观感（思路通用，衰减系数自调）：

```ini
# 每帧让显示血量向真实血量衰减
updateUnitMemory: disp_hp= max( self.hp, memory.disp_hp - 0.5 - ((memory.marked_hp - self.hp) / 50)), marked_hp= select( int(memory.disp_hp + 0.5) == int(self.hp + 0.5), self.hp, memory.marked_hp)
updateUnitMemoryRate: 1

[decal_hp_damage_fade]
layer: BEFOREUI
isVisible: if memory.disp_hp > self.hp
image: SHARED:white_pixel.png
imageScale: 2
imageScaleX: memory.disp_hp / self.maxHp * 20
basePosition: getOffsetAbsolute(x= (1 - (memory.disp_hp / self.maxHp)) * -20, y= 20)
alpha: (memory.disp_hp - self.hp) / (memory.marked_hp - self.hp)
color: #e00000
```

> 🟡 **衰减思路通用**，但"每帧减多少、多久追上"要按你的手感调，别照抄系数。

**两条被反复验证的通用教训：**

- **局部覆写优先于 `copyFrom` 父层**：想用父层的值却被覆盖时，先检查是不是局部写死了一份。
- **静态颜色只能逐个手填**（如用 `@global` 定义颜色常量），引擎暂不支持动态计算颜色——这是限制，不是用法问题。

## 5. 双语、UI 展示与模组元数据

许多 RW 模组都遵循一条约定：**所有玩家可见文本都要中英双语**。无论你的项目是否强制，把双语当默认是最稳妥的做法。审校时要同时防两类问题——"漏翻"(只写了一侧语言)和"误报"(把本就该单侧的语言中立标签当成漏翻)。本章覆盖双语文本的所有产生方式、各类 UI 展示键，以及 `mod-info.txt` 元数据里那个"后缀方向相反"的陷阱。

动手前记住一条可执行约束：改任何一行可见文本，先用 `Grep` 确认它对应的 `_zh`(或在 `mod-info.txt` 里是 `_en`)姊妹键是否存在，再决定怎么改。

### 双语约定：四对键两侧都写

通行约定要求下列四对键必须两侧都写，不要只加一种语言：

- `displayText` / `displayText_zh`
- `text` / `text_zh`
- `displayName` / `displayName_zh`
- `displayDescription` / `displayDescription_zh`

记住后缀方向：在单位/行动/资源文件里，**基键 = 英文，`_zh` = 中文**。唯一的例外是 `mod-info.txt`(见本章末尾)，那里方向是反的。

### 四类可见文本及其对应键

不同 UI 对象用不同的键族，不能混用。单位名用 `displayText`，行动按钮用 `text`——两者分属不同键。

| 场景      | 名称键                                              | 说明/提示键                                         | 载体节                   |
| ------- | ------------------------------------------------ | ---------------------------------------------- | --------------------- |
| 单位身份    | `displayText` / `displayText_zh`                 | `displayDescription` / `displayDescription_zh` | `[core]`              |
| 行动按钮    | `text` / `text_zh`                               | `description` / `description_zh`               | `[action_x]`          |
| 资源(HUD) | `displayName` / `displayName_zh`                 | 另有一组 `display*` 展示键                            | `[global_resource_x]` |
| 运行时消息   | `showMessageToPlayer` / `showMessageToPlayer_zh` | —                                              | `[hiddenAction_x]` 等  |

### 单位名与说明：`displayText` / `displayDescription`

基键英文、`_zh` 中文，写在单位的 `[core]` 节：

```ini
displayText: My Unit
displayText_zh: 我的单位

displayDescription: Scout Vehicle
displayDescription_zh: 侦察型单位。\n便宜又快，开局即可出击……
```

英文说明常用 `${...}` 在**载入期**插值出数值，中文侧偏风味描述——两侧内容不必字面对等：

```ini
displayDescription: Detects units within range.\nRange is ${my_range}, consumes ${my_power} power per second.
displayDescription_zh: 预警系统。\n中等距离内预警敌方动向，造价低廉……
```

对应的 `@global` 必须声明：

```ini
@global my_range = 1000
@global my_power = 0.8
```

两个坑：

- `${my_range}` / `${my_power}` 是载入期插值，引用的 `@global` 必须先声明。**全局名要原样照抄**——哪怕源头把名字拼错了(例如本该 `power_consume` 却写成 `power_comsume`)，所有引用处也必须沿用同样的错拼，否则插值找不到源会报错。
- 若同一模板被活体单位和它的残骸(wreckage)共用，`${...}` 要保证**两侧都能解析**。改动这些 `@global` 时别让某一方缺定义，否则残骸侧展示会出错。

角色/语音类单位同样遵守这套双语，介绍文里可混入原文+译文+画师署名：

```ini
displayText: My Character 
displayText_zh: 我的角色
displayDescription: Introduction: ...\n(Art by Someone)
displayDescription_zh: 开场白：……\n（画师：某人）
```

注意上例 `displayText: My Character ` 结尾多一个空格，与 `_zh` 不对称——这类格式小瑕疵在复核英文串时留意即可(尾随空格、半角/全角标点)。

### 行动按钮：`text` / `description`

写在 `[action_x]` 节：

```ini
text: Stop
text_zh: %{select( memory.inactivate, "开始", "停止")}

description:
description_zh: 当资源不足以支撑建造时，可强制停止。
```

同一按钮也可同时给 `text` 和 `description` 两对双语：

```ini
text: %{select( memory.buttons[${section.button}], "Back", "Start")}
text_zh: %{select( memory.buttons[${section.button}], "退出", "开始")}
description: Please select an option
description_zh: 请选择一个选项
```

### 资源 HUD 展示键

资源名用 `displayName` / `displayName_zh`，另配一整组展示键，写在 `[global_resource_x]` 节：

```ini
[global_resource_gold]
priority: 1
displayPos: 0

displayName: Gold
displayName_zh: 金币
displayTextPrefix: 
displayNameShort: G

displayWhenZero: true
displayRoundedDown: true

iconImage: ROOT:path/to/icon.png
displayColor: #666680

appendResourceInHUD: gold_uplimit
```

资源还可带 `displayTextPrefix` / `displayTextPostfix`(含 `_zh`)做前后缀：

```ini
displayTextPrefix: （

displayTextPostfix: 
displayTextPostfix_zh: ）你在浪费资源。
```

### 动态 `%{...}` 双语：两侧表达式一致，只本地化尾部标签

运行时文本用 `%{...}`。双语做法是**两侧用完全相同的表达式，仅把末尾的单位标签换成本地语言**：

```ini
text: +%{select(self.isOverwater(), "${rate_water}", str(int(${rate_land})) + "." + str(int(${rate_land} * 10 % 10)))} E
text_zh: +%{select(self.isOverwater(), "${rate_water}", str(int(${rate_land})) + "." + str(int(${rate_land} * 10 % 10)))} 能量
```

两侧表达式逐字相同，差别只在结尾的 `E` ↔ `能量`。切换类标签则相反——英文侧可能是静态词，中文侧用 `select()` 二选一文案(见上面 `Stop` ↔ `开始/停止`)。

### 定宽 substring 本地化

多个译名**等宽填充**拼成一长串，再按 `索引 * 宽度` 切片取出。英文和中文的字符宽度不同，所以两侧各用一个宽度常量。有两种写法，区别在常量是"节内键"还是"`@define` 宏"：

写法一——节内键，用 `${section.xxx}` 引用：

```ini
en= 10
zh= 2
...
showMessageToPlayer: Mode: %{substring("Easy      Hard      ", (memory.mode - 1) * ${section.en}, memory.mode * ${section.en})}
showMessageToPlayer_zh: 模式：%{substring("简单困难", (memory.mode - 1) * ${section.zh}, memory.mode * ${section.zh})}
```

写法二——`@define` 宏，用 `${xxx}` 引用：

```ini
@define en= 6
@define zh= 2
...
text: Sort: %{substring( "Name  Score ", memory.sortMode * ${en}, memory.sortMode * ${en} + ${en})}
text_zh: 按%{substring( "名称分数", memory.sortMode * ${zh}, memory.sortMode * ${zh} + ${zh})}排序
```

(两种 start/end 写法等价：`(n-1)*w .. n*w` 与 `n*w .. n*w+w` 都是取第 n 段 `[start, end)`。)

坑：填充宽度与译名字符数必须严格对齐(英文 `Easy` + 6 空格 = 10，中文 `简单` = 2)。新增一个选项，要同步往两条填充串里按各自宽度补齐，否则切片会错位串词。

### 运行时弹给玩家的消息

`showMessageToPlayer` / `showMessageToPlayer_zh` 成对：

```ini
showMessageToPlayer: Your score: %{memory.game_score}
showMessageToPlayer_zh: 你的分数：%{memory.game_score}
```

### 双语的两种"非直写"入口(容易被漏查)

除了直接写 `text`/`text_zh`，还有两种 UI 文本不在按钮本身：

1. **从被引用单位带入。** 用 `textAddUnitName` / `descriptionAddFromUnit` / `unitShownInUI` / `guiBuildUnit` 把目标单位的 `displayText(_zh)` / `displayDescription(_zh)` 拉进按钮：

```ini
[action_option]
@copyFromSection: template_
textAddUnitName: myqueueunit
guiBuildUnit: ${section.textAddUnitName}
unitShownInUI: ${section.textAddUnitName}
descriptionAddFromUnit: ${section.textAddUnitName}
descriptionAddUnitStats: ${section.textAddUnitName}
displayType: queueUnit
```

**这类按钮里看不到 `text_zh` 是正常的**——它的双语性来自被引用单位，别误判为缺翻译；真要改文案，去改那个被引用单位的 `displayText(_zh)` / `displayDescription(_zh)`。

1. **父模板框架 + 子项 `@define` 文案。** 开关状态词在父模板集中双语化，具体条目说明由子项用 `@define` 两侧注入。父模板：

```ini
description: [%{select( memory.options[${section.option}], "ON", "OFF")}]\n${description}
description_zh: [%{select( memory.options[${section.option}], "开启", "关闭")}]\n${description_zh}
```

子项提供 `${description}` / `${description_zh}`：

```ini
@define description: Toggle this option to change the behavior.
@define description_zh: 切换此选项以改变行为。
```

新增条目时，`@define description` 和 `@define description_zh` 两侧都要给。


### 合法例外：语言中立标签不要误报

内容为纯数字/符号(语言中立)的 `text` 可以只写一侧、无 `text_zh`，且父模板本身也可以不提供 `text_zh` 兜底。这是**正确写法**，不是违例：

```ini
text: ${d}                                              # 数字键 0-9，只有 text
text: %{memory.customValue[${section.o - 1}]}%{select(…, "▌", "")}   # 自定义数值显示
```

但相邻的文字标签必须双语：

```ini
text: Width:
text_zh: 宽：
```

审校规则：`${d}`、纯数字、`▌`/`↩` 这类符号单侧合法；只要含可读单词(`Width:` / `Flag` / `New Game`)就必须成对。

### 真实违例(反面教材，别照抄，发现要修)

常见违例模式：

- **中文塞进英文基键、缺 `_zh`。** 例如 `text: 隐身` 而没有 `text_zh`。
- **同上，还带内联 `select()`。** 例如 `text: 干扰器(%{ select( self.tags(includes="my_tag"), "关闭", "启动") })` 却无 `text_zh`。注意 `self.tags(includes=...)` 是引擎函数，保留原样。
- **占位串未翻译就随版本发布。** 英文基键里残留 `text: - -` / `description: - -` 之类占位。
- **英文串拼写错误。** 例如把 `character` 误拼成 `csharacter`，发布前应复核英文拼写。

违例示例：

```ini
[action_myaction]
@copyFromSection: template_

text: 隐身          # 违例：中文塞进英文基键，且无 text_zh

displayType: rally
```

坑：判断一行是否"生效代码"时，要看它是否落在 `"""` 块注释内——注释块里的 `text:` 不生效，注释块**之前/之外**的才算生效代码。别把注释里的示例当成违例，也别漏掉伪装在注释外的违例。

### UI 展示样式：`displayType`

`displayType` 决定行动在 UI 的呈现方式。**完整合法取值只有下面 9 个（别臆造引擎不支持的值）**：

| 取值                  | 颜色 / 样式 | 使用场景                      |
| ------------------- | ------- | ------------------------- |
| `none`              | 无标记     | 默认                        |
| `rally`             | 白色 R    | 集结点类按钮                    |
| `upgrade`           | 蓝色 U    | 升级 / 退格类按钮                |
| `queueUnit`         | 绿色      | 建造队列按钮（配合 `guiBuildUnit`） |
| `building`          | 绿色      | 建筑类                       |
| `action`            | 蓝色      | 普通可点击按钮                   |
| `infoOnly`          | 灰色框     | 纯信息展示（有框）                 |
| `infoOnlyNoBox`     | 灰色无框    | 纯信息展示（无框）                 |
| `infoOnlyStockpile` | 灰色      | 纯信息展示，按资源算「还能触发几次」        |

> `infoOnlyStockpile` 配套 `displayRemainingStockpile: true`，显示为「剩余可触发次数」而非固定文本。

### UI 可见性 / 状态 / 图标键

这些键用 `memory` 数组驱动显隐：

```ini
pos: ${section.button}                                      # 布局位置
isVisible: if memory.mode == 0 and memory.buttonsVisible[${section.button}]
iconExtraImage: path/to/ui/icon.png
iconExtraColor: #ffffff
iconExtraIsVisible: if not memory.buttons[${section.button}]
```

另有 `isActive: if …`、`isGuiBlinking: if …` 等条件键。`iconExtraImage` 等 `ROOT:` 以外、直接写磁盘相对路径的资源，须在磁盘上真实存在，否则图标空缺。

> **UI 显示单位的两种入口**：`unitShownInUI: <单位名或单位引用>` 用某单位当按钮图标（可配 `unitShownInUIWithHpBar` / `unitShownInUIWithProgressBar` 加血条 / 进度条）；`guiBuildUnit: <单位名>` 把图标和鼠标指针改成「正在建造该单位」的形态，受地形影响，也能为 action 或路径点提供坐标。

### 模组元数据：`mod-info.txt`

`[mod]` 节的典型键序：`title` → `description`(`"""多行"""`) → `description_en`(`"""多行"""`) → `thumbnail` → `minVersion`。

**后缀方向在这里是反的**：与单位文件相反，`mod-info.txt` 里**基键 `description` = 中文，`description_en` 才是英文**。`_en` 后缀几乎只出现在 `mod-info.txt` 的 `description_en`；单位/行动/资源文件一律用 `_zh`、不用 `_en`。改 mod-info 前务必认清方向，别把英文写进 `description`。

```ini
[mod]
title: 我的模组  |  My Mod 1.0
description:"""
\n- 作者：作者名
...
"""
description_en: """
\n- Author: Author Name
...
"""
thumbnail: thumbnail.png
minVersion: v1.15
```

`title` 是单条非键化字符串，常内嵌版本号。两种常见风格：

- 中英两名用 `|` 并排：`title: 我的模组  |  My Mod 1.0`
- 只写英文名：`title: My Mod v0.1.3(20260925)`

`tags` 是按逗号分隔的标签串（别名分隔符用 `,` 或空格都见得到），供 Steam 展示与检索用：

```ini
tags: MyMod,Units,Maps,Starting Units,Replacing Units
```

可选的 `[music]` 节(没有就不写)：

```ini
[music]
sourceFolder: sounds/music
whenUsingUnitsFromThisMod_playExclusively: true
addToNormalPlaylist: true
```

- `sourceFolder`：填文件夹路径（仅支持 `.ogg` 或 `.wav`；手机端任意音频都能播），游戏会播放该文件夹内音乐。
- `whenUsingUnitsFromThisMod_playExclusively: true`：用了本模组单位时，**只**播该文件夹内的曲目。
- `addToNormalPlaylist: true`：把该目录下的曲目**追加**进默认播放列表。

坑：`thumbnail` 指向的图必须在模组根目录真实存在，别留悬空引用——从别的模组复制 `mod-info.txt` 时很容易遗留一个指向不存在图片的 `thumbnail`。

> `description` 的写法有两种真实变体：`"""多行"""` 块（缩进对齐、去换行符），或**单行内联 `\n`**（如 `description: 第一行\n第二行`）。两种都能用，照所在工程既有写法走。

### 版本串格式(多格式并存，别硬套单一模板)

RW 生态里不存在单一统一的版本串格式，实际多种并存。唯一的恒定点：**若带日期，恒为紧跟版本号的 `(YYYYMMDD)`**。几种常见风格：

| 风格                 | 格式                          | 示例                      |
| ------------------ | --------------------------- | ----------------------- |
| 点分带 `v`            | `v<主>.<次>.<修>(YYYYMMDD)`    | `v0.1.3(20260925)`      |
| 省略 PATCH           | `v<主>.<次>(YYYYMMDD)`        | `v0.1(20260822)`        |
| 带 `-release` 无 `v` | `<主>.<次>-release(YYYYMMDD)` | `1.0-release(20251019)` |
| 标题里甚至不带日期          | `<主>.<次>-release`           | `My Mod 1.0-release`    |

同一模组内部沿用它自己那套，别跨模组套格式。

### 更新日志(changelog)

两种常见放法：

- **独立 log 文件。** 顶部一个标题，每版一节 `版本变化 #N v…(日期)`，其下分 `平衡：` / `特性：` / `修复：` 等小节；条目可缩进写 `旧值 -> 新值`。例如：
  ```
  ==我的模组 更新日志==

  版本变化 #1 v0.1(20260822)

  平衡：

  某单位
      收益 4 -> 1
  ```
- **内嵌在 `mod-info.txt`。** 把中文 changelog 放进 `description`、英文放进 `description_en`，不另开 log 文件。

坑：

- 内嵌 changelog 两侧内容量常**不对齐**(英文版漏了中文版某段，或某段被整行 `#` 注释掉而中英都没真正发布)。做元数据双语审校时别默认两侧等量。
- 独立 log 文件可能**落后于 `mod-info.txt` 的版本号**(日志没补齐到最新版)。

写日志的硬约束：不要用占位内容去推进 `mod-info.txt` / log 的版本号，只在改动真实、面向玩家时才更新版本与日志；若有意跳过，要说明原因。

### 速查清单

- 改任一可见文本：先确认 `_zh`(单位/行动/资源文件)或 `_en`(仅 `mod-info.txt`)姊妹键存在且同步更新。
- 单位用 `displayText`/`displayDescription`；行动用 `text`/`description`；资源用 `displayName`；运行时弹窗用 `showMessageToPlayer`——不要混。
- 单位/行动/资源：基键=英文、`_zh`=中文；**`mod-info.txt`：基键=中文、`_en`=英文**(方向相反)。
- `%{...}` 双语：两侧表达式保持一致，只换尾部语言标签；定宽 `substring` 两侧填充宽度要各自对齐译名。
- 看到按钮没 `text_zh` 先分三种情况判断：语言中立标签(合法)、靠 `textAddUnitName`/`descriptionAddFromUnit` 从单位带入(合法)、还是真漏翻(违例)。
- `${...}` 载入期插值的 `@global` 必须声明、拼写照抄(含源头的既有错拼)，活体与残骸都要能解析。
- 版本串按各模组自己的格式写；日志不要填占位内容。

## 6. 进阶技法示例库

本章收录一批**自包含的进阶技法**——每个把一个高阶机制拆成最小可参考形态。核心价值是示范几类高频手法：**贴花即渲染层、标记与偏移、数组 + `thisActionIndex` 遍历、`takeResources_*` 扫描、`self.timeAlive` 驱动动画**。

> 用法提醒：这些是**技法示例**，不是即插即用成品。移植前先按第 8 章核实用到的每个函数名，并按第 7 章验证 `${}` / `"""` 平衡。

### 6.1 概率变身（随机 `convertTo`）

`rnd(0, N.99)` 取随机数、`int()` 取整当分支下标，向自己广播一条消息，再用 N 个 `[hiddenAction_result*]` 各自 `requireConditional: if int(memory.result)==order` 命中其一执行 `convertTo`。靠 `@define` + `@copyFromSection` 批量展开分支：

```ini
[action_switch]
@define total_units= 2        # 能转换成几个就写几
sendMessageTo: self
sendMessageWithTags: switch
setUnitMemory: result= rnd(0, ${total_units}.99)

[hiddenAction_result]
@define unit: myunit_a
@define order: 0
autoTriggerOnEvent: newMessage(withTag= "switch")
requireConditional: if int(memory.result) == ${order}
convertTo: ${unit}

[hiddenAction_result_1]
@copyFromSection: hiddenAction_result
@define unit: myunit_b
@define order: 1
```

适用：随机刷兵、抽卡式单位、随机事件分支。要点：下标分支用 `@copyFromSection` 复制骨架、只改 `@define unit/order`。

### 6.2 旋转加载圈（透明度拖尾）

一圈 `SHARED:white_pixel.png` 贴花（一个 `[decal_line]` + 若干 `@copyFromSection` 复制），用 `createMarker(... dir= int(self.timeAlive*speed)*(360/total)+(360/total*order)).getOffsetRelative(y=central_spacing)` 绕中心排布，`alpha: ${(order+1)/total}` 让每片透明度递增，整体是一个旋转的拖尾加载圈。纯 `self.timeAlive` 驱动，无需逻辑：

```ini
[decal_line]
@define order = 0
@define total = 12
@define rotation_speed = 25
@define central_spacing = 10
image: SHARED:white_pixel.png
imageScaleX: 2
imageScaleY: 5
basePosition: createMarker( self.x, self.y, dir = int(self.timeAlive * ${rotation_speed}) * (360 / ${total}) + (360 / ${total} * ${order}) ).getOffsetRelative( y = ${central_spacing} )
alpha:  ${(order + 1) / total}
[decal_line_1]
@copyFromSection: decal_line
@define order = 1
# … decal_line_2 … decal_line_11 同理，各改 @define order
```

适用：读条、充能、施法进度等纯视觉指示。要点：拖尾感来自 `alpha` 随 `order` 线性递增 + `dir` 随 `timeAlive` 旋转。

### 6.3 弧形血条（线段逐段点亮）

一组 `[decal_c*]` 线段沿一段圆弧排布，用 `isVisible: if self.hp/self.maxHp*${tPB} > ${ord}` 按血量比例逐段点亮；每段用 `createMarker(self.x, self.y, dir=${ord*len}-${dev}).getOffsetRelative(y=${sDi})` 定起点、`drawLineTo` 画到 `y=${sDi+sLe}` 的终点：

```ini
[decal_c]
@define tPB: 32
@define ord: 0
@define len: 3.5
@define dev: 0
@define sDi: 10
@define sLe: 2
isVisible: if self.hp / self.maxHp * ${tPB} > ${ord}
basePosition: createMarker(self.x, self.y, dir= ${ord * len} - ${dev}).getOffsetRelative(y= ${sDi})
drawLineTo: createMarker(self.x, self.y, dir= ${ord * len} - ${dev}).getOffsetRelative(y= ${sDi + sLe})
color: #00ff00
[decal_c1]
@copyFromSection:decal_c
@define ord:1
# … 继续 decal_c2, decal_c3, … 每份只改 @define ord
```

适用：环形血条 / 能量条 / 充能环。要点：`${ord * len}` 决定每段角度、`${sDi}`/`${sLe}` 决定半径与段长；点亮阈值 `tPB` 要与段数对齐。

### 6.4 带衰减窗口的伤害统计

用 `defineUnitMemory` 一行声明多个浮点变量；`updateUnitMemory` + `updateUnitMemoryRate` 做周期衰减（计时器过期就把累计清零）；`created` 时初始化基准血量、`tookDamage` 时累加这次掉的血，用 `select()` 只在正伤害时累加；`%{}` 实时播报：

```ini
[core]
defineUnitMemory: float timer, float last_hp, float dmg_stats, float dmg
updateUnitMemory: dmg_stats= select( self.timeAlive > memory.timer, 0, memory.dmg_stats)
updateUnitMemoryRate: 1
[hiddenAction_init]
autoTriggerOnEvent: created
setUnitMemory: last_hp= self.maxHp
[hiddenAction_tookDmg]
@define dur= 2.5
autoTriggerOnEvent: tookDamage
setUnitMemory: dmg= memory.last_hp - self.hp, dmg_stats= select( memory.dmg > 0, memory.dmg_stats + memory.dmg, memory.dmg_stats), last_hp= self.hp, timer= self.timeAlive + ${dur}
showMessageToAllPlayers: 受到 %{memory.dmg_stats} 伤害。
```

适用：DPS 统计、爆发伤害提示、仇恨值。要点：`updateUnitMemory`（声明在 `[core]`，引擎按 `updateUnitMemoryRate` 周期自动跑）是「不占 action 的轻量周期更新」通道；`last_hp` 做差分得出每次伤害。

### 6.5 雷达盘（扫描 + 坐标投影）

两段式：扫描动作用 `takeResources_*` 遍历范围内敌人，把每个目标位置 `getAsMarker` 存进数组 `dt[thisActionIndex]`（`thisActionIndex` 是逐目标遍历的内建下标，`requireConditional` 卡上限对齐贴花数）；再用一批 `[decal_c*]` 光点，每个 `isVisible: if memory.dt[${ord}] != null`，用 `directionBetween` / `distanceBetween` 把世界坐标投影到以本体为中心、按比例 `pro` 缩放的局部雷达盘：

```ini
[core]
@memory dt: unit[]
@global pro: 0.05
[hiddenAction_Radar]
autoTrigger: true
takeResources_searchOnly: true
takeResources_triggerActionForEach: store_detected
takeResources_includeUnitsWithinRange: 1000
takeResources_includeUnitsWithinRange_team: enemy
setUnitMemory: dt= null                        # 每轮先清空
[hiddenAction_store_detected]
requireConditional: if thisActionIndex <= 101   # 数量与贴花数对上
setUnitMemory: dt[thisActionIndex]= thisActionTarget.getAsMarker
[decal_c]
@define ord: 0
layer: BEFOREUI
isVisible: if memory.dt[${ord}] != null
image: SHARED:light_50.png
imageScale: ${pro}
basePosition: createMarker(self.x, self.y, dir= directionBetween(self, memory.dt[${ord}])).getOffsetRelative(y= distanceBetween(self, memory.dt[${ord}]) * ${pro})
color: #ff0000
[decal_c1]
@copyFromSection:decal_c
@define ord:1
# … 继续到你需要的目标上限，贴花数必须 >= 下标上限
```

适用：小地图 / 雷达盘、威胁指示、索敌可视化。要点：`takeResources_searchOnly` 只搜不扣资源，`_triggerActionForEach` + `thisActionIndex` 把「遍历范围内所有单位」做成批处理；贴花数必须与下标上限对齐。超大规模（上千目标）时贴花用自动生成的大文件 `copyFrom` 进来。


### 6.6 环形缓冲回溯（技法骨架）

技法：用数组当**环形缓冲**，每隔一段时间把 `getAsMarker`（位置 + 朝向）、`self.hp`、`self.shield` 存进 `pos[]` / `values[]`；触发回溯时 `teleportTo` 到若干秒前的标记、`setBodyRotation` 恢复朝向、`setUnitStats: hp=…, shield=…` 还原状态，并 `addActionCooldownTime` 加冷却；回溯期间用两张贴花画「残影」——一张复用本体图 `${decal_img.image}`、一张用 `drawLineTo` 从当前位到标记位连线，`alpha` 随时间线性淡出：

```ini
[action_implement]
text: 时间回溯
text_zh: 时间回溯
teleportTo: memory.pos[(${pos} + 1) % ${dura + 1}]
setBodyRotation: memory.pos[(${pos} + 1) % ${dura + 1}].dir
setUnitStats: hp= …, shield= …
addActionCooldownTime: ${dura + 1}s
setUnitMemory: timer_1= self.timeAlive, current_pos= getAsMarker, marked_pos= memory.pos[(${pos} + 1)]
[decal_phantomShadow]
image: ${decal_img.image}
basePosition: memory.current_pos
alpha: (((memory.timer_1 + ${dura + 1}) - self.timeAlive) / ${dura + 1}) * 0.5
[decal_phantomLine]
drawLineTo: memory.current_pos
basePosition: memory.marked_pos
lineWidth: 1.01
```

适用：回溯 / 回放 / 血量时光机类技能。⚠️ 注意：环形缓冲的下标回绕一定要显式加括号 `(x + 1) % N`（见第 3 章「优先级」坑），`%` 优先级高于 `+`，漏括号会让取模形同虚设。参考**技法骨架**即可，落地时自己补齐数组下标与写入节奏。

### 6.7 本章手法小结

| 手法           | 关键 API                                                                                                                            |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| 贴花即 UI / 渲染层 | `[decal_*]` + `image` / `imageStack` / `imageScale*` / `color` / `alpha` / `isVisible` / `drawLineTo` / `layer: BEFOREUI`         |
| 批量展开贴花       | `@copyFromSection` + `@define ord/…`                                                                                              |
| 标记与偏移        | `createMarker` / `getAsMarker` / `getOffsetRelative` / `getOffsetAbsolute`                                                        |
| 两点关系         | `directionBetween` / `distanceBetween`                                                                                            |
| 遍历范围单位       | `takeResources_searchOnly` / `_triggerActionForEach` / `_includeUnitsWithinRange(_team)` + `thisActionIndex` / `thisActionTarget` |
| 时间驱动动画       | `self.timeAlive` + `rnd` / `int` / `select`                                                                                       |
| 轻量周期更新       | `defineUnitMemory` + `updateUnitMemory` + `updateUnitMemoryRate`                                                                  |
| 概率分支         | `rnd` + `int` + 消息 + `requireConditional` + `convertTo`                                                                           |

### 6.8 隐形代理单位：把建造 / 修理触角伸到全图

> 本节骨架提炼自真实工程（单位名、节名、标签、数值与文案均已中性化），只保留可复用的通用结构。照抄结构、按自己工程改名换值，勿沿用示例里的占位名。

**需求**：一个建筑能对**任意远处**的目标持续建造 / 修理，而引擎的纳米建造（nano）只在自身 `nanoRange` 内生效。做法不是拉大半径，而是**在目标点生成一个隐形代理单位**，让代理代自己干活。

**范式三段**：

1. 主建筑：用 `spawnUnits` 在**路径点（`activeWaypointTarget`）**&#x5904;生成代理，而不是在自己脚下。

```ini
# 主建筑：在“当前路径点”处派出一个隐形代理
[hiddenAction_spawnProxy]
spawnUnits: nano_proxy(spawnSource=self.activeWaypointTarget)
```

1. 代理单位（独立同名 `.ini`，如 `nano_proxy.ini`）：本身是个半径很小的纳米建造 / 修理器，靠"就地生成"覆盖远点。

```ini
[core]
name: nano_proxy
canRepairUnits: true
canRepairBuildings: true
autoRepair: true
nanoBuildSpeed: 0.2
nanoRepairSpeed: 0.04
nanoRange: 32

[turret_1]
invisible: true
limitingRange: 128
canShoot: false
isMainNanoTurret: true        # 关键：声明为主纳米炮塔，才走建造/修理逻辑

[graphics]
repairEffectRate: 120         # 代理可同时充当“额外建造效果”的视觉载体
repairEffectAtTarget: NONE
repairEffect: NONE
```

1. 代理：生成后立刻用 `guard` 路径点**锁定父级**（`customTarget1` 默认指向生成它的工厂 / 来源单位），并在若干秒后**自清理**，避免残留。

```ini
# 代理：出生即守卫父级；寿命到点自删
[hiddenAction_proxy_guardParent]
autoTriggerOnEvent: created
addWaypoint_type: guard
addWaypoint_target_fromReference: customTarget1

[hiddenAction_proxy_expire]
autoTrigger: if self.timeAlive > 10
deleteSelf: true
```

**要点**（均为通用规律，与具体工程无关）：

- `isMainNanoTurret: true` 是让炮塔变"纳米臂"的开关；缺了它就只是个隐形空炮塔。
- 代理靠 `spawnSource=self.activeWaypointTarget` 落到远点，再用 `addWaypoint_target_fromReference: customTarget1` 回到父级身边 —— 于是建造/修理"触角"就伸到了全图。
- 代理**务必** `deleteSelf` 或设寿命上限，否则会越积越多（性能 + 计数）。
- 这套还顺带解决了「额外建造效果没有视觉」的问题：让隐形代理把 `[graphics] repairEffect` 画在目标点上即可。
- `spawnUnits` 的 `spawnSource=` 决定生成位置，可传 `self.activeWaypointTarget` / `customTarget1` / 标记对象等任意单位引用；这是把"生成点"与"建筑自身"解耦的关键。

## 7. 验证、调试与常见坑

铁律：先打开真实文件再下结论。注释、旧文档、甚至指南本身都会过期——绝不能凭记忆或文档臆造节名、键名、成员清单、继承关系或染色范围。常见的"文档打脸"场景：注释里写的工厂 `[canBuild_N]` 成员清单与该节实际 `name:` 不一致；注释把某个 `[decal_*]` 节说成"不被染色"，实际它却落在染色白名单里。

结论：涉及名字、成员清单、继承关系、染色范围时，一律以实际节的真实行为为准，注释与文档仅作线索。

### 下结论前的自检清单

| 自检项               | 怎么查                                                                                                                       |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------- |
| 名字能否被 grep 到      | 单位在静态母版写 `name: ${core.altNames}` 并显式声明 `altNames:`，`grep ^name:` 才解析得出；`altNames` 同时是残骸 `convertTo` 的目标名                 |
| `[canBuild_N]` 成员 | 直接读对应节的 `name:`，勿信文档                                                                                                      |
| ROOT 资产是否真实存在     | `ROOT:` 剥掉前缀后，去磁盘确认该文件真的存在                                                                                                |
| 共享模板的影响面          | 编辑前 `grep -rln 'copyFrom.*<模板名>'` 看谁继承了它                                                                                  |
| `"""` 成对          | 它既是块注释也是多行字符串，必须偶数配平                                                                                                      |
| `${ }` 平衡         | 载入期一次性展开，括号须平衡，引用的 `section.key` / `@global` 必须真实存在                                                                       |
| 节头查重              | `grep -n '^\[' \| sort \| uniq -d` 查重复节头，但勿误伤 `@copyFromSection`（`[decal_shadow] @copyFromSection: decal_img` 是引用，不是重复节头） |

名字自检与 `${}` 平衡示例：

```ini
# name 取自 altNames，altNames 显式声明
name: ${core.altNames}

altNames: myunit
```

```ini
# ${} 内嵌 int()，括号须平衡
reclaimPrice: metal = ${int(core.metalCost * 0.7)}
fogOfWarSightRange: ${int((attack.maxAttackRange * 1.1 + 48) / 20)}
```

### 继承链：改哪个文件波及谁

`grep copyFrom` 看影响面这一做法正确，但要分清"行为链"与"静态链"，否则会误判。带残骸（wreak）的单位最典型：

- 活体 `.ini` 可能同时 `copyFrom` **两条链**：一条**行为模板**（脚本/逻辑，仅活体继承）+ 一条**静态母版**（数值/贴图，活体与残骸共用）。
- 残骸通常**只** `copyFrom` 静态母版，**不吃**行为模板。

```ini
# 残骸只继承静态母版，不继承行为脚本模板
copyFrom: ROOT:units/myunit.template
```

因此：

- 编辑行为模板只改**活体的"行为"**。
- 要同时改**活体 + 残骸**的数值/贴图，必须编辑双方共用的**静态母版**。

查影响面时注意**自匹配**：`grep -rln 'copyFrom.*myunit.template'` 的结果里，模板文件自身的注释行可能自匹配，真正继承它的是那些 `copyFrom` 它的 `.ini`。

### 调试工具与输出通道

四条输出通道，按去向选择；`${}` 载入期展开、`%{}` 运行期求值，可混用：

| 工具                                                | 去向                                       |
| ------------------------------------------------- | ---------------------------------------- |
| `debugMessage: %{...}`                            | 日志                                       |
| `debug(x)` 包进 `%{}`                               | 把单位引用展开成可读调试串（比直接 `%{eventSource}` 信息更全） |
| `showMessageToPlayer` / `showMessageToAllPlayers` | 屏幕消息框                                    |
| `showQuickWarLogToPlayer` / `_zh`                 | 战报（适合事件流水）                               |

```ini
# debug() 展开单位引用，定位"引用是否返回正确单位"
debugMessage: a, %{self.id}, %{debug(eventSource)}
```

```ini
# 战报，用户可见字符串成对给出中英
showQuickWarLogToPlayer: Received unit from %{eventSource.playerName}: %{eventSource}!
showQuickWarLogToPlayer_zh: 收到 %{eventSource.playerName} 的单位: %{eventSource}!
```

```ini
# 屏幕消息框，中英成对
showMessageToPlayer: Your score: %{memory.game_score}
showMessageToPlayer_zh: 你的分数：%{memory.game_score}
```

排错前先 grep 已知待修标记：工程里的 `TODO` / `FIX` 注释常标出已知坏逻辑。

```ini
# TODO: 这里的自动逻辑有 bug，待修。
# FIX: 新版引擎此块需更新（例如 if-else 结构将改写为 otherwise）。
```

### 载入期 `${}` vs 运行期 `%{}`

同名的 `@global` 与 `@memory` 极易混淆。一个单位可同时声明两者：`${threshold}` 是全局载入期常量（可用 `globalSearch` 读别的单位内存）用来取下标，`memory.threshold[...]` 是运行期本单位数组用来取值：

```ini
generation_active: if self.resource.power / self.resource.power_uplimit >= memory.threshold[${threshold}] and self.resource.power >= ${powerMake}
@global threshold: globalSearchForFirstUnit(withTag = "myTag", relation = "own").readUnitMemory("myThresholdStep", type = "float")
@memory threshold: float[]
```

### 性能与联机：沿用节流，勿每帧触发

应在基底模板**显式**设定帧节流（如 `every8Frames`，配 `autoTriggerCooldownTime`），而不是依赖"引擎默认值"（引擎自身默认值无法从文件证实，别臆测）。注意 `autoTriggerCooldownTime_allowDangerousHighCPU: true` 是"允许高 CPU"的许可开关，不是"把逻辑标记为危险"的标签：

```ini
autoTriggerCooldownTime: 5
autoTriggerCheckRate: every8Frames
#autoTriggerCheckWhileNotBuilt: true
autoTriggerCooldownTime_allowDangerousHighCPU: true
```

核心原则：沿用节流，不要每帧触发高频逻辑；残骸等不需要跑逻辑的单位，可只保留最低限度的 `autoTriggerCheckRate`。

### 常见坑与 workaround

| 坑                                | workaround                                                                            |
| -------------------------------- | ------------------------------------------------------------------------------------- |
| 数组取长度用哪个 | **用 `.size`**。官方代码表明确收录 `memory.NAME.size`（1.15，"数组大小，包含空位"）；`length(string)` 只对字符串。真实工程里 `.size` 占绝对多数。空数组行为特殊，自维护计数器 + `shrinkArrays` 最稳 |
| 跨单位读数组会重定向                       | 用 `.get(N)` 读另一单位的数组，别用直接下标                                                           |
| 浮点精度丢失                           | `int()` 拆出整数位与小数位再拼接                                                                  |
| 转换单位丢字段/附属                       | `convertTo_keepCurrentFields` 列白名单；附属须在母版链重声明                                         |
| decal 不能动态跑逻辑                    | action 先算好写进 memory，decal 再读                                                          |
| `setFlag` 不支持动态值                 | 用 `select` 绕，或改设计                                                                     |

**空数组安全模式**：`置 null → shrinkArrays → size 遍历`。取长度统一用 `.size`（官方代码表：`memory.NAME.size` = "数组大小，包含空位"），并自维护计数器下标：

```ini
setUnitMemory: myArray[eventData("id", type = "float")] = null, count = 0
shrinkArrays: myArray
alsoTriggerActionRepeat: memory.myArray.size
setUnitMemory: count = memory.count + 1
setUnitMemory: myArray[memory.myArray.size] = eventSource
```

**跨单位读数组**：真正的 workaround 是 `.get(N)`，而非直接下标。直接下标 `[...]` 易触发跨单位重定向；用 `.get(N)` 读另一单位的 `bool[]` 才是正解：

```ini
# 直接下标（易踩重定向）
setUnitMemory: myVal = customTarget1.readUnitMemory("myBoolArray", type = "bool[]")[eventData("", type = "float")]
# .get(N) 绕过重定向
requireConditional: if memory.myFlag and customTarget1.readUnitMemory("myBoolArray", type = "bool[]").get(0)
```


**浮点精度**：用 `int()` 分别取整数位 `int(x)` 与小数位 `int(x * 10 % 10)` 再拼接。注意有两种变体（`%` 写在 `int` 内 vs 写在 `int` 外）：

```ini
# % 在 int 内
text: %{int(${myval})}.%{int(${myval} * 10 % 10)}
# % 在 int 外
text: %{int(${income})}.%{int(${income} * 10) % 10}
```

**转换单位丢字段/附属**：`convertTo` 默认丢弃当前字段，只有 `convertTo_keepCurrentFields` 列出的才保留。`[attachment_N]` 等活体独有节若未在残骸母版链重声明，转换后即丢失：

```ini
# 死亡就地 convertTo 成残骸，只保 maxHp
setUnitStats: maxHp = self.maxHp * 2, hp += self.maxHp
convertTo: w_${core.altNames}
convertTo_keepCurrentFields: maxHp
```

```ini
# 活体独有附属，不在残骸母版链，转换后丢失
[attachment_1]
onCreateSpawnUnitOf: mysubunit
```

**decal 不能动态跑逻辑**：贴花 `frame` / `basePosition` 只能读 `self.*` / `memory.*`，不能跑 action。做法：由 action 先把位置算好写进 memory，贴花再读：

```ini
# action 把位置算好写进 memory
[hiddenAction_mydecalDriver]
autoTrigger: true
requireConditional: if self.resource.power > 0 and memory.myTimer.timeAlive() > ${14 / 40}
setUnitMemory: myTimer = getOffsetRelative(x = rnd(-${core.radius}, ${core.radius}), y = rnd(-${core.radius}, ${core.radius}))
# 贴花只负责读 memory，不跑逻辑
[decal_mydecal]
frame: self.timeAlive * 40 % 14
basePosition: memory.myTimer
```

### 残骸（wreak）专项坑

残骸是独立的中立外壳单位，继承规则与活体不同，踩坑集中在此。

**残骸只 `copyFrom` 静态母版，`@global` 必须声明在母版链**。`displayDescription` 里的 `${...}` 活体与残骸都要能解析，故 `@global` 要放在双方共用的静态母版，而不是只写在活体 `.ini`：

```ini
# 描述里的 ${} 与其 @global 声明同在静态母版
displayDescription: Detects units within range and displays their position.\nRange is ${myRange}, consumes ${myPower} power per second.
@global myRange = 1000
@global myPower = 0.8
```

```ini
# 残骸 copyFrom 静态母版并改名
copyFrom: ROOT:units/myunit.template
name: w_${core.altNames}
```

**`convertTo: w_${core.altNames}` 要求活体真的 `set` 了 `altNames`**。`altNames` 设在静态母版，`name` 则 `= ${core.altNames}`：

```ini
name: ${core.altNames}
altNames: myunit
```

**`#555555` 染色是固定节名白名单，不是任意编号 decal 都染**。白名单固定为 `{decal_img, decal_turret, decal_img2, decal_img3}`，残骸基底对这些节做 `color: #555555` 的 seed：

```ini
# 四个被 seed 染暗的节
[decal_img]
color: #555555
[decal_turret]
color: #555555
[decal_img2]
color: #555555
[decal_img3]
color: #555555
```

后果：`[decal_img1]` 与 `decal_img4+` **不在**白名单，其残骸层不会染暗。用 `[decal_img1]` 做背景贴图时残骸背景层保持原色，`[decal_img2]` 则会染暗。建议统一使用 `decal_img` / `decal_img2` / `decal_img3`：

```ini
[decal_img1]
image: ROOT:path/to/background.png
[decal_img2]
image: ROOT:path/to/main.png
```

**炮塔贴图须用编号 `[decal_imgN]`（惯例用 `decal_img2`）才落入白名单**。活体 `[turret_1]` 不写 `image`，贴图交由静态 `[decal_img2]` 跟随炮塔渲染：

```ini
# 炮塔贴图用编号 decal_img2，以便残骸自动染暗
[decal_img2]
image: ROOT:path/to/turret.png
basePositionFromTurret: 1
```

**`[movement]` 与 `fogOfWarSightRange` 必须留在活体 `.ini`**。母版若不含它们，残骸会回退到残骸基底的 `movementType: NONE` 与 `fogOfWarSightRange: 0`（残骸本就该不动、无视野）：

```ini
# 活体独有
fogOfWarSightRange: 26
[movement]
moveSpeed: 2.036
# 残骸回退值（写在残骸基底模板里）
fogOfWarSightRange: 0
[movement]
movementType: NONE
```

**注释/文档不可全信，一律以 `copyFrom` 实际行与 `altNames` 为准**。常见坑：母版链的注释是从别的单位复制粘贴后忘了改——注释写的是 A，实际 `copyFrom` 的却是 B：

```ini
# 注释（可能写错，别信）：copyFrom 静态母版 units/anotherunit.template ...
copyFrom: ROOT:units/myunit.template
```


### 跨工程实测发现（来自真实模组，非文档）

以下都是在本工作区多个真实工程里实际见到、且容易误判的点（工程身份隐去，只留现象与对策）：

| 现象                                                                                                                                                                 | 真相 / 对策                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mod-info.txt` 里键写成 `titleb:`                                                                                                                                      | 真键是 `title`，`titleb` 静默失效（真实工程里的笔误）。改完务必核对键名                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `#thumbnail: xxx.png` 被 `#` 注释掉                                                                                                                                    | `#` 是行注释，注释掉的键等于没写。别把要生效的键注释掉                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `thumbnail` 指向了另一个模组的图（如 A 模组的清单里写着 `thumbnail: B.png`）                                                                                                            | 复制粘贴遗留的**错指图**。`thumbnail` 悬空 / 错指很常见，发布前必查指向的文件是否真实存在且为本模组的图                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `mass: 2147483467`                                                                                                                                                 | 真实笔误（少一位 4），靠"数值大到推不动"照样有效。新写用标准 `2147483647`                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `explodeOnDeathGroundCollosion` / `effectOnDeathGroundCollosion`                                                                                                   | 引擎**同时**接受正确拼写 `...Collision` 与旧拼写 `...Collosion`，两种都是真键                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `friendlyFire: only-ignoreEnemy`                                                                                                                                   | `friendlyFire` 除 `true` / `false` 外还有值（如 `only-ignoreEnemy`），别以为只吃布尔                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `repeatConditional: <表达式>`                                                                                                                                         | `[hiddenAction_*]` 上的社区约定键：把该 action 的布尔条件**存起来**，供别处 `${section.repeatConditional}` 引用（代码表未收录，属工程惯例）                                                                                                                                                                                                                                                                                                                                                                                     |
| `autoTriggerCooldownTime: NaNs` | 真实工程里出现过，但**它不是引擎的哨兵值**：`NaN` 会污染后续浮点比较（任何 `>` `<` 都为 false），属隐患写法，别模仿。要"永不冷却"就显式给一个很大的秒数 |
| `setUnitStats: moveSpeed = ${movement.moveSpeed} / ...`                                                                                                            | 运行时改数值用 `setUnitStats`，不能直接改 `[movement]`；表达式里可再引用 `${movement.moveSpeed}` 取原值                                                                                                                                                                                                                                                                                                                                                                                                            |
| `"""` 包住整段 action                                                                                                                                                  | 活体模板里用 `"""` 把"下个版本才启用"的一整段 `[hiddenAction_*]` 注释掉，是常见做法——`"""` 既是多行串也是块注释                                                                                                                                                                                                                                                                                                                                                                                                                |
| `soundOnDeath: a.ogg, b.ogg`                                                                                                                                       | 音效键接受**逗号分隔的多个文件**，随机选播                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `[graphics]` 里的 `animation_idle_start` / `animation_moving_start` / `animation_attack_*`                                                                           | 是 C-f「不建议使用」的旧式动画键，但大量真实工程仍在用；新写优先用 `[animation_*]` 节                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `@global X = 20` 与 `@memory X: float` **同名共存**                                                                                                                     | 局部（`@define`）> 全局（`@global`）> 内存（`@memory`）是不同层；同名不会冲突，但要清楚读的是哪层                                                                                                                                                                                                                                                                                                                                                                                                                          |
| mutator 前缀可以是**多位数**：`mutator31_ifUnitWithTags` / `mutator41_*` / `mutator51_*`                                                                                    | 「基础单数字 + 多数字」并存（实测：`mutator1`…`mutator7` 与 `mutator31/41/51` 同时出现），说明编号就是任意的数字组，`mutator<N>_ifUnitWithTags` 的 N 并非只限 1–9                                                                                                                                                                                                                                                                                                                                                                  |
| mutator 前缀也可以是**单词**：`mutatorPlate_*` / `mutatorShield_*` / `mutatorCavalry_*` / `mutatorUndead_*` / `mutatorIce_*` / `mutatorbio_*` / `mutatorX_*` / `mutatorY_*` | 「数字」只是最常用写法；整套 `mutatorX_<后缀>` 家族的字面量本身就允许是任意单词（含单个大写字母 `X`/`Y`）。后缀家族全量只有 5 种：`ifUnitWithTags` / `ifUnitWithoutTags` / `directDamageMultiplier` / `areaDamageMultiplier` / `addResourcesDirectHit` / `addResourcesAreaHit`（外加 `changedExplodeEffect`）                                                                                                                                                                                                                                     |
| `[hiddenAction_*]` + 独立代理单位 `.ini`                                                                                                                                 | **跨工程「远程建造/修理范围扩展器」范式**（实测于真实工程）：主建筑用 `spawnUnits: <代理名>(spawnSource=self.activeWaypointTarget)` 在**任意路径点处生成一个隐形代理单位**，代理自身 `canRepairUnits` / `canRepairBuildings` / `autoRepair: true` + `nanoRange: 32` + `[turret_1] isMainNanoTurret: true`，于是把建造/修理触角伸到全图；代理用 `addWaypoint_type: guard` + `addWaypoint_target_fromReference: customTarget1` 锁定父级、`autoTrigger: if self.timeAlive > 10` + `deleteSelf: true` 自清理。若要给额外建造效果**补视觉**，正是靠这个隐形代理把 `[graphics] repairEffect` 画在目标点上。详见 6.8 |
| `attachments_addNewUnits` + `attachments_onlyOnSlots` / `onConvertKeepExistingUnitInSameSlot`                                                                      | 「附属即子系统」：一个建筑用 `attachments_addNewUnits: <附属单位名>` + `attachments_onlyOnSlots: 1` 把子系统挂到 1 号槽；子系统升级时用 `onConvertKeepExistingUnitInSameSlot: true` **原地换单位不丢槽位**。这是比 `convertTo` 更适合"装备位"的写法                                                                                                                                                                                                                                                                                                |
| `action_*` 里 `displayType:rally` + `isLockedAlt` / `isLockedAltMessage`                                                                                            | 建造/升级项除 `isLocked` 外还有 **`isLockedAlt`** 一族（独立条件 + 独立提示文案），可与主 `isLocked` 并存，用于「主条件不满足 or 次条件不满足」双闸门                                                                                                                                                                                                                                                                                                                                                                                      |

## 8. 权威速查：代码表与维基

写任何不确定的语法 / 键名 / 函数前，先在这三处核实，别凭记忆。它们是社区公认的权威出口，也是老师模式里要引导用户去的地方。

### 8.0 查键与判版本 —— 用 MCP，不要读表文件

**判定"有没有这个键、从哪个版本才有"这件事，交给 `rusted-warfare` MCP 的 `lookup_key`。**
它背后就是原来那张官方 CSV（1486 行 × 26 列，1177 条带值类型的键），
但已经把三份资料（官方 CSV / 中文离线表 / 二进制）做过对账，返回里直接告诉你结论：

```
lookup_key("targetGround")
→ found / versions（从哪版起）/ value_type / sections（归属哪些节）
  / agreement（几张表都有这个键）/ conflicts（两表说法冲突时）
  / 中文语义 + 官方英文原文 + 例子
```

一次查多个键就传 `keys=["a","b","c"]`——写一个单位常要查七八个键，
分开查就是七八次往返，而每次往返都要重发整段上下文。

**查不到时不要放弃**：官方 CSV 不是全集，二进制里有 44 个键是"游戏认、中文表有、CSV 没有"。
判定规则是**三份资料有其二即可用**；`lookup_key` 的 `agreement` 字段就是干这个的。
三者都查不到才留空。

**为什么曾经强调"看 `Version Released` 列"**：因为它是判断"这个键存不存在 / 从哪个版本才有"
的唯一可靠依据，而 `minVersion` 声明错了会让整个模组在旧版客户端上直接失效。
现在这一步 `lookup_key` 的 `versions` 字段直接给，不用再自己翻列。


**这张表最值钱的地方：它敢说"这个键在某种情况下无效"。** 几个被它直接否掉的想当然写法：

| 你以为 | 官方原文 |
|--------|----------|
| `directDamage` 打地面也有伤害 | `directDamage`："Does not work with `targetGround:true` as it won't have a clear unit to target" |
| 地面武器不用管伤害键 | `targetGround`："only `areaDamage` is applied if targeting ground" |
| `canShoot: false` 就没法开火 | `fireTurretXAtGround`："**bypasses canShoot rules in turret**" |
| action 上的 `autoTriggerCheckRate` 和 `[core]` 叠加 | "This **overrides** `autoTriggerCheckRate` set on `[core]`" |
| `@define` 和 `@global` 差不多 | `@define`："local variable within a section (**best outside of template**)"；`@global`："used in all sections. **Local variables have a higher priority**" |
| `layer` 可以随便大小写 | 官方枚举全小驼峰：`shadow, beforeBody, afterBody, onTop, beforeUI, inactive` |

**版本门槛**（`Version Released` 列的实测摘要，写代码前先对一眼）：

| 版本 | 该版本起才有的常见能力 |
|------|------------------------|
| 1.13 | `self.timeAlive()`、`areaRadius`、`eventSource` 之前的多数基础键 |
| 1.13.3 | `showMessageToPlayer`、`isVisible`（单位级）、`mutatorX_changedExplodeEffect` |
| 1.14 | `alwaysSinglePress`、`iconExtraIsVisible`、`targetGround_includeTargetHeight`、`targetGroundHeightOffset` |
| 1.15 | `@memory`、`setUnitMemory`、`setUnitStats`、`eventSource`、`nullUnit`、`autoTriggerOnEventRecursionLimit` |
| 1.15p9 | `layer`（decal 分层）、decal 相关键；**用了就要在 `mod-info.txt` 声明 `minVersion: 1.15p9`** |

> 官方原文（`minVersion`）："It is important to declare one when using decals and other modding keys starting on version 1.15p9 beta"。**用了 decal 却不声明 `minVersion`，是新手最常犯的发布级错误。**

### 8.1 代码 API 站（「代码表」）

`https://rwapicode.spldream.com/` —— 分类索引式的单位 API 代码表。单位 API 按节分组，查某个节的全部可用键时直接进对应分组：

| 分组            | 对应内容                                                                                           |
| ------------- | ---------------------------------------------------------------------------------------------- |
| 核心 CORE       | `[core]`：name / price / radius / mass / maxHp / displayText(\_zh) / displayDescription(\_zh) 等 |
| 可建造 CANBUILD  | `[canBuild_N]`：name / isLocked / pos / forceNano 等                                             |
| 附属 ATTACHMENT | `[attachment_N]`：挂载子单位                                                                         |
| 图像 GRAPHICS   | `[graphics]`：image / total_frames / dustEffect 等                                               |
| 炮塔 TURRET     | `[turret_N]`：projectile / delay / turnSpeed / aimOffsetSpread 等                                |
| 攻击 ATTACK     | `[attack]`：canAttack* / maxAttackRange / shootDelay 等                                          |
| 运动 MOVEMENT   | `[movement]`：movementType / moveSpeed 等                                                        |
| 逻辑 LOGIC      | 行动 / 触发 / 事件 / 内存 / 条件                                                                         |
| 资源 RESOURCE   | `[resource_*]` / `[global_resource_*]`                                                         |
| 贴花 DECAL      | `[decal_*]`：image / basePosition / layer / color 等                                             |
| 刷兵 SPAWN      | spawnUnits / spawnUnit 等                                                                       |

另有「地图 API」「Trigger」「编写指南」「RW-Engine 指南」等分区。

**该站的真实导航结构**（VitePress 站点，URL 形如 `/src/Unit/<分组>`）：

| 站点顶级入口       | URL                          | 内容                                                                                                                          |
| ------------ | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| 单位代码表        | `/src/Unit/core` 等           | 单位 API，按节分组（core / canBuild / graphics / attack / turret / projectile / movement / ai / logic / resource / decal / spawn …） |
| 单位代码表（NDT）   | `/src/UnitNDT/index`         | NDT 数据集版本                                                                                                                   |
| 地图代码表        | `/src/Map/all`               | TMX 地图代码（当前仅 Trigger 部分）                                                                                                    |
| RW-Engine 指南 | `/src/RW-Engine/quick-start` | RW-Engine 插件使用（仅 Android，开发中）                                                                                               |

> 注意：**站内分组是"功能分组"命名**（core / logic / resource …），与离线中文表的**章节字母 A–U** 大体对应、但并非逐条一一映射。要查全量键名与值类型，**用 MCP `lookup_key`**（它已经把官方 CSV / 中文表 / 二进制对过账）；要读分类说明与在线例子，用此站。下表给出两者的对应关系（近似）：

| 代码表章节 | 站内分组           | 内容                                                                                               |
| ----- | -------------- | ------------------------------------------------------------------------------------------------ |
| A     | 核心 CORE        | `[core]`（12 个子类：通用 / 单位统计 / UI 图形 / 仅构建 / 杂项 / 运输 / 资源节点 / 资源收集器 / 建筑工厂 / 死亡 / 动作 / 不建议使用）       |
| B     | 可建造 CANBUILD   | `[canBuild_NAME]`                                                                                |
| C     | 图像 GRAPHICS    | `[graphics]`（未分类 / 炮塔 / 阴影 / 效果动画 / 特殊 / 不建议使用）                                                  |
| D     | 攻击 ATTACK      | `[attack]`                                                                                       |
| E     | 炮塔 TURRET      | `[turret_NAME]`（未分类 / 计时 / 射击时 / 定位控制 / 图形效果）                                                    |
| F     | 抛射体 PROJECTILE | `[projectile_NAME]`（未分类 / 伤害 / 运动 / 图形效果）                                                        |
| G     | 运动 MOVEMENT    | `[movement]`                                                                                     |
| H     | AI             | `[ai]`                                                                                           |
| I     | 腿脚 / 胳膊        | `[leg_#]` / `[arm_#]`                                                                            |
| J     | 附属 ATTACHMENT  | `[attachment_NAME]`                                                                              |
| K     | 效果 EFFECT      | `[effect_NAME]`（未分类 / 移动 / 图形 / 动画）                                                              |
| L     | 动画 ANIMATION   | `[animation_NAME]`                                                                               |
| M     | 逻辑 LOGIC       | `[action_*]` / `[hiddenAction_*]`（**共 31 个子类** a–ae，见下）                                          |
| N     | 放置规则           | `[placementRule_NAME]`                                                                           |
| O     | 全局资源           | `[global_resource_NAME]`                                                                         |
| P     | 局部资源           | `[resource_NAME]`                                                                                |
| Q     | 贴花 DECAL       | `[decal_NAME]`                                                                                   |
| R     | 模板 / 复制        | `[template_NAME]`（`@copyFromSection` / `@define` / `@global` / `${}` / `%{}` / `"""` / `IGNORE`） |
| S     | 注释 / 特殊单位      | `[comment_NAME]`（内含 `damagingBorder` / `zonemarker` / `setRally` / `reclaim` / `repair` 等内置单位）   |
| T     | 模组             | `[mod]`（仅 `mod-info.txt`）                                                                        |
| U     | 音乐             | `[music]`（仅 `mod-info.txt`）                                                                      |

> **M 章（行动 / 隐藏行动）的 31 个子类**：a 未分类 / b 单位参考 / c UI.AI 要求 / d AI 使用方式 / e 触发器 / f 队列时 / g 结果 / h 连锁动作 / i 声音 / j 发射抛射体 / k 生成单位 / l 位置 / m 运输变化 / n 路径点 / o 冷却 / p 动画 / q 中立 / r 获取资源 / s 转换资源 / t 设置资源 / u 附件 / v 标签变更 / w 显示讯息 / x 发送数据 / y 设置自定义目标 / z 单位位置和移动 / aa 单位统计 / ab 杂项 / ac 单位引用 / ad 标记功能 / ae 全局功能。写行动逻辑时按这 31 类去代码表定位键名，比盲搜快得多。

> 注意一处差异：官方 CORE 文档用 `price:`（支持多资源语法 `price: 资源1=数值1, 资源2=数值2`）；部分模组改用 `metalCost` 并由它派生造价/回收/建造时间。两者都是真实键，照你所在工程的既有写法走，查全量键名用此站。

### 8.2 维基「mod的坑」（高级功能索引）

`https://rustedwarfare.org/wiki/mod的坑` —— 进阶机制的索引页，顺着链接进各专题：

- **基础**：宏（变量）、自定义内存、数组、注释、复制、特殊值、单位引用
- **特殊**：随机数、概率与随机偏移、多单位排序、ai 优先级、重排序、更新延迟
- **常用依赖插件**：`rnd`（修正随机数重复）、`clipboard`（多队伍剪贴板，便捷输入 float/unit）、`RW-Engine`（文本图像化、碰撞箱）、`PCMOD`（便捷输入字符串、游戏内聊天）

### 8.2.1 维基核验的高价值事实（已逐条对照 rustedwarfare.org/wiki）

以下均已在官方维基上**逐条核实**（2026-10，中文铁锈百科）：

**变量（`@define` / `@global` / `${}`）**

- 变量是**纯粹的加载期文本替换工具**，本身没有数据类型；`@global 名:值` 定义全局、`@define 名:值` 定义局部（局部仅在定义它的节可见，同名时局部覆盖全局）。
- **`@global` 务必写在 `[core]` 节**：复制时它会因重排序导致取值错误，放 `[core]` 可避免。
- 引用范围的正则是 `${\s*(.*)\s*}`：**圈内不要填空格**；替换名须匹配 `[a-zA-Z_][0-9a-zA-Z_.]*` 且不能是运算函数名。
- `${}` 支持的运算：`+ - * / ^ ( )`、`sqrt()`、`int()`、`sin()`、`cos()`。**有运算优先级 bug，一律加括号**。若不想被当运算式，值里就别含 `+-*/^()`。
- `${core.price}` 引用 `core` 节的 `price`；`${section}` 指自己，含被复制的节——但某些复制实现在序列化后才注入，**不可引用**。

**自定义内存（`memory`）**

- 类型：`boolean` / `float` / `number`（整数，实现为 float）/ `unit` / **`string`（字符串，常被漏列）**。
- **优先用 `@memory 名:类型`，少用 `defineUnitMemory`**：后者可被覆盖，一旦被覆盖定义就可能失效；`@memory` 无此问题，更适合模板。名字可用中文，但避免特殊符号。
- 读写：`setUnitMemory: 名=值, 名=值...`；`[core]updateUnitMemory`（配 `updateUnitMemoryRate`，单位帧，填 0 表示每帧更新）。
- **`updateUnitMemoryRate` 不要填 `NaN` / `NaNs`**，否则更新会停摆。
- 跨单位读：`单位引用.readUnitMemory('名', type='类型')`；数组版支持 `index='下标'` 参数，即 `readUnitMemory('名', type='类型', index=114)`。

**数组（`xxx[]`，1.15p11+）**

- 类型 `boolean[]` / `float[]` / `number[]` / `unit[]`；单数组上限 10000；下标从 0。
- 定义同内存：`defineUnitMemory:类型 名称[]` 或 `@memory 名称:类型[]`。
- 取长度：**`数组名.size`**（官方代码表收录，1.15，"包含空位"）。`length(string)` 是字符串专用，别混用。
- `数组名=null` 清空（大小归 0）；`数组名.contains("数据")` 判包含；`shrinkArrays` 移除空洞。
- **跨单位读数组重定向 bug（截至 1.15）**：`外部单位.readUnitMemory("名",type="类型")[下标]`，若下标里再嵌 `memory.*` / `self.*`，会被整体重定向到那个外部单位。**局部函数 `thisActionIndex` / `index` / `eventSource` / `thisActionTarget` 不受影响**；消息传来的数组恒为空（`eventData("k",type="float[]")` = `[]`）。绕法：用 `.get(下标)` 而非直接 `[...]`。

**单位引用（1.15+）**

- 标记：`getAsMarker()`；`getOffsetRelative([x],[y],[height],[dirOffset])`（相对，受朝向影响）；`getOffsetAbsolute([x],[y],[height])`（绝对）；`createMarker(x, y, [height], [teamId], [dir])`（`x` `y` 必填，可省略 `x=` / `y=` 字样）。
- 变量引用：`thisActionTarget`（随上下文变）、`eventSource`（仅与 `autoTriggerOnEvent` 绑定）。**只能存在于行动链**（`alsoTriggerAction` / `alsoQueueAction` 传递，连续同种限 10 层，交替可绕过）。
- 函数引用（所有节可用，带选填参数，**慎用默认参数**）：`attachment([slot],[withTag])`、`transporting([slot])`、`nearestUnit([withinRange],[withTag],[relation],[incompleteBuildings],[withoutTag])`（不填默认范围 550）、`globalSearchForFirstUnit([withTag],[relation],[incompleteBuildings])`（不填默认返回地图最小 id 单位）、`self`、`attacking`、`lastDamagedBy`（事件为 `tookDamage` 时的快捷引用）、`parent`（快捷式 `unitref.hasParent([withTag])`）、`activeWaypointTarget`（未指定则返回该位置的标记）。
- 存储引用：`customTarget1` / `customTarget2`——**单位死亡/删除时自动清除**（比 `@memory unit` 省心）。**工厂 `canBuild` / `produceUnits` / `spawnUnit(s)` 出厂单位的 `customTarget1` 默认就是该工厂**，不必再用 `queuedUnitFinished` + `sendMessageTo` 告知。
- 空引用：`null`（可清空数组、可赋空值）；`nullUnit`（不可用于清空数组）。

**特殊值（`-Infinity` / `Infinity` / `NaN`）**

- 生成：`-1/0`、`1/0`、`0/0`。要判断可用字符串比较 `str(${a})=="Infinity"`。
- **luke 对 `NaN` 的判断不规范**：`a==NaN` 返回 true、`NaN!=NaN` 返回 false（均与标准相反），比较时务必留意。
- `max(a,b)` / `min(a,b)` **不受**上述 NaN / Infinity 规则影响，它们按 `a>b` / `a<b` 比较。

**随机数 `rnd(min,max)`**

- **存在"同一帧生成相同随机数"的问题**：返回式约为 `((int)min*1000,(int)max*1000, RandomIndex+unit.bE)*0.001f`，同一 ini 内多个行动的 `RandomIndex` 相同 → 重复。
- 缓解①：用 `self.id` 做偏移，如 `rnd(self.id*0.001, mod)+min`；要更均匀可放大倍率。②：取整数丢弃小数 `int(rnd(self.id*0.001, 1/0))`。③：**建议直接用 `rnd` 组件**（下载在维基"依赖"区，密码 00）。
- 随机器有效范围 **16777215**（游戏滥用 id 时可能超出）；要精确小数位请把区间限制在 **-16777.217 ~ 16777.216** 内以免 float 精度损失。
- 运算优先级有 bug，表达式**尽量加括号**。

**复制 / 继承（`copyFrom`）**

- 解析顺序：`copyFrom` 从左边开始，把每个来源解析成 Map **追加并覆盖**，最后把自己的配置追加覆盖上去（即**右侧 / 自身优先级更高**；离线代码表也表述为"后者覆盖前者"）。**复制一个已用过 `copyFrom` 的 ini，取的是它最终的 Map，但不包含 `all-units.template`。**
- `all-units.template`：让同级与子级、且自身没有 `all-units.template` 的 ini 把它作为**第一个追加**，优先级低于 `copyFrom`。
- `@copyFrom_skipThisSection`：启用则**舍弃此前解析内容、从这里重新追加**；关闭时拿回此前所有内容。
- `@copyFromSection`：取最终 Map 逐节追加覆盖，自身作为最终覆盖；复制一个已用过 `@copyFromSection` 的节，取它的最终结果。
- **`copyFrom`（节级）不支持引用**，且它在序列化完成后才复制——引用型写法会失效。

### 8.3 查询优先级

遇到不确定，按这个顺序查，**不要跳步**：

1. **先看最近邻真实代码怎么写** —— 打开同目录 / 同类单位的真实节，照抄节名、键名、大小写、缩进，再改。真实代码永远比文档新。
2. **查 8.0 官方 CSV** —— 确认"这个键到底存不存在""从哪个版本开始有"。**这一步是判死刑的地方**：CSV 里查不到，就不要写。
3. **查 8.1 在线代码表 / 离线中文代码表** —— 中文表描述更细、示例更全，用来补"怎么用、和谁互斥、有什么坑"。
4. **查 8.2 维基** —— 进阶机制、已知 bug、社区补丁（`rnd` / `clipboard` / `RW-Engine` / `PCMOD`）。
5. **仍不确定就留空**，在描述里写清"未验证"，交给用户进游戏实测。

> 三份代码表的分工：**CSV 判有无与版本**（权威、带 Version 列）→ **中文离线表补语义**（描述细、例子多）→ **在线站补分组导航**（知道该去哪一节找）。三者冲突时，**以 CSV 的键名拼写与版本为准**，以中文表的语义解释为辅。

**永远不要靠猜补语法。**

### 8.4 编辑器插件：RustedWarfare Mod Support（VS Code）

**用户用 VS Code / VSCodium 写模组时，主动推荐装这个插件**——它把"查代码表"搬进编辑器，对冲 luke 语"拼错不报错、只静默失效"的痛点：

| 项目  | 值                                                                                         |
| --- | ----------------------------------------------------------------------------------------- |
| 名称  | RustedWarfare Mod Support                                                                 |
| 作者  | `xingwangzhe`                                                                             |
| 市场  | `https://marketplace.visualstudio.com/items?itemName=xingwangzhe.RustedWarfareModSupport` |
| 开源  | `https://github.com/xingwangzhe/RustedWarfareModSupport`（AGPL-3.0）                        |
| 交流群 | GMBOX 的 mod 群 `1006360455`                                                                |

能力：节属性键自动补全（附说明 / 示例 / 版本 / 弃用）、属性值按类型补全（布尔 / 逻辑布尔 / 单位生成 / 枚举）、`@memory` 上下文补全、`mod-info.txt` 补全、悬停文档、十六进制颜色与 `image` 图片预览、`Format INI File` 右键格式化（保留注释 / 空行 / 节结构）、节折叠、`ZIP` / `RWMOD` 一键导出、自定义后缀侧边栏（记得把 `.template` 加进去）、14 种界面语言。

用法建议：补全当"第一道防线"，键名最终仍以代码表为准；Agent 自己查键走 8.1 / 8.2。安装前先把 VS Code 更新到最新版。详见 0.6。

## 附录 A：常用代码片段

```ini
# —— 条件判断（混用 and/or 一律加括号）——
requireConditional: if self.hp <= 50 and ( self.tags(includes="infantry") or self.tags(includes="scout") )

# —— 内存：声明 + 读写（无 ++，自增手写）——
@memory count: number
setUnitMemory: count = 0
setUnitMemory: count = memory.count + 1

# —— 数组：声明 / 下标 / 长度 / 压缩 / 清空 ——
@memory arr: unit[]
setUnitMemory: arr[0] = nearestUnit(withTag="enemy")
alsoTriggerActionRepeat: memory.arr.size
shrinkArrays: arr
setUnitMemory: arr = null

# —— 跨单位读内存（.get 绕重定向）——
setUnitMemory: v = customTarget1.readUnitMemory("values", type="float[]").get(0)

# —— 单位搜索 ——
nearestUnit(withinRange=500, withTag="enemy", relation="enemy")
globalSearchForFirstUnit(withTag="mainBase", relation="own")

# —— 消息：发送 ——
sendMessageTo: self
sendMessageWithTags: UPDATE
sendMessageWithData: hp= self.hp
# —— 消息：接收 ——
autoTriggerOnEvent: newMessage(withTag="UPDATE")
setUnitMemory: hp = eventData("hp", type="number")

# —— 贴花：本体 + 阴影（阴影复用本体节）——
[decal_img]
image: ROOT:path/to/sprite.png
teamColors: true
[decal_shadow]
@copyFromSection: decal_img
layer: shadow
color: #000000
alpha: 0.5

# —— 资源当 buff 条：受击加、每周期减、映射成减速 ——
[hiddenAction_buff_slow]
autoTriggerOnEvent: tookDamage(withTag="slow")
setResourcesWithLogic: slow = min(50, self.resource.slow + 10)
[hiddenAction_buff_slow_recover]
autoTrigger: true
setResourcesWithLogic: slow = max(0, self.resource.slow - 1)
setUnitStats: moveSpeed = ${movement.moveSpeed} / (self.resource.slow / 50 + 1)
```

## 附录 B：关键事实速查

动手前扫一眼，全是容易踩的硬事实：

- **武器 = `[turret_N]` + `[projectile_N]` + `[effect_*]` 三件套，没有 `[arm_*]`。** 炮塔用 `projectile:` 指向弹丸节（数字对数字、自定义名对同名节）。
- **散布键是 `aimOffsetSpread`，不是 `aimOffsets`。**
- **数组长度用 `.size`**（官方代码表收录 `memory.NAME.size`，1.15）。自维护计数器下标 + `shrinkArrays` 压缩最稳。
- **跨单位读数组用 `.get(N)` 绕重定向 bug**；消息传来的数组恒为空。
- **三种插值分清**：`${...}` 载入期展开一次（含编译期数学 `${int(...)}`）；`%{...}` 运行期每帧求值（UI 文本专用）；`${节.键}` 载入期复制另一节的键值（任意普通键都能被读）。
- **`"""` 既是多行串又是块注释，必须偶数配对**；漏配对会吞掉后续整段配置。`${}` 括号也要平衡。
- **节名 / 键名区分大小写**，拼错不报错只静默失效；casing 不统一是实装常态，照抄最近邻，别据此推断可随意大小写。
- **混用 `and` / `or` 一律加括号**，别赌默认优先级；`%` 优先级高于 `+`，取模回绕写 `(x + 1) % N`。
- **建筑 / 炮塔不可被推动**用质量哨兵 `mass: 2147483647`。
- **`movementType` 取值**：`NONE` / `LAND` / `AIR` / `HOVER` / `WATER` / `OVER_CLIFF`；移动类一般由家族行为模板设定，`copyFrom` 继承即可。
- **继承 = 最后写入者获胜**：引擎默认 < `all-units.template`（按文件名自动套用）< `copyFrom` 链（按列出顺序）< 单位自身内联键；**节按键逐个合并、不整体替换**。
- **双语成对**：单位 / 行动 / 资源文件里 **基键 = 英文、`_zh` = 中文**；但 **`mod-info.txt` 方向相反**（基键 = 中文、`_en` = 英文）。语言中立标签（纯数字 / 符号）可单侧。
- **静态进母版、动态留活体**：造价 / 血量 / 贴图等进 `.template` 母版；`[movement]`、`fogOfWarSightRange`、攻击 / 移动逻辑等若残骸不该继承就留在活体 `.ini`，让残骸回退到残骸基础层的 `NONE` / `0`。
- **残骸只 `copyFrom` 静态母版**：母版 `displayDescription` 用到的 `@global` 必须声明在母版链里；`convertTo: w_${core.altNames}` 要求活体真的 `set` 过 `altNames`。
- **残骸自动染暗只认固定节名白名单**（如 `decal_img` / `decal_img2` / `decal_img3` 等编号节），自由命名的贴花不会被染。
- **高频 `autoTrigger` 要显式开 `_allowDangerousHighCPU`**，并清楚联机同步 / 卡顿代价；能用事件（`autoTriggerOnEvent`）或路径点就别每周期轮询。
- **贴花不能跑逻辑**：`frame` / `basePosition` 只能读 `self.*` / `memory.*`——先用 action 把结果写进内存，贴花再读。

---

## 附录 C：分节键名速查（按 `[section]` 归类）

写具体键前查此表定位分类，再进代码表核对全量参数与值类型。**括号内为代码表里的中文注释**，键名一律照抄英文原拼写。

### C.1 `[core]`（12 个子类，节内直接写键）

**通用**：`name` `altNames` `class` `strictLevel` `price` `mass` `techLevel` `buildSpeed` `radius` `isBio` `isBug` `isBuilder` `streamingCost` `switchPriceWithStreamingCost`

**单位统计**：`maxHp` `selfRegenRate` `maxShield` `startShieldAtZero` `shieldRegen` `energyMax` `startEnergyAtZero` `energyRegen` `energyRegenWhenRecharging` `energyStartingPercentage` `energyNeedsToRechargeToFull` `energyDisplayName` `armour` `armourMinDamageToKeep` `borrowResourcesWhileAlive` `borrowResourcesWhileBuilt` `generation_resources` `generation_active` `generation_credits` `generation_delay`

**UI 和图形**：`showInEditor` `displayText` `displayText_[Language]` `displayDescription` `displayDescription_[Language]` `displayLocaleKey` `displayRadius` `uiTargetRadius` `shieldRenderRadius` `shieldDisplayOnlyDeflection` `shieldDeflectionDisplayRate` `showOnMinimap` `showOnMinimapToEnemies` `showActionsWithMixedSelectionIfOtherUnitsHaveTag`

**仅构建**：`isBuilding` `footprint` `constructionFootprint` `displayFootprint` `buildingSelectionOffset` `buildingToFootprintOffsetX` `buildingToFootprintOffsetY` `placeOnlyOnResPool` `selfBuildRate` `ignoreInUnitCapCalculation`

**杂项**：`copyFrom` `dont_load` `overrideAndReplace` `overrideResourceLoadPath` `logIfCreditResourceUsed` `onNewMapSpawn` `globalScale` `isLocked` `isLockedIfGameModeNoNuke` `experimental` `stayNeutral` `createNeutral` `createOnNeutralTeam` `createOnAggressiveTeam` `tags` `defineUnitMemory` `@memory` `updateUnitMemory` `updateUnitMemoryRate` `fogOfWarSightRange` `fogOfWarSightRangeWhileNotBuilt` `softCollisionOnAll` `disableAllUnitCollisions` `availableInDemo` `isUnrepairableUnit` `isUnselectable` `isUnselectableAsTarget` `isPickableStartingUnit` `startFallingWhenStartingUnit` `soundOnAttackOrder` `soundOnMoveOrder` `soundOnNewSelection` `canNotBeDirectlyAttacked` `canNotBeDamaged` `canNotBeGivenOrdersByPlayer` `canOnlyBeAttackedByUnitsWithTags` `allowCaptureWhenNeutralByAI`

**运输**：`transportSlotsNeeded` `maxTransportingUnits` `transportUnitsRequireTag` `transportUnitsRequireMovementType` `transportUnitsBlockAirAndWaterUnits` `transportUnitsKeepBuiltUnits` `transportUnitsCanUnloadUnits` `transportUnitsAddUnloadOption` `transportUnitsUnloadDelayBetweenEachUnit` `transportUnitsKillOnDeath` `transportUnitsHealBy` `transportUnitsBlockOtherTransports` `whileNeutralTransportAnyTeam` `whileNeutralConvertToTransportedTeam` `convertToNeutralIfNotTransporting` `transportUnitsOnTeamChangeKeepCurrentTeam` `transportUnitsEachUnitAlwaysUsesSingleSlot` `transportUnitsKeepWaypoints`

**资源节点**：`resourceRate` `similarResourcesHaveTag` `resourceMaxConcurrentReclaimingThis` `reclaimPrice`

**资源收集器**：`canReclaimResources` `canReclaimResourcesNextSearchRange` `canReclaimResourcesOnlyWithTags` `resourceReclaimMultiplier` `nanoUnbuildSpeed`

**建筑和工厂**：`canRepairBuildings` `canRepairUnits` `autoRepair` `canReclaimUnitsOnlyWithTags` `canRepairUnitsOnlyWithTags` `nanoRange` `nanoRepairSpeed` `nanoBuildSpeed` `nanoReclaimSpeed` `nanoRangeForRepairIsMelee` `nanoRangeForReclaimIsMelee` `nanoRangeForRepair` `nanoRangeForReclaim` `nanoFactorySpeed`（工厂建造速度乘数，默认 1）`extraBuildRangeWhenBuildingThis` `builtFrom_#_name` / `builtFrom_#_pos` / `builtFrom_#_forceNano` / `builtFrom_#_isLocked` / `builtFrom_#_isLockedMessage`
  
**工厂 / 载具出口**（单位从工厂产出或从载具卸载时的出现位置）：`exit_x` `exit_y` `exit_dirOffset` `exit_heightOffset` `exit_moveAwayAmount`（默认 70）`exitHeightIgnoreParent`

**动作（全局触发节流，写在 `[core]`）**：`autoTriggerCooldownTime` `autoTriggerCooldownTime_allowDangerousHighCPU`（**必须显式开启才允许超高频触发**）`autoTriggerCheckWhileNotBuilt` `autoTriggerCheckRate`（如 `every8Frames`）

**死亡**：`dieOnConstruct` `dieOnZeroEnergy` `dieOnZeroHp` 的反面 `disableDeathOnZeroHp`（**为 true 时 0 血不死，做自定义死亡动作必备**）`numBitsOnDeath` `fireOnDeath` `nukeOnDeath` / `nukeOnDeathRange` / `nukeOnDeathDamage` / `nukeOnDeathDisableWhenNoNuke` `fireTurretXAtSelfOnDeath` `explodeOnDeath` `explodeOnDeathGroundCollision` `effectOnDeath` `effectOnDeathGroundCollision` `explodeOnDeathGroundCollosion` / `effectOnDeathGroundCollosion`（**旧拼写别名，两种都存在**）`unitsSpawnedOnDeath` `unitsSpawnedOnDeath_setToTeamOfLastAttacker` `hideScorchMark` `soundOnDeath` `explodeTypeOnDeath`（枚举：`verysmall` / `small` / `normal` / `large` / `largeUnit` / `building` / `buildingNoShockwaveOrSmoke` / `verylargeBuilding`）`effectOnDeathIfUnbuilt`

### C.2 `[movement]`（22）

`movementType` `moveSpeed` `moveAccelerationSpeed` `moveDecelerationSpeed` `reverseSpeedPercentage` `landOnGround` `targetHeight` `targetHeightDrift` `startingHeightOffset` `maxTurnSpeed` `turnAcceleration` `moveSlidingMode` `moveIgnoringBody` `moveSlidingDir` `joinsGroupFormations` `ignoreMoveOrders` `moveYAxisScaling` `slowDeathFall` `slowDeathFallSmoke` `heightChangeRate` `fallingAcceleration` `fallingAccelerationDead`

> `movementType` 取值：`NONE` / `LAND` / `BUILDING` / `AIR` / `WATER` / `HOVER` / `OVER_CLIFF` / `OVER_CLIFF_WATER`。

### C.3 `[ai]`（23）

`useAsBuilder` `useAsTransport` `useAsAttacker` `useAsHarvester` `disableUse` `ai_upgradePriority` `buildPriority` `noneInBaseExtraPriority` `noneGlobalExtraPriority` `nonInBaseExtraPriority` `nonGlobalExtraPriority`（**官方拼写是 `none*`**；`non*` 变体在游戏二进制里也存在，但代码表只收录 `none*`，新写用 `none*`）`recommendedInEachBaseNum` `recommendedInEachBasePriorityIfUnmet` `upgradedFrom` `maxGlobal` `maxEachBase` `notPassivelyTargetedByOtherUnits` `lowPriorityTargetForOtherUnits` `aiTags` `whenUsingAsHarvester_recommendedInEachBase` `whenUsingAsHarvester_recommendedGlobal` `whenUsingAsHarvester_includeOtherHarvesterCounts` `onlyUseAsHarvester_ifBaseHasUnitTagged`

### C.4 `[attack]`（`canAttack*` 一族）

`maxAttackRange` `canAttack` `canAttackFlyingUnits` `canAttackLandUnits` `canAttackUnderwaterUnits` `canAttackNotTouchingWaterUnits` `canOnlyAttackUnitsWithTags` `canOnlyAttackUnitsWithoutTags` `setMainTurretAs` `turretMultiTargeting` `isMelee` `meleeEngangementDistance`（原文拼写如此）`turretRotateWithBody` `attackMovement` `dieOnAttack` `removeOnAttack` `isFixedFiring` `aimOffsetSpread` `stopTargetingAfterFiring` `disablePassiveTargeting` `showRangeUIGuide` `shootDelayMultiplier` `shootDamageMultiplier`；luke 不推荐：`turretSize` `turretTurnSpeed` `shootDelay`；无明显作用：`attackMovementSpeed` `attackMovementSpread`

### C.5 `[turret_N]`（5 组）

**未分类**：`x` `y` `height` `copyFrom` `projectile` `altProjectile` `altProjectileCondition` `barrelX` `barrelY` `barrelHeight` `size` `turnSpeed` `turnSpeedAcceleration` `turnSpeedDeceleration` `idleDir` `idleDirReversing` `shouldResetTurret` `idleSweepAngle` `idleSweepDelay` `idleSweepSpeed` `idleSweepCondition` `idleSweepAddRandomDelay` `idleSweepAddRandomAngle` `attachedTo` `slave` `isMainNanoTurret` `energyUsage` `resourceUsage`
  
**计时**：`delay` `linkDelayWithTurret` `warmup` `warmupCallDownRate` `warmupNoReset` `warmupShootDelayTransfer`
  
**射击时**：`onShoot_freezeBodyMovementFor` `barrelOffsetX_onOddShots` `yAxisScaling`
  
**定位控制**：`canShoot` `canAttack` `canAttackFlyingUnits` `canAttackLandUnits` `canAttackUnderwaterUnits` `canAttackNotTouchingWaterUnits` `canOnlyAttackUnitsWithTags` `canOnlyAttackUnitsWithoutTags` `canAttackCondition` `clearTurretTargetAfterFiring` `limitingRange` `limitingAngle` `limitingMinRange` `canAttackMaxAngle` `interceptProjectiles_withTags` `interceptProjectiles_andTargetingGroundUnderDistance` `interceptProjectiles_andUnderDistance` `interceptProjectiles_andOverHeight` `laserDefenceEnergyUse` `aimOffsetSpread`
  
**图形和效果**：`invisible` `image` `image_applyTeamColors` `image_drawOffsetX` `image_drawOffsetY` `chargeEffectImage` `warmupStartEffect` `shoot_sound` `shoot_sound_vol` `shoot_flame` `shoot_light` `idleSpin` `onShoot_playAnimation` `onShoot_triggerActions` `unloadUpToXUnitsAndGiveAttackOrder` `recoilOffset` `recoilOutTime` `recoilReturnTime` `showRangeUIGuide`

### C.6 `[projectile_N]`（4 组）

**未分类**：`life` `delayedStartTimer` `interceptProjectile_removeTargetLifeOnly` `deflectionPower` `explodeOnEndOfLife` `autoTargetingOnDeadTarget` `autoTargetingOnDeadTargetRange` `autoTargetingOnDeadTargetLead` `unloadUpToXUnitsFromSource` `teleportSource` `spawnUnit` `convertHitToSourceTeam` `tags` `flameWeapon` `spawnProjectilesOnEndOfLife` `spawnProjectilesOnExplode` `spawnProjectilesOnCreate`
  
**伤害**：`directDamage` `areaDamage` `areaRadius` `areaDamageNoFalloff` `areaRadiusFromEdge` `areaExpandTime` `areaHitAirAndLandAtSameTime` `areaHitUnderwaterAlways` `areaIgnoreUnitsCloserThan` `buildingDamageMultiplier` `shieldDamageMultiplier` `shieldDefectionMultiplier` `hullDamageMultiplier` `ignoreParentShootDamageMultiplier` `armourIgnoreAmount` `friendlyFire` + **mutator 系列**：`mutatorX_ifUnitWithTags` / `mutatorX_ifUnitWithoutTags` / `mutatorX_directDamageMultiplier` / `mutatorX_areaDamageMultiplier` / `mutatorX_changedExplodeEffect` / `mutatorX_addResourcesDirectHit` / `mutatorX_addResourcesAreaHit`（X 为 1、2、3… 序号，按目标标签切换伤害 / 效果）
  
**运动**：`targetGround` `targetGroundSpread` `targetGround_includeTargetHeight` `targetGroundHeightOffset` `speed` `targetSpeed` `targetSpeedAcceleration` `ballistic` `ballistic_delaymove_height` `ballistic_height` `speedSpread` `instant` `instantReuseLast` `instantReuseLast_alsoChangeTurretAim` `instantReuseLast_keepAreaDamageList` `disableLeadTargeting` `leadTargetingSpeedCalculation` `initialUnguidedSpeedHeight` `initialUnguidedSpeedX` `initialUnguidedSpeedY` `gravity` `trueGravity` `turnSpeed` `turnSpeedWhenNear` `wobbleAmplitude` `wobbleFrequency` `pushForce` `pushVelocity` `moveWithParent` `sweepOffset` `sweepSpeed` `sweepOffsetFromTargetRadius` `retargetingInFlight` `retargetingInFlightSearchDelay` `retargetingInFlightSearchRange` `retargetingInFlightSearchLead` `retargetingInFlightSearchOnlyTags`
  
**图形和效果**：`color` `teamColorRatio` `teamColorRatio_sourceRatio` `invisible` `image` `shadowFrame` `shadowImage` `drawType` `drawSize` `frame` `hitSound` `explodeEffect` `explodeEffectOnShield` `drawUnderUnits` `effectOnCreate` `shouldRevealFog` `alwaysVisibleInFog` `nukeWeapon` `trailEffect` `trailEffectRate` `lightSize` `lightColor` `lightCastOnGround` `largeHitEffect` `lightingEffect` `laserEffect` `beamImage` `beamImageOffsetRate` `beamImageStart` `beamImageEnd` `beamImageStartRotated` `beamImageEndRotated`

### C.7 `[effect_N]`（4 组）

**未分类**：`life` `lifeRandom` `alsoEmitEffectsOnDeath` `alsoEmitEffects` `ifSpawnFailsEmitEffects` `alsoPlaySound` `createWhenOffscreen` `createWhenZoomedOut` `createWhenOverLiquid` `createWhenOverLand` `spawnChance` `showInFog` `delayedStartTimer` `delayedStartTimerRandom` `liveAfterAttachedDies` `priority`
  
**移动**：`attachedToUnit` `alwayStartDirAtZero` `atmospheric` `physics` `physicsGravity` `xOffsetRelative` `yOffsetRelative` `xOffsetRelativeRandom` `yOffsetRelativeRandom` `xOffsetAbsolute` `yOffsetAbsolute` `xOffsetAbsoluteRandom` `yOffsetAbsoluteRandom` `xSpeedRelative` `ySpeedRelative` `xSpeedRelativeRandom` `ySpeedRelativeRandom` `xSpeedAbsolute` `ySpeedAbsolute` `xSpeedAbsoluteRandom` `ySpeedAbsoluteRandom` `hOffset` `hOffsetRandom` `hSpeed` `hSpeedRandom` `dirOffset` `dirOffsetRandom` `dirSpeed` `dirSpeedRandom` `pivotOffset` `pivotOffsetRandom`
  
**图形**：`frameIndex` `frameIndexRandom` `stripIndex` `image` `imageShadow` `scaleTo` `scaleFrom` `color` `teamColorRatio` `drawType` `drawUnderUnits` `fadeInTime` `fadeOut` `alpha` `trailEffect` `trailEffectRate` `shadow`
  
**动画**：`frame_width` `frame_height` `total_frames` `animateFrameStart` `animateFrameEnd` `animateFramePingPong` `animateFrameSpeed` `animateFrameSpeedRandom` `animateFrameLooping` `animateFrameStartRandomAdd`

### C.8 `[decal_N]`（54）

`layer` `order` `onlyWhenSelectedByOwnPlayer` `onlyWhenSelectedByEnemyPlayer` `onlyWhenSelectedByAllyNotOwnPlayer` `onlyWhenSelectedByAnyPlayer` `includeParentsSelection` `onlyPlayersWithUnitControl` `onlyTeam` `onlyWithZoomLevelOrMore` `onlyWhileActive` `onlyOnBodyFrameOf` `onlyWhileAlive` `onlyInPreview` `onlyOnNonPreview` `imageScale` `imageScaleX` `imageScaleY` `image` `teamColors` `imageStack` `stack_hOffset` `stack_frameOffset` `stack_drawInReverseOrder` `stack_indexStart` `stack_indexCount` `total_frames` `frame_verticalOrdering` `frame_width` `frame_height` `frame` `addBodyFrameMultipliedBy` `isVisible` `xOffsetRelative` `yOffsetRelative` `xOffsetAbsolute` `yOffsetAbsolute` `hOffset` `dirOffset` `pivotOffset` `alwaysStartDirAtZero` `alwayStartDirAtZero` `alwaysStartHeightAtZero` `basePosition` `basePositionFromLeg` `basePositionFromTurret` `basePositionFromLegEnd` `drawLineTo` `image_shadow` `shadowOffsetX` `shadowOffsetY` `color` `alpha` `lineWidth`

### C.9 `[canBuild_N]`（17）

`name` `pos` `tech` `forceNano` `isVisible` `isLocked` `isLockedMessage(_[Language])` `isLockedAlt(_Message)` `isLockedAlt2(_Message)` `addResources` `price` `isGuiBlinking` `extraLagHidingInUI` `type`

### C.10 `[placementRule_N]`（24）

`anyRuleInGroup` `searchTags` `searchTeam` `searchOffsetX` `searchOffsetY` `searchDistance` `excludeIncompleteBuildings` `excludeNonBuildings` `minCount` `maxCount` `blocksPlacement` `cannotPlaceMessage(_[Language])` `checkEachTile` `aiSuggestionOnly` `credits` `energy` `hp` `shield` `ammo` `setFlag` `unsetFlag` `hasFlag` `hasMissingFlag`

### C.11 `[attachment_N]`（37）

定位：`x` `y` `height` `lockDir` `idleDir` `idleDirReversing` `isVisible` `onCreateSpawnUnitOf` `canBeAttackedAndDamaged` `isUnselectable` `isUnselectableAsTarget` `lockLegMovement` `freezeLegMovement` `showMiniHp` `hideHp` `hidden` `keepAliveWhenParentDies` `setDrawLayerOnTop` `setDrawLayerOnBottom` `addTransportedUnits` `lockRotation` `rotateWithParent` `resetRotationWhenNotAttacking` `deattachIfWantingToMove` `unloadInCurrentPosition` `prioritizeParentsMainTarget` `alwaysAllowedToAttackParentsMainTarget` `onlyAttackParentsMainTarget` `canAttack` `onParentTeamChangeKeepCurrentTeam` `smoothlyBlendPositionWhenExistingUnitAdded` `keepWaypointsNeedingMovement` `showAllActionsFrom` `createIncompleteIfParentIs` `onConvertKeepExistingUnitInSameSlot` `redirectDamageToParent` `redirectDamageToParent_shieldOnly`

### C.12 `[global_resource_N]`（27）/ `[resource_N]`（24）

两者键几乎相同：`stackHorizontal` `displayName` `displayNameShort` `hidden` `priority` `displayColor` `displayRoundedDown` `displayWhenZero` `iconImageUseInText` `iconImage` `displayNameHideWhenIconShownInText` `displayNameHideWhenIconShownInHUD` `displayColorUseInText` `appendResourceInHUD` `displayPrefixInHUD` `displayPostfixInHUD` `displayTextAppendResourceWithGap` `appendResourceInHUD_whenThisZero` `includeInStats` `valueInStats` `displayInHud` `displayDigitGrouping` `displayTextAppendResource` `displayPos` `displayWithRounding` `displayTextPrefix` `displayTextPostfix`。
  
**局部资源**另有 `equivalentGlobalResourceForAI`（把局部资源映射成 AI 能读的全局资源）。

### C.13 `[animation_N]`（L 章）/ `[leg_#]` / `[arm_#]`

动画：`onActions` `onActionsQueuedUnitPlayAt` `blendIn` `blendOut` `pingPong` `playbackRate` `KeyframeTimeScale`；关键帧 `arm#_[time]` / `leg#_[time]` / `body_[time]` / `effect#_[time]` / `turret#_[time]`；多向动画 `direction_useMainTurret` / `direction_units` / `direction_strideX` / `direction_strideY` / `direction_starting`。
  
腿脚 / 胳膊：`x` `y` `alpha` `copyFrom` `attach_x` `attach_y` `rotateSpeed` `endDirOffset` `lockMovement` `heightSpeed` `moveSpeed` `moveWarmUp` `holdDisMin` `holdDisMax` `holdDisMin_maxMovingLegs` `hold_moveOnlyIfFurthest` `holdDisMin_checkNeighbours` `hardLimit` `estimatingPositionMultiplier`；图形 `hidden` `image_end` `image_end_shadow` `image_end_teamColors` `image_foot` `image_foot_shadow` `image_middle` `image_leg` `liftingHeightOffset` `targetHeight` `targetHeightRelative` `image_middle_teamColors` `draw_foot_on_top` `drawOverBody` `drawUnderAllUnits` `drawDirOffset` `dust_effect` `spinRate` `favourOppositeSideNeighbours` `drawLegWhenZoomedOut` `drawFootWhenZoomedOut` `explodeOnDeath` `resetAngle`

### C.14 `[graphics]`（5 组）

**未分类**：`image` `image_back` `image_back_always_use_full_image` `image_wreak` `image_shield` `image_offsetX` `image_offsetY` `image_offsetH` `isVisible` `isVisibleToEnemies` `teamColorsUseHue` `teamColoringMode` `scaleImagesTo` `imageScale` `drawLayer` `whenBeingBuiltMakeTransparentTill` `icon_zoomed_out` `icon_zoomed_out_neverShow` `icon_build` `image_floatingPointSize` `showSelectionIndicator`
  
**炮塔**：`image_turret` `turretImageScale` `teamColorsOnTurret` `scaleTurretImagesTo` `lock_body_rotation_with_main_turret` `lock_leg_rotation_with_main_turret`
  
**阴影**：`image_shadow` `shadowOffsetX` `shadowOffsetY` `image_shadow_frames` `lock_shadow_rotation_with_main_turret`
  
**效果和动画**：`total_frames` `default_frame` `frame_width` `frame_height` `splastEffect`（原文拼写）`dustEffect` `splastEffectReverse` `dustEffectReverse` `movementEffect` `movementEffectReverse` `movementEffectRate` `movementEffectReverseFlipEffects` `repairEffect` `repairEffectAtTarget` `repairEffectRate` `reclaimEffect` `reclaimEffectAtTarget` `reclaimEffectRate` `rotate_with_direction` `animation_direction_useMainTurret` `animation_direction_units` `animation_direction_strideX` `animation_direction_strideY` `animation_direction_starting` `disableLowHpFire` `disableLowHpSmoke` `showTransportBar` `showHealthBar` `showHealthBarChanges` `showEnergyBar` `showShieldBar` `showQueueBar` `showShotDelayBar`
  
**特殊**：`imageSmoothing` `imageSmoothingWhenZoomedIn`



### C.15 `[action_N]` / `[hiddenAction_N]`（31 个子类，择要）

**a 未分类（外观 / 元数据）**：`text` `textPostFix` `text_[Language]` `description` `description_[Language]` `displayType` `displayRemainingStockpile` `pos` `iconImage` `iconExtraImage` `iconExtraColor` `iconExtraIsVisible` `unitShownInUI` `setBuilt` `guiBuildUnit` `tags` `id` `aiTags`
**b 单位参考**：`textAddUnitName` `descriptionAddFromUnit` `descriptionAddUnitStats` `unitShownInUIWithHpBar` `unitShownInUIWithProgressBar`
**c UI / AI 要求**：`price` `isActive` `isVisible` `isLocked` `isLockedMessage` `isLockedAlt` `isLockedAltMessage` `isLockedAlt2` `isLockedAlt2Message` `allowMultipleInQueue` `onlyOneUnitAtATime` `isGuiBlinking` `alwaysSinglePress` `isAlsoViewableByAllies` `isAlsoViewableByEnemies` `extraLagHidingInUI` `streamingCost` `switchPriceWithStreamingCost` `aiUse`
**d AI 使用方式**：`ai_isDisabled` `ai_isHighPriority` `ai_considerSameAsBuilding`
**e 触发器**：`autoTriggerOnEvent` `alsoTriggerOrQueueActionWithTarget` `autoTriggerOnEventRecursionLimit` `autoTrigger` `autoTriggerCheckRate`
**f 队列时**：`buildSpeed` `buildSpeed_ignoreFactorySpeedModifiers` `refundAllQueuedItems` `removeAllQueuedItemsWithoutRefund` `highPriorityQueue` `canPlayerCancel` `whenBuilding_cannotMove` `whenBuilding_playAnimation` `whenBuilding_rotateTo` `whenBuilding_rotateTo_orBackwards` `whenBuilding_rotateTo_waitTillRotated` `whenBuilding_temporarilyConvertTo` `whenBuilding_temporarilyConvertTo_keepFields` `whenBuilding_triggerAction` `whenBuilding_rotateTo_aimAtActionTarget` `whenBuilding_rotateTo_rotateTurretX` `spawnEffectsOnQueue` `playSoundToPlayerOnQueue`
**g 结果**：`requireConditional` `convertTo` `convertTo_keepCurrentTags` `convertTo_keepCurrentFields` `addEnergy` `addResources` `addResourcesScaledByAIHandicaps` `addResourcesWithLogic` `setResourcesWithLogic` `deleteSelf` `resetCustomTimer` `setBodyRotation` `setHeight` `setUnitStats` `resetUnitStats` `shrinkArrays` `setUnitMemory`
**h 连锁动作**：`alsoTriggerAction` `alsoTriggerActionRepeat` `alsoQueueAction` `alsoTriggerOrQueueActionConditional`
**i 声音**：`playSoundAtUnit` `playSoundGlobally` `playSoundToPlayer`
**j 发射抛射体**：`fireTurretXAtGround` `fireTurretXAtGround_withOffset` `fireTurretXAtGround_withProjectile` `fireTurretXAtGround_showGuideDecals` `fireTurretXAtGround_withTarget` `fireTurretXAtGround_count` `fireTurretXAtGround_onlyOverPassableTileOf`
**k 生成单位**：`spawnUnits` `spawnEffects` `produceUnits`
**l 位置**：`offsetSelfAbsolute` `teleportTo`
**m 运输变化**：`transportTargetNow` `addUnitsIntoTransport` `deleteNumUnitsFromTransport` `deleteNumUnitsFromTransport_onlyWithTags` `startUnloadingTransport` `forceUnloadTransportNow` `forceUnloadTransportNow_onlyOnSlot`
**n 路径点**：`clearAllWaypoints` `clearActiveWaypoint` `addWaypoint_type` `addWaypoint_unitType` `addWaypoint_prepend` `addWaypoint_triggerActionIfFailed` `addWaypoint_triggerActionIfMatched` `addWaypoint_maxTime` `addWaypoint_target_nearestUnit_tagged` `addWaypoint_target_nearestUnit_team` `addWaypoint_target_nearestUnit_maxRange` `addWaypoint_target_mapMustBeReachable` `addWaypoint_target_fromReference` `addWaypoint_position_offsetFromSelf` `addWaypoint_position_fromAction` `addWaypoint_position_randomOffsetFromSelf` `addWaypoint_position_relativeOffsetFromSelf` `addWaypoint_target_randomUnit_tagged` `addWaypoint_target_randomUnit_team` `addWaypoint_target_randomUnit_maxRange`
**o 冷却**：`addAllActionCooldownsTime` `addAllActionCooldownsFor` `addActionCooldownTime` `addActionCooldownFor` `addActionCooldownApplyToActions` `clearAllActionCooldowns`
**p 动画**：`playAnimation` `playAnimationIfNotPlaying` `playAnimation_lowPriority` `finishPlayingLastAnimation` `stopLastAnimation`
**q 中立**：`switchToNeutralTeam` `switchToAggressiveTeam` `switchToTeam`
**r 获取资源**：`takeResources` `takeResources_includeUnitsInTransport` `takeResources_includeParent` `takeResources_includeReference` `takeResources_triggerActionForEach` `takeResources_includeUnitsWithinRange` `takeResources_includeUnitsWithinRange_team` `takeResources_excludeUnitsWithoutTags` `takeResources_excludeUnitsWithoutCustomTarget1EqualTo` `takeResources_excludeUnitsWithTheseResources` `takeResources_excludeUnitsWithoutAllResources` `takeResources_triggerActionIfAnyCollected` `takeResources_triggerActionIfNoneCollected` `takeResources_discardCollected` `takeResources_keepResourcesOnTarget` `takeResources_maxUnits` `takeResources_directTransferStoppingAtZero` `takeResources_searchOnly` `takeResources_saveFirstUnitToCustomTarget1` `takeResources_saveFirstUnitToCustomTarget2`
**s 转换资源**：`convertResource_from` `convertResource_to` `convertResource_minAmount` `convertResource_maxAmount` `convertResource_multiplyAmountBy`
**t 设置资源**：`resourceAmount` `resourceAmount_setValue` `resourceAmount_addOtherResource` `resourceAmount_multiplyBy`
**u 附件**：`attachments_addNewUnits` `attachments_deleteNumUnits` `attachments_onlyOnSlots` `disconnectFromParent` `attachments_unload` `attachments_disconnect`
**v 标签变更**：`temporarilyAddTags` `temporarilyRemoveTags` `resetToDefaultTags` `addGlobalTeamTags` `removeGlobalTeamTags`
**w 显示讯息**：`showMessageToPlayer` `showMessageToPlayer_[Language]` `showMessageToAllPlayers` `showMessageToAllEnemyPlayers` `showQuickWarLogToPlayer` `showQuickWarLogToAllPlayers` `debugMessage`
**x 发送数据**：`sendMessageTo` `sendMessageWithData` `sendMessageWithTags`
**y 设置自定义目标 / 生成参数**：`setCustomTarget1` `setCustomTarget2` `swapCustomTarget1And2` `neutralTeam` `aggressiveTeam` `setToTeamOfLastAttacker` `spawnChance` `spawnSource` `maxSpawnLimit` `gridAlign` `skipIfOverlapping` `falling` `offsetX` `offsetY` `offsetRandomX` `offsetRandomY` `offsetRandomXY` `offsetRandomDir` `offsetHeight` `offsetDir` `transportedUnitsToTransfer` `copyWaypointsFrom` `techLevel` `recursionLimit` `xOffsetRelative` `yOffsetRelative` `xOffsetAbsolute` `yOffsetAbsolute`
**y 逻辑（可填进任何 `requireConditional` / if 表达式）**：`true` `false` `if` `and` `or` `not` `<` `>` `<=` `>=` `==` `!=` `+` `-` `/` `*` `%` `^` `()`
**z 单位位置和移动**：`self.isUnderwater()` `self.underwater()` `self.gound()`（原文拼写，另见 `self.ground()`）`self.isAtGroundHeight()` `self.flying()` `self.isFlying()` `self.isMoving()` `self.isAtTopSpeed()` `self.isInWater()` `self.inWater()` `self.isOverwater()` `self.overWater()` `self.isOverLiquid()` `self.isOverClift()`（原文拼写）`self.isOverPassableTile()` `self.isOverOpenLand()` `self.height()`
**aa 单位统计**：`self.hasResources()` `self.resource()` `self.resource.RESOURCE_TYPE` `self.isResourceLargerThan()` `self.maxHp()` `self.hp()` `self.ammo()` `self.maxShield()` `self.maxEnergy()` `self.isEnergyRecharging()` `self.isAmmoEmpty()` `self.ammoIncludingQueued()` `self.energy()` `self.energyIncludingQueued()` `self.isEnergyFull()` `self.isEnergyEmpty()` `self.shield()` `self.kills()` `self.queueSize()` `self.id()` `self.teamId()` `self.playerName()` `self.teamName()` `self.x()`/`self.y()`/`self.z()` `self.dir()` `self.priceCredits()`
**ab 杂项**：`self.hasFlag()` `self.tags()` `self.hasTags()` `self.globalTeamTags()` `self.transportingCount()` `self.numberOfAttachedUnits()` `self.isAttacking()` `self.hasActiveWaypoint()` `self.transportingUnitWithTags()` `self.isTransportUnloading()` `self.hasParent()` `self.hasTakenDamage()` `self.timeAlive()` `self.lastConverted()` `self.customTimer()` `self.isOnNeutralTeam()` `numberOfUnitsInTeam()` `self.numberOfUnitsInAllyTeam()` `self.numberOfUnitsInAllyNotOwnTeam()` `numberOfUnitsInEnemyTeam()` `numberOfUnitsInNeutralTeam()` `numberOfUnitsInAggressiveTeam()` `numberOfUnitsInAllTeams()` `self.hasUnitInTeam()` `self.noUnitInTeam()` `self.isInMap()` `game.mapWidth()` `game.mapHeight()` `self.isReversing()` `self.isControlledByAI()` `self.readUnitMemory()` `self.eventData()` `memory.NAME` `memory.NAME[下标]` `memory.MEMORY_NAME.size`（**官方数组长度写法，优先用它**）`memory.MEMORY_NAME.length()` `memory.MEMORY_NAME.get()` `memory.MEMORY_NAME.contains()` `self.numberOfQueuedWaypoints()` `self.speed()` `self.maxspeed()` `self.builtAmount()` `self.completed()` `self.maxMoveSpeed()` `self.teamDefeatedTech()` `self.teamWipedOut()` `self.numberOfConnections` `self.teamVictory()`
**ac 单位引用**：`thisActionTarget` `eventSource` `attachment` `transporting` `attacking` `lastDamagedBy` `parent` `activeWaypointTarget` `customTarget1` `customTarget2` `nearestUnit` `globalSearchForFirstUnit` `nullUnit` `null`
**ad 标记功能**：`getAsMarker()` `getOffsetAbsolute([x],[y],[height])` `getOffsetRelative([x],[y],[height],[dirOffset])` `createMarker([x],[y],[height],[dir],[teamId])`
**ae 全局功能**：`distance(x1,y1,x2,y2)` `distanceSquared(x1,y1,x2,y2)` `distanceBetween(u1,u2)` `distanceBetweenSquared(u1,u2)` `game.nukesEnabled()` `int([float])` `select(bool,a,b)` `debug(bool)` `debugPassthrough(bool)` `str(x)` `substring(string,start,end)` `length(string)` `squareRoot(num)` `sqrt(num)`（**仅 `${}` 可用**）`min(a,b)` `max(a,b)` `cos([float])`（**仅 `${}`**）`sin([float])`（**仅 `${}`**）`thisActionIndex` / `index` `uppercase(string)` `lowercase(string)` `direction(x1,y1,x2,y2)` `directionBetween(u1,u2)` `true()` `false()` `rnd(min,max)`

### C.16 模板 / 特殊值（R 章）

`@copyFromSection: 节名` `@copyFrom_skipThisSection: true` `@define X: 值` `@global X: 值` `${X}` `${section.key}` `%{X}` `"""文本"""` `IGNORE`（全大写）

---

> 本指南持续更新。遇到新坑、新技法、新约定时及时补充。永远记住：**先查代码表，再写代码；能自己试，就别问。**
