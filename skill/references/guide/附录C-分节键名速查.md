# 附录 C · 分节键名速查（按 `[section]` 归类）

> 铁锈战争模组开发指南 · 分册 ｜ [← 附录 B](附录B-关键事实速查.md) ｜ [目录](README.md)

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

---

> [← 附录 B](附录B-关键事实速查.md) ｜ [目录](README.md)
