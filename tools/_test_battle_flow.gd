# _test_battle_flow.gd — 合战生产入口 battle_flow.gd 校验
#
# 校验：
#   ① build() 能从真实战图建 ctx，并按 wet 设置 mode_m2
#   ② 降水只可能**降低**战力（cat==2 洋枪 ×2/3）；有洋枪时严格降低
#   ③ run() 跑完整场：收敛（winner 合法、rounds>0）、双方剩余兵力非负
#   ④ 多张战图压测均收敛（复用 battle_sim 既有 38 图×100 场的结论，此处抽样）
# 运行：Godot --headless --script res://tools/_test_battle_flow.gd

extends SceneTree

const BattleFlow = preload("res://src/battle/battle_flow.gd")
const BattleSim = preload("res://src/battle/battle_sim.gd")

var _pass := 0
var _fail := 0

func _c(cond: bool, msg: String) -> void:
	if cond:
		_pass += 1
		print("  [ok] ", msg)
	else:
		_fail += 1
		print("  [FAIL] ", msg)


func _total_strength(ctx: BattleSim.BattleCtx) -> int:
	return BattleSim.army_strength(ctx, 0) + BattleSim.army_strength(ctx, 1)


func _run() -> void:
	var path := "res://data/battles.json"
	if not FileAccess.file_exists(path):
		_c(false, "缺少 battles.json")
		quit(1)
	var battles: Array = JSON.parse_string(FileAccess.get_file_as_string(path))
	_c(battles != null and battles.size() > 0, "battles.json 载入 %d 张战图"
		% (battles.size() if battles != null else 0))

	var b0: Dictionary = battles[0]
	var seed0 := 12345

	# —— ① 建 ctx + mode_m2 ——
	var ctx_dry := BattleFlow.build(b0, seed0, 0)
	var ctx_wet := BattleFlow.build(b0, seed0, 1)
	_c(ctx_dry.mode_m2 == 0, "build(wet=0) ⇒ mode_m2=0")
	_c(ctx_wet.mode_m2 == 1, "build(wet=1) ⇒ mode_m2=1（洋枪惩罚开）")
	_c(ctx_dry.units.size() > 0, "ctx 建出单位 %d 个" % ctx_dry.units.size())

	# —— ② 降水只降不升；有洋枪则严格降低 ——
	var s_dry := _total_strength(ctx_dry)
	var s_wet := _total_strength(ctx_wet)
	_c(s_wet <= s_dry, "降水战力 ≤ 干燥战力（%d ≤ %d）" % [s_wet, s_dry])
	var guns := 0
	for u in ctx_dry.units:
		var unit := u as BattleSim.BattleUnit
		if unit != null and unit.active() and unit.category() == 2:
			guns += 1
	if guns > 0:
		_c(s_wet < s_dry, "存在洋枪(%d)时降水严格降战力（%d < %d）" % [guns, s_wet, s_dry])
	else:
		print("  [info] 本战图无 cat2 单位，跳过严格降低断言")

	# —— ③ 跑完整场 ——
	var r_dry := BattleFlow.run(b0, seed0, 0)
	var r_wet := BattleFlow.run(b0, seed0, 1)
	_c(int(r_dry.get("rounds", 0)) > 0, "干燥：回合数 %d > 0" % int(r_dry.get("rounds", 0)))
	_c(int(r_dry.get("winner", -2)) in [-1, 0, 1], "干燥：winner 合法 (%d)" % int(r_dry.get("winner", -2)))
	_c(int(r_dry.get("troops_side0", -1)) >= 0 and int(r_dry.get("troops_side1", -1)) >= 0,
		"干燥：剩余兵力非负 (s0=%d s1=%d)" % [int(r_dry.get("troops_side0", -1)), int(r_dry.get("troops_side1", -1))])
	_c(int(r_wet.get("rounds", 0)) > 0, "降水：回合数 %d > 0" % int(r_wet.get("rounds", 0)))
	_c(int(r_wet.get("winner", -2)) in [-1, 0, 1], "降水：winner 合法 (%d)" % int(r_wet.get("winner", -2)))

	# —— ④ 多图抽样收敛 ——
	var ok := 0
	var n := mini(battles.size(), 8)
	for i in n:
		var res := BattleFlow.run(battles[i], 777 + i, i % 2)
		if int(res.get("rounds", 0)) > 0 and int(res.get("winner", -2)) in [-1, 0, 1]:
			ok += 1
	_c(ok == n, "抽样 %d 张战图全部收敛 (%d/%d)" % [n, ok, n])

	print("\nRESULT: %d/%d checks passed" % [_pass, _pass + _fail])
	quit(0 if _fail == 0 else 1)


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)
