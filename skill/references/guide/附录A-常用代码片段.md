# 附录 A · 常用代码片段

> 铁锈战争模组开发指南 · 分册 ｜ [← 第 8 章](08-权威速查.md) ｜ [目录](README.md) ｜ [附录 B →](附录B-关键事实速查.md)

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

---

> [← 第 8 章](08-权威速查.md) ｜ [目录](README.md) ｜ [附录 B →](附录B-关键事实速查.md)
