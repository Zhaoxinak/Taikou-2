# _test_duel.gd — M7 单挑（一骑讨）DuelSim 无头校验（extends SceneTree）
#
# 复刻结构：src/core/duel.gd
# 比对参考实现：scripts/duel_ref.py（11/11）+ duel2_ref.py（15/15）+ duel3_ref.py（21/21）
#
# 覆盖：跳表派发 / 大额公式(0x467c80/0x468000) / 暴击(0x467a70) / 瞬杀阈值 /
#   常规三段式(0x4687b0→0x4698d0→0x466340) 基表·上限·钳制·伤害域·扣血方向 /
#   AI 一击必杀决策(0x469310) check_action_code·compute_threshold·ai_decide_ikill·ai_select_action /
#   AI 行动谱穷举({0,4}) / GameState.run_duel 集成 + 确定性。
#
# 运行：Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_duel.gd

extends SceneTree

const DuelRef = preload("res://src/core/duel.gd")

var _fails: int = 0


func check(cond: bool, msg: String) -> void:
	if cond:
		print("[ok] " + msg)
	else:
		push_error("[FAIL] " + msg)
		_fails += 1


func _setg(ds: RefCounted, g978v: int, g993v: int, g833v: int, g818v: int, g81av: int, g995v: int) -> void:
	ds.g978 = g978v
	ds.g993 = g993v
	ds.g833 = g833v
	ds.g818 = g818v
	ds.g81a = g81av
	ds.g995 = g995v


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)


