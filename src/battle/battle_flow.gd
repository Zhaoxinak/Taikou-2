extends RefCounted
## battle_flow.gd — 合战「生产入口」薄层：把 battle_sim 接上真实战图 + 天气
##
## 闭合缺口：battle_sim 早已具备 `build_ctx_from_battle`（从真实战图建 ctx）
##   与 `simulate`（跑完整场至一方归零）—— 测试里 38 图×100 场 = 3800 场全收敛；
##   但 `src/` 下**无任何 BattleCtx 构建点**，`battle_screen.gd` 只做静态展示
##   → 合战「能看不能打」。本文件即那层缺失的入口。
##
## RE 已证（1:1 复用，不另造公式）：
##   · build_ctx_from_battle：sect_a ← unit_table[*].raw（9×20，低4位=divisor 索引）；
##     单位 ← deploy 图非中性格（左/右军各一单位）
##   · simulate：逐回合同推进至 alive_troops 一方归零，返回 {winner, rounds, ...}
##   · 天气降水 → ctx.mode_m2（即 0x51352c wet 旗）⇒ cat==2 洋枪战力 ×2/3
##     （0x42d62e；与 weather.gd 的 gun_strength_penalty 同规则，_test_gun_penalty 11/11 已验）
##
## 设计：与 diplomacy.gd / weather.gd 一致 —— **自含、不依赖 GameData**；
##   战图 Dictionary 与 wet 旗由调用方注入（便于无头测试，也便于 UI/AI 复用）。
##
## ⚠️ 诚实未接（沿用 battle_sim 现状，非本层引入）：
##   · 单位 stat_atk/equip_tier/morale 由 build_ctx_from_battle 依部署图派生，
##     原版单位属性来自运行时 obj（0x43e200 等），静态无表 → 属既有占位，非本层新增。

const BattleSim = preload("res://src/battle/battle_sim.gd")


## 从真实战图构建 ctx，并按降水旗设置 mode_m2（洋枪惩罚开关）。
##   battle  battles.json 的一条（含 unit_table / deploy / terrain）
##   seed    随机种子（决定单位初始属性抖动）
##   wet     降水旗（0/1）；非 0 ⇒ cat==2 单位战力 ×2/3
static func build(battle: Dictionary, seed: int, wet: int = 0) -> BattleSim.BattleCtx:
	var ctx := BattleSim.build_ctx_from_battle(battle, seed)
	ctx.mode_m2 = 1 if int(wet) != 0 else 0
	return ctx


## 跑完一整场。返回 battle_sim.simulate 的结果并附加本层信息：
##   winner  0/1 胜方，-1 = 同时归零（平局/全灭）
##   rounds  回合数
##   wet     实际生效的降水旗
##   gun_units  参战单位中 cat==2（洋枪）的数量 >0 时惩罚才可能生效
static func run(battle: Dictionary, seed: int, wet: int = 0,
		max_rounds: int = 2000) -> Dictionary:
	var ctx := build(battle, seed, wet)
	var guns := 0
	for u in ctx.units:
		var unit := u as BattleSim.BattleUnit
		if unit != null and unit.active() and unit.category() == 2:
			guns += 1
	var cmds := BattleSim.commanders_of(ctx)
	var res: Dictionary = BattleSim.simulate(ctx, cmds.pA, cmds.pB, max_rounds)
	res["wet"] = 1 if int(wet) != 0 else 0
	res["gun_units"] = guns
	res["troops_side0"] = BattleSim.alive_troops(ctx, 0)
	res["troops_side1"] = BattleSim.alive_troops(ctx, 1)
	return res
