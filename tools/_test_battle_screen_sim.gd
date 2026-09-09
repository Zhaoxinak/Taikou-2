# _test_battle_screen_sim.gd — 验证 battle_screen 已接线 battle_flow（能看→能打）
#
# 实例化 scenes/screens/battle_screen.tscn：
#   1. _ready 自动推演 ⇒ result 非空、winner∈{-1,0,1}、rounds>0
#   2. 晴 vs 雨：降水旗 wet 生效（晴 0 / 雨 1），雨时洋枪队战力受 ×2/3
#      ⇒ 同一 seed 下雨天总战力更低（或至少回合数/结果有可观测差异）
#   3. 天晴/雨切换触发重算，结果面板节点 BattleResult 存在
#   4. result_summary() 文本含胜负与回合数
#
# 运行：Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_battle_screen_sim.gd

extends SceneTree

var _pass := 0
var _fail := 0


func check(cond: bool, msg: String) -> void:
	if cond:
		_pass += 1
		print("  [ok] %s" % msg)
	else:
		_fail += 1
		print("  [FAIL] %s" % msg)


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)


func _run() -> void:
	var scene_path := "res://scenes/screens/battle_screen.tscn"
	if not ResourceLoader.exists(scene_path):
		push_error("缺少场景 %s" % scene_path)
		quit(1)
	var scene: PackedScene = load(scene_path)
	var inst := scene.instantiate()
	inst.battle_id = 0
	inst.auto_simulate = true
	inst.battle_seed = 7
	root.add_child(inst)
	await create_timer(0.15).timeout

	# 1) 自动推演
	var r: Dictionary = inst.result
	check(not r.is_empty(), "_ready 自动推演产出 result（非空）")
	check(r.has("winner"), "result 含 winner")
	check(r.has("rounds"), "result 含 rounds")
	var w := int(r.get("winner", -99))
	check(w >= -1 and w <= 1, "winner ∈ {-1,0,1}（实得 %d）" % w)
	check(int(r.get("rounds", 0)) > 0, "rounds > 0（实得 %d）" % int(r.get("rounds", 0)))
	check(int(r.get("wet", -1)) == 0, "默认「晴」⇒ wet=0（实得 %d）" % int(r.get("wet", -1)))
	check(r.has("gun_units"), "result 含 gun_units")
	check(r.has("troops_side0") and r.has("troops_side1"), "result 含双方残兵")

	# 2) 结果面板
	var panel_node := inst.get_node_or_null("BattleResult")
	check(panel_node != null, "战果面板 BattleResult 已挂（CanvasLayer + UiPanel）")

	# 3) result_summary 文本
	var s: String = inst.result_summary()
	check(s.find("回合") >= 0, "result_summary 含回合数：%s" % s)

	# 4) 切雨 ⇒ 重算且 wet=1
	var dry_rounds := int(r.get("rounds", 0))
	var dry_t0 := int(r.get("troops_side0", 0))
	var dry_t1 := int(r.get("troops_side1", 0))
	inst.set_weather("雨")
	await create_timer(0.15).timeout
	var r2: Dictionary = inst.result
	check(int(r2.get("wet", -1)) == 1, "set_weather(雨) 后 wet=1（实得 %d）" % int(r2.get("wet", -1)))
	var wet_rounds := int(r2.get("rounds", 0))
	var wet_t0 := int(r2.get("troops_side0", 0))
	var wet_t1 := int(r2.get("troops_side1", 0))
	var guns := int(r2.get("gun_units", 0))
	print("  [info] 洋枪队 %d；晴 %d 回合(左%d/右%d) vs 雨 %d 回合(左%d/右%d)" % [
		guns, dry_rounds, dry_t0, dry_t1, wet_rounds, wet_t0, wet_t1])

	# 若本战图有洋枪队，降水必然改变战力 ⇒ 回合数或残兵必有差异
	if guns > 0:
		check(dry_rounds != wet_rounds or dry_t0 != wet_t0 or dry_t1 != wet_t1,
			"有洋枪队时降水改变战局（回合数/残兵与晴天不同）")
	else:
		print("  [skip] 战图 0 无洋枪队（cat!=2），跳过降水差异断言")

	# 5) 直接调 simulate 显式参数：同 seed 可复现
	var a: Dictionary = inst.simulate(7, 0)
	var b: Dictionary = inst.simulate(7, 0)
	check(int(a.get("rounds", -1)) == int(b.get("rounds", -2)),
		"同 seed 同 wet 推演可复现（%d == %d）" % [
			int(a.get("rounds", -1)), int(b.get("rounds", -2))])

	# 6) 换 seed ⇒ 战局可不同（不强制，仅信息）
	var c: Dictionary = inst.simulate(99, 0)
	print("  [info] seed=99 ⇒ %d 回合（seed=7 ⇒ %d 回合）" % [
		int(c.get("rounds", 0)), int(a.get("rounds", 0))])

	print("RESULT: %d/%d checks passed" % [_pass, _pass + _fail])
	quit(1 if _fail > 0 else 0)
