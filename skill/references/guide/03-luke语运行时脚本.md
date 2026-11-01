# 第 3 章 · luke 语运行时脚本与逻辑

> 铁锈战争模组开发指南 · 分册 ｜ [← 第 2 章](02-单位建筑武器定义.md) ｜ [目录](README.md) ｜ [第 4 章 →](04-非战斗与UI驱动.md)

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

---

> [← 第 2 章](02-单位建筑武器定义.md) ｜ [目录](README.md) ｜ [第 4 章 →](04-非战斗与UI驱动.md)