func _run() -> void:
	var ds: RefCounted = DuelRef.new()
	var gs = root.get_node("/root/GameState")

	# ---- [A] 跳表派发 0x4684c0 ----
	check(ds.dispatch(0) == 0x468457, "dispatch(0) → 0x468457")
	check(ds.dispatch(1) == 0x468489, "dispatch(1) → 0x468489")
	check(ds.dispatch(2) == 0x468495, "dispatch(2) → 0x468495")
	check(ds.dispatch(3) == 0x4684a0, "dispatch(3) → 0x4684a0")
	check(ds.dispatch(4) == 0x4684a9, "dispatch(4) → 0x4684a9")
	check(ds.dispatch(5) == -1, "dispatch(5) 非法 → -1")

	# ---- [B] 大额公式（duel2_ref self_test #2/#3/#4）----
	# #2: g978=0x0c,g993=30,g833=60,g818=2,g81a=0,g995=10; rand%40 中值 19
	# dmg = 19 + 3*10 + 30//3 + 20 + 2*10 = 99
	_setg(ds, 0x0c, 30, 60, 2, 0, 10)
	var r1: RefCounted = ds.new_rng(); r1.push_queue([19])
	var res1: Dictionary = ds.large_damage(r1)
	check(int(res1["damage"]) == 99, "large-dmg(Fixed) = 99")
	check(res1["halved"] == false, "large-halved = false")
	# #3: g81a=0x38 → 减半；g995=0x20 不加；dmg=19//2=9
	_setg(ds, 0, 0, 0, 0, 0x38, 0x20)
	var r2: RefCounted = ds.new_rng(); r2.push_queue([19])
	var res2: Dictionary = ds.large_damage(r2)
	check(int(res2["damage"]) == 9 and res2["halved"] == true, "large-half-true = (9, true)")
	# #4: g995 边界 <20 加 20
	_setg(ds, 0, 0, 0, 0, 0, 0x13)
	var rA: RefCounted = ds.new_rng(); rA.push_queue([19]); var aL: Dictionary = ds.large_damage(rA)
	_setg(ds, 0, 0, 0, 0, 0, 0x14)
	var rB: RefCounted = ds.new_rng(); rB.push_queue([19]); var bL: Dictionary = ds.large_damage(rB)
	check(int(aL["damage"]) - int(bL["damage"]) == 20, "g995 边界：<20 加 20（差 20）")

	# ---- [C] 暴击概率（0x467a70）----
	# g978=0x0c → p=((0x0c>>2)&3)*3=9；中值 49 → 49<9 false
	_setg(ds, 0x0c, 0, 0, 0, 0, 0)
	var rc: RefCounted = ds.new_rng(); rc.push_queue([49])
	check(ds.crit_roll(rc) == false, "crit-roll g978=0x0c(p=9) 49<9 → false")
	# g978=0 → p=0
	_setg(ds, 0, 0, 0, 0, 0, 0)
	var rc2: RefCounted = ds.new_rng(); rc2.push_queue([49])
	check(ds.crit_roll(rc2) == false, "crit-roll g978=0(p=0) → false")

	# ---- [D] 瞬杀阈值（0x468000）dmg > (g833//3 + (g818&3)*10) ----
	# dmg=19+0+0+0+2*10=39；threshold=60//3+2*10=40 → 39>40 false
	_setg(ds, 0, 0, 60, 2, 0, 0x20)
	var ri: RefCounted = ds.new_rng(); ri.push_queue([19])
	var inst1: Dictionary = ds.attack_damage(4, ri)
	check(inst1["instakill"] == false, "instakill-false (dmg=39, thr=40)")
	# dmg=39+0+0+0+2*10=59 > 40 true
	_setg(ds, 0, 0, 60, 2, 0, 0x20)
	var ri2: RefCounted = ds.new_rng(); ri2.push_queue([39])
	var inst2: Dictionary = ds.attack_damage(4, ri2)
	check(inst2["instakill"] == true, "instakill-true (dmg=59, thr=40)")

	# ---- [E] 常规三段式伤害模型（duel_ref selfcheck #11-17）----
	check(ds.DMG_BASE_TABLE == [[0,0,0,0,0,1,1],[0,0,0,1,1,1,2],[0,0,1,1,1,2,2],[0,1,1,1,2,2,3]], "DMG_BASE_TABLE 4×7")
	check(ds.DMG_CAP_TABLE == [1,2,2,3], "DMG_CAP_TABLE [1,2,2,3]")
	var caps: Array = ds.DMG_CAP_TABLE
	var ok_cap: bool = true
	for i in range(4):
		if ds.damage_tier(i, 1, 10, 6, 0) > int(caps[i]):
			ok_cap = false
	check(ok_cap, "damage_tier 被上限钳制")
	var hi: int = -1
	for rr in range(100):
		var vh: int = ds.damage_value(3, 99, rr)
		if vh > hi: hi = vh
	var lo: int = 999
	for rr in range(100):
		var vl: int = ds.damage_value(3, 0, rr)
		if vl < lo: lo = vl
	check(hi == 4 and lo == 0, "damage_value 域 [0,4]（bonus 0-2 + rand%tier）")
	# 扣血方向
	var ad1: Array = ds.apply_damage(10, 10, 0, 3)
	var ad2: Array = ds.apply_damage(10, 10, 1, 3)
	check(ad1[0] == 7 and ad1[1] == 10, "apply_damage flag=0 扣 A")
	check(ad2[0] == 10 and ad2[1] == 7, "apply_damage flag≠0 扣 B")
	# duel_damage 组合
	var dd: Array = ds.duel_damage(3, 1, 55, 6, 0, 99, 0)
	check(dd[0] == 3 and dd[1] == 2, "duel_damage(3,1,55,6,0,99,0) = [3,2]")

	# ---- [F] AI 一击必杀决策（duel3_ref）----
	check(ds.check_action_code(0) == 0 and ds.check_action_code(1) == 0 and ds.check_action_code(2) == 0, "chk 0/1/2 → 0")
	check(ds.check_action_code(3) == 1 and ds.check_action_code(4) == 1 and ds.check_action_code(5) == 1, "chk 3/4/5 → 1")
	check(ds.compute_threshold(0, 50, false) == 60, "thr t0 hp50 nobit5 = 60")
	check(ds.compute_threshold(2, 30, true) == 50, "thr t2 hp30 bit5 = 50")
	check(ds.compute_threshold(5, 80, true) == 70, "thr cap t5 hp80 bit5 = 70")
	check(ds.compute_threshold(3, 100, false) == 140, "thr t3 hp100 nobit5 = 140")
	var weak: Dictionary = {0xb: 30, 0xf: 0x00, 0x8: 0x00, 0x21: 0x30}
	check(ds.ai_decide_ikill(weak, 10, 0) == false, "no-skill 永不 ikill")
	var strong: Dictionary = {0xb: 95, 0xf: 0xC0, 0x8: 0x00, 0x21: 0x50}
	check(ds.ai_decide_ikill(strong, 5, 0) == true, "strong+lowhp → ikill")
	var strong_full: Dictionary = {0xb: 95, 0xf: 0xC0, 0x8: 0x20, 0x21: 0x50}
	check(ds.ai_decide_ikill(strong_full, 200, 0) == true, "strong fullhp bit5 → ikill")
	var strong_full2: Dictionary = {0xb: 95, 0xf: 0xC0, 0x8: 0x00, 0x21: 0x50}
	check(ds.ai_decide_ikill(strong_full2, 200, 0) == false, "strong fullhp no-bit5 → no ikill")
	var edge: Dictionary = {0xb: 50, 0xf: 0x00, 0x8: 0x00, 0x21: 0x41}
	check(ds.ai_decide_ikill(edge, 40, 0) == false, "edge strength==thr → no ikill")
	var edge2: Dictionary = {0xb: 51, 0xf: 0x00, 0x8: 0x00, 0x21: 0x41}
	check(ds.ai_decide_ikill(edge2, 40, 0) == true, "edge strength>thr → ikill")
	var s1: Dictionary = ds.ai_select_action(strong, 5, 0)
	check(s1["action"] == 4 and s1["ikill_flag"] == 1, "select ikill → action=4 flag=1")
	var s2: Dictionary = ds.ai_select_action(strong_full2, 200, 0)
	check(s2["action"] == 0 and s2["ikill_flag"] == 0, "select normal → action=0 flag=0")
	# AI 行动谱穷举（续93）
	var ok_rep: bool = true
	var combos: int = 0
	var sweep_b: Array = [0, 40, 95]
	var sweep_f: Array = [0x00, 0x20, 0xC0]
	var sweep_21: Array = [0x30, 0x41, 0x80]
	var sweep_hp: Array = [0, 30, 100, 200]
	var sweep_tier: Array = [0, 2, 4]
	for b in sweep_b:
		for f in sweep_f:
			for f21 in sweep_21:
				for hp in sweep_hp:
					for tier in sweep_tier:
						var ch: Dictionary = {0xb: b, 0xf: f, 0x8: (f & 0x20), 0x21: f21}
						var sel: Dictionary = ds.ai_select_action(ch, hp, tier)
						combos += 1
						if not (int(sel["action"]) in ds.AI_ACTION_REPERTOIRE):
							ok_rep = false
						if (int(sel["action"]) == 4) != bool(sel["ikill_flag"]):
							ok_rep = false
	check(ok_rep, "AI 行动谱穷举仅 ∈ {0,4} 且 flag 一致")
	check(combos > 0, "sweep 非零组合")

	# ---- [G] GameState.run_duel 集成 + 确定性 ----
	gs.start_new_game(13)
	var rngg: RefCounted = ds.new_rng(); rngg.seed(12345)
	var r1g: Dictionary = gs.run_duel(13, 0, rngg)
	check(r1g.has("winner"), "run_duel 返回 winner 键")
	var rngg2: RefCounted = ds.new_rng(); rngg2.seed(12345)
	var r2g: Dictionary = gs.run_duel(13, 0, rngg2)
	check(r1g["winner"] == r2g["winner"] and r1g["rounds"] == r2g["rounds"], "run_duel 同种子确定性一致")
	var ok_log: bool = true
	for e in r1g["log"]:
		if not (int(e["action"]) in ds.AI_ACTION_REPERTOIRE):
			ok_log = false
	check(ok_log, "run_duel 日志行动谱 ∈ {0,4}")

	# ---- 收尾 ----
	print("")
	if _fails == 0:
		print("[DUEL PASS] 全部断言通过 ✅")
		quit(0)
	else:
		push_error("[DUEL FAIL] %d 项断言失败 ❌" % _fails)
		quit(1)
