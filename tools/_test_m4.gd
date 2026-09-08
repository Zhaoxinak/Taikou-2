# _test_m4.gd — M4 内政与修行 无头校验（extends SceneTree）
#
# 覆盖：8 修行动作 + 功勲 += (旧级+1)×500 封顶 60000 + 12 主命派发 + 覆盖层隔离。
# 运行：Godot_v4.7.1/Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_m4.gd

extends SceneTree

const ConstsRef = preload("res://src/core/Consts.gd")

var _fails: int = 0

func check(cond: bool, msg: String) -> void:
	if cond:
		print("[ok] " + msg)
	else:
		push_error("[FAIL] " + msg)
		_fails += 1

func _initialize() -> void:
	# --script 模式下 autoload 尚未进树，挂首个 process_frame 再跑断言
	process_frame.connect(_run, CONNECT_ONE_SHOT)

func _run() -> void:
	var gs = root.get_node("/root/GameState")
	var gd = root.get_node("/root/GameData")

	# —— 0) 开局 ——
	check(gs.start_new_game(13), "#13 织田信长 开局成功")
	check(gs.is_started(), "开局状态成立")
	var st0: Dictionary = gs.get_status()
	var sk0: Array = st0.get("skill_levels", [])
	var fo0: Dictionary = st0.get("forces", {})
	var merit0: int = int(st0.get("merit", 0))
	var money0: int = int(st0.get("money", 0))
	check(sk0.size() == 10, "技能数组 10 项")
	check(money0 == 1000, "主角私金起始 = 1000 (got %d)" % money0)

	# —— 1) 学习魅力(mode2) → 兵法(5)+1 + 功勲=(旧级+1)*500 ——
	var s5 := int(sk0[5])
	var exp_gain2 := 0
	var exp_merit2 := 0
	if s5 < ConstsRef.SKILL_CAP:
		exp_gain2 = 1
		exp_merit2 = (s5 + 1) * 500
	var exp_final2: int = mini(merit0 + exp_merit2, ConstsRef.MERIT_CAP)
	var exp_delta2: int = exp_final2 - merit0
	var r2: Dictionary = gs.train_mode(2, 1, [])
	check(r2.get("ok", false), "mode2 学习魅力 执行成功 (reason=%s)" % r2.get("reason",""))
	check(int(r2.get("gains", []).size()) == exp_gain2, "mode2 增益数 = %d (got %d)" % [exp_gain2, r2.get("gains", []).size()])
	check(int(r2.get("merit_gain", 0)) == exp_delta2, "mode2 功勲增量 = %d (got %d)" % [exp_delta2, r2.get("merit_gain", 0)])
	check(int(gs.get_status().get("merit", 0)) == exp_final2, "功勲累计 = %d (got %d)" % [exp_final2, gs.get_status().get("merit", 0)])

	# —— 2) 学习内政(mode0) 概率门 ——
	gs.start_new_game(13)
	var sk_a: Array = gs.get_status().get("skill_levels", [])
	var sub0 := int(sk_a[0])
	var money_a := int(gs.get_status().get("money", 0))
	# 成功门：rand_vals=[0] → 0 % (16-sub)==0
	var r0s: Dictionary = gs.train_mode(0, 1, [0])
	var exp_gain0 := 1 if sub0 < ConstsRef.SKILL_CAP else 0
	check(int(r0s.get("gains", []).size()) == exp_gain0, "mode0 成功门增益 = %d (got %d)" % [exp_gain0, r0s.get("gains", []).size()])
	check(int(gs.get_status().get("money", 0)) == money_a - 2, "mode0 成功日 私金 -2 (got %d, expect %d)" % [gs.get_status().get("money", 0), money_a - 2])
	# 失败门：rand_vals=[1] → 1 % (16-sub) != 0（16-sub∈{13..16}）
	gs.start_new_game(13)
	var money_b := int(gs.get_status().get("money", 0))
	var r0f: Dictionary = gs.train_mode(0, 1, [1])
	check(int(r0f.get("gains", []).size()) == 0, "mode0 失败门 无增益")
	check(int(gs.get_status().get("money", 0)) == money_b - 2, "mode0 失败日仍计费 私金 -2 (got %d)" % gs.get_status().get("money", 0))

	# —— 3) 学习外交(mode1) → 筑城(7)+1 + 功勲=(旧级+1)*500 ——
	gs.start_new_game(13)
	var sk_c: Array = gs.get_status().get("skill_levels", [])
	var s7 := int(sk_c[7])
	var merit_c := int(gs.get_status().get("merit", 0))
	var exp_gain1 := 1 if s7 < ConstsRef.SKILL_CAP else 0
	var exp_merit1 := (s7 + 1) * 500 if s7 < ConstsRef.SKILL_CAP else 0
	var exp_final1: int = mini(merit_c + exp_merit1, ConstsRef.MERIT_CAP)
	var r1: Dictionary = gs.train_mode(1, 1, [0])
	check(int(r1.get("gains", []).size()) == exp_gain1, "mode1 增益数 = %d (got %d)" % [exp_gain1, r1.get("gains", []).size()])
	check(int(gs.get_status().get("merit", 0)) == exp_final1, "mode1 功勲累计正确 (got %d, exp %d)" % [gs.get_status().get("merit", 0), exp_final1])

	# —— 4) 五维提升（mode3/5/6/4），确定 +1 不计功勲 ——
	gs.start_new_game(13)
	var fo_d: Dictionary = gs.get_status().get("forces", {})
	var m0 := int(fo_d.get("martial", 0))
	var merit_d := int(gs.get_status().get("merit", 0))
	var r3: Dictionary = gs.train_mode(3, 1, [])
	var exp_m := 1 if m0 < ConstsRef.FORCE_CAP else 0
	check(int(r3.get("gains", []).size()) == exp_m, "mode3 武力增益 = %d" % exp_m)
	check(int(gs.get_status().get("forces", {}).get("martial", 0)) == m0 + exp_m, "武力 = %d (got %d)" % [m0 + exp_m, gs.get_status().get("forces", {}).get("martial", 0)])
	check(int(gs.get_status().get("merit", 0)) == merit_d, "五维提升不计功勲（与原值相等）")

	gs.start_new_game(13)
	var fo_e: Dictionary = gs.get_status().get("forces", {})
	var ch0 := int(fo_e.get("charm", 0))
	var r5: Dictionary = gs.train_mode(5, 1, [])
	var exp_ch := 1 if ch0 < ConstsRef.FORCE_CAP else 0
	check(int(gs.get_status().get("forces", {}).get("charm", 0)) == ch0 + exp_ch, "mode5 魅力 +1 生效")

	gs.start_new_game(13)
	var fo_f: Dictionary = gs.get_status().get("forces", {})
	var dp0 := int(fo_f.get("diplomacy", 0))
	var r6: Dictionary = gs.train_mode(6, 1, [])
	var exp_dp := 1 if dp0 < ConstsRef.FORCE_CAP else 0
	check(int(gs.get_status().get("forces", {}).get("diplomacy", 0)) == dp0 + exp_dp, "mode6 外交 +1 生效")

	# 读书 mode4：rand_vals=[0]→内政(domestic)；[1]→统御(lead)
	gs.start_new_game(13)
	var fo_g: Dictionary = gs.get_status().get("forces", {})
	var dom0 := int(fo_g.get("domestic", 0))
	var r4a: Dictionary = gs.train_mode(4, 1, [0])
	var exp_dom := 1 if dom0 < ConstsRef.FORCE_CAP else 0
	check(int(gs.get_status().get("forces", {}).get("domestic", 0)) == dom0 + exp_dom, "mode4 rand=0 → 内政 +1")
	gs.start_new_game(13)
	var fo_h: Dictionary = gs.get_status().get("forces", {})
	var lead0 := int(fo_h.get("lead", 0))
	var r4b: Dictionary = gs.train_mode(4, 1, [1])
	var exp_lead := 1 if lead0 < ConstsRef.FORCE_CAP else 0
	check(int(gs.get_status().get("forces", {}).get("lead", 0)) == lead0 + exp_lead, "mode4 rand=1 → 统御 +1")

	# —— 5) 什么也不做(mode7) → 早退，无增益无费 ——
	gs.start_new_game(13)
	var money_m := int(gs.get_status().get("money", 0))
	var day_m := int(gs.get_status().get("day", 1))
	var r7: Dictionary = gs.train_mode(7, 1, [])
	check(r7.get("ok", false) and int(r7.get("gains", []).size()) == 0, "mode7 早退 无增益")
	check(int(gs.get_status().get("money", 0)) == money_m, "mode7 不计费")
	check(int(gs.get_status().get("day", 1)) == day_m + 1, "mode7 仅推进 1 天")

	# —— 6) 天数/花费上限 ——
	gs.start_new_game(13)
	var r_big: Dictionary = gs.train_mode(0, 999, [])   # 超 day_cap
	check(not r_big.get("ok", false) and r_big.get("reason", "") == "exceeds_cap", "超天数上限 → exceeds_cap (got %s)" % r_big.get("reason",""))
	# 体力不足
	gs.start_new_game(13)
	var r_sta: Dictionary = gs.train_mode(3, 25, [])     # 25*5=125 > 体力上限
	check(not r_sta.get("ok", false) and r_sta.get("reason", "") == "low_stamina", "体力不足 → low_stamina (got %s)" % r_sta.get("reason",""))

	# —— 7) 功勲封顶 60000 + 技能封顶不溢出 ——
	gs.start_new_game(13)
	var skp: Array = gs.get_status().get("skill_levels", [])
	var s5p := int(skp[5])
	# 反复 mode2 直到兵法封顶，累计功勲不应超 60000，封顶后不再增益
	var guard := 0
	while guard < 20:
		var rr: Dictionary = gs.train_mode(2, 1, [0])
		if int(rr.get("gains", []).size()) == 0:
			break
		guard += 1
	check(int(gs.get_status().get("skill_levels", [])[5]) <= ConstsRef.SKILL_CAP, "兵法 封顶 ≤ 3 (got %d)" % gs.get_status().get("skill_levels", [])[5])
	check(int(gs.get_status().get("merit", 0)) <= ConstsRef.MERIT_CAP, "功勲 封顶 ≤ 60000 (got %d)" % gs.get_status().get("merit", 0))
	# 封顶后再训练不再增益
	var merit_cap := int(gs.get_status().get("merit", 0))
	var r_cap: Dictionary = gs.train_mode(2, 1, [0])
	check(int(r_cap.get("gains", []).size()) == 0 and int(gs.get_status().get("merit", 0)) == merit_cap, "封顶后 mode2 不再增益/不加功勲")

	# —— 8) 12 主命派发 + 城资源覆盖层隔离 ——
	gs.start_new_game(13)
	var cid: int = int(gs.get_status().get("city", 255))
	check(cid != 255, "主角有居城 id=%d" % cid)
	var base_castle: Dictionary = gd.get_castle(cid)
	var base_shikin: int = int(base_castle.get("shikin", 0))
	var base_gunryo: int = int(base_castle.get("gunryo", 0))
	check(gs.COMMAND_NAMES.size() == 12, "主命表 12 项")
	# 逐条执行，校验 documented delta 与月推进，且 GameData 原表不被污染
	var prev_month: int = int(gs.get_status().get("month", 1))
	for cmd in range(12):
		var before: Dictionary = gs.get_effective_castle(cid)
		var rc: Dictionary = gs.issue_command(cmd)
		check(rc.get("ok", false), "主命 #%d %s 执行成功 (reason=%s)" % [cmd, gs.COMMAND_NAMES[cmd], rc.get("reason","")])
		var deltas: Dictionary = rc.get("deltas", {})
		var after: Dictionary = gs.get_effective_castle(cid)
		for f in deltas.keys():
			var exp_v: int = int(before.get(f, 0)) + int(deltas[f])
			check(int(after.get(f, 0)) == exp_v, "主命#%d %s.%s = %d (got %d)" % [cmd, gs.COMMAND_NAMES[cmd], f, exp_v, after.get(f, 0)])
		# 月推进
		var now_month: int = int(gs.get_status().get("month", 1))
		check(now_month == (prev_month % 12) + 1, "主命#%d 推进 1 月 (%d→%d)" % [cmd, prev_month, now_month])
		prev_month = now_month
	# 原表隔离：GameData 城 shikin 仍为初始值
	check(int(gd.get_castle(cid).get("shikin", 0)) == base_shikin, "GameData 原表 shikin 未被污染 (%d)" % base_shikin)
	check(int(gd.get_castle(cid).get("gunryo", 0)) == base_gunryo, "GameData 原表 gunryo 未被污染 (%d)" % base_gunryo)

	# —— 9) 资格判定接口 ——
	gs.start_new_game(13)
	check(gs.can_train(2, -1) == true, "无师 可修行")
	check(gs.can_train(99) == false, "非法 mode 资格判定=false")

	# —— 收尾 ——
	print("")
	if _fails == 0:
		print("[M4 PASS] 全部断言通过 ✅")
		quit(0)
	else:
		push_error("[M4 FAIL] %d 项断言失败 ❌" % _fails)
		quit(1)
