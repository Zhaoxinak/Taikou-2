# _test_m5.gd — M5 職位晋升 无头校验（extends SceneTree）
#
# 覆盖：勲功阈值晋升 + 城主任命 + 大名继承 + 派生状态 + 覆盖层隔离。
# 规格对齐 promo2_ref.py / promote3_ref.py（二进制自校验 续63）。
# 运行：Godot_v4.7.1/Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_m5.gd

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
	process_frame.connect(_run, CONNECT_ONE_SHOT)

func _run() -> void:
	var gs = root.get_node("/root/GameState")
	var gd = root.get_node("/root/GameData")

	# —— 0) 开局（确保 GameData 已载入；清空所有覆盖层）——
	check(gs.start_new_game(13), "#13 织田信长 开局成功")

	# —— 1) 常量与查表 ——
	check(ConstsRef.RANK_NAMES == ["浪人", "步兵头", "队长", "侍大将", "部将", "家老", "宿老", "大名", "城主"],
		"職位 ladder 名表 0x50d850 = " + "/".join(ConstsRef.RANK_NAMES))
	check(gs.threshold_of(0) == -1 and gs.threshold_of(7) == -1, "浪人(0)/大名(7) 不在阈值表 → -1")
	check(gs.threshold_of(1) == 100 and gs.threshold_of(2) == 500 and gs.threshold_of(3) == 1500
		and gs.threshold_of(4) == 5000 and gs.threshold_of(5) == 10000 and gs.threshold_of(6) == 30000,
		"勲功阈值表 = 100/500/1500/5000/10000/30000")
	check(gs.stipend_of(1) == 1 and gs.stipend_of(2) == 10 and gs.stipend_of(3) == 30
		and gs.stipend_of(4) == 50 and gs.stipend_of(5) == 100 and gs.stipend_of(6) == 200,
		"俸禄表 = 1/10/30/50/100/200")
	# rank_from_merit 边界（0x49fc60）
	check(gs.rank_from_merit(99) == 1 and gs.rank_from_merit(100) == 1, "勲功 99/100 → 職位 1（兜底）")
	check(gs.rank_from_merit(499) == 1 and gs.rank_from_merit(500) == 2, "勲功 499→1, 500→2")
	check(gs.rank_from_merit(1499) == 2 and gs.rank_from_merit(1500) == 3, "勲功 1499→2, 1500→3")
	check(gs.rank_from_merit(29999) == 5 and gs.rank_from_merit(30000) == 6, "勲功 29999→5, 30000→6")
	check(gs.rank_from_merit(99999) == 6, "勲功 99999 → 職位 6（封顶）")

	# —— 2) 勲功阈值晋升（try_promote）——
	# 2a 勲功不足 → 不晋升
	gs.start_new_game(13)
	gs._rank_override[100] = 2
	gs._merit_override[100] = 499
	var pa: Dictionary = gs.try_promote(100, 7)
	check(not pa.get("ok", false) and pa.get("reason", "") == "merit_low",
		"勲功 499 < 1500 → 不晋升（reason=merit_low）")
	# 2b 勲功达标 → 晋升侍大将(3) + 俸禄 30
	gs._merit_override[100] = 1500
	var pb: Dictionary = gs.try_promote(100, 7)
	check(pb.get("ok", false) and int(pb.get("to", 0)) == 3 and gs._ov_rank(100) == 3,
		"勲功 1500 >= 1500 → 晋升侍大将(3)")
	check(gs._ov_salary(100) == 30, "俸禄随職位更新 = 30（表值 30）")
	# 2c 不得达到主君職位（主君 家老=5，部将4 → new 5 不 < 5）
	gs.start_new_game(13)
	gs._rank_override[100] = 4
	gs._merit_override[100] = 99999
	var pc: Dictionary = gs.try_promote(100, 5)
	check(not pc.get("ok", false) and pc.get("reason", "") == "not_below_lord",
		"主君家老(5)：部将(4)→5 不允许（须严格小于主君）")
	# 2d 主君 宿老(6)，部将(4)→5 允许
	var pd: Dictionary = gs.try_promote(100, 6)
	check(pd.get("ok", false) and int(pd.get("to", 0)) == 5, "主君宿老(6)：部将(4)→5(家老) 允许")
	# 2e 同城规避
	gs.start_new_game(13)
	gs._rank_override[200] = 2
	gs._merit_override[200] = 60000
	gs._city_override[200] = 7
	gs._rank_override[300] = 3        # self 非浪人
	gs._city_override[300] = 7        # self 与 target 同城
	var pe: Dictionary = gs.try_promote(200, 7, 300)
	check(not pe.get("ok", false) and pe.get("reason", "") == "same_city", "同城且我非浪人 → 跳过晋升")
	gs._city_override[300] = 9        # 不同城
	var pe2: Dictionary = gs.try_promote(200, 7, 300)
	check(pe2.get("ok", false) and int(pe2.get("to", 0)) == 3, "不同城 → 正常晋升")

	# —— 3) 城主任命（can_appoint / appoint）——
	gs.start_new_game(13)
	gs._rank_override[100] = 4        # 部将，低于门槛
	gs._skill_override[100] = [0,0,0,0,0,0,0,0,1,0]   # 礼法(索引8)=1
	var ca1: Dictionary = gs.can_appoint_castle_lord(100, 66)
	check(not ca1.get("ok", false) and ca1.get("reason", "") == "rank_too_low", "rank=4 部将 → 拒绝(门槛>4)")
	gs._rank_override[100] = 5        # 家老，过门槛
	var ca2: Dictionary = gs.can_appoint_castle_lord(100, 66)
	check(ca2.get("ok", false), "rank=5 家老 + 礼法具备 + 城有效 → 通过")
	# 礼法不足
	gs._skill_override[100] = [0,0,0,0,0,0,0,0,0,0]
	var ca3: Dictionary = gs.can_appoint_castle_lord(100, 66)
	check(not ca3.get("ok", false) and ca3.get("reason", "") == "no_etiquette", "礼法(byte11&3)==0 → no_etiquette")
	# 城无效
	gs._skill_override[100] = [0,0,0,0,0,0,0,0,1,0]
	var ca4: Dictionary = gs.can_appoint_castle_lord(100, 999)
	check(not ca4.get("ok", false) and ca4.get("reason", "") == "no_castle", "城无效(999) → no_castle")
	# 任命生效 + 派生状态
	gs._skill_override[100] = [0,0,0,0,0,0,0,0,1,0]
	var ap: Dictionary = gs.appoint_castle_lord(100, 66)
	check(ap.get("ok", false) and int(gs.get_castle_lord(66)) == 100, "任命后 城66 城主 = 100")
	check(gs.is_castle_lord(100), "is_castle_lord(100) == true")
	check(int(gs._ov_city(100)) == 66, "任命后 武将居城更新为 66")
	# 原表不被污染：GameData 城 66 的 f0a 仍为初始值
	check(int(gd.get_castle(66).get("f0a", -1)) != 100, "GameData 原表 f0a 未被污染（仍为初始城主）")

	# —— 4) 大名继承（inherit_daimyo）——
	gs.start_new_game(13)
	var inh: Dictionary = gs.inherit_daimyo(13, 257, [
		{"pid": 16, "father_id": 13, "rand_val": 5, "loyalty_base": 10},   # 嫡系
		{"pid": 1,  "father_id": 99, "rand_val": 5, "loyalty_base": 40},   # 非嫡系
		{"pid": 300, "father_id": 50, "rand_val": 0, "loyalty_base": 0},   # 非嫡系 + 下限
	])
	check(inh.get("ok", false), "inherit_daimyo 执行成功")
	check(int(inh.get("heir_rank", -1)) == 7, "继承人升大名(7)")
	check(int(inh.get("heir_merit", -1)) == 60000, "继承人勲功拉满 60000")
	# 嫡系(父ID==死亡者) → 宿老(6) + 忠诚 100
	var ret16: Dictionary = {}
	for r in inh.get("retainers", []):
		if int(r.get("pid", -1)) == 16:
			ret16 = r
	check(int(ret16.get("rank", -1)) == 6 and int(ret16.get("loyalty", -1)) == 100, "嫡系 → 宿老(6) + 忠诚100")
	# 非嫡系 → 忠诚 = rand + base
	var ret1: Dictionary = {}
	for r in inh.get("retainers", []):
		if int(r.get("pid", -1)) == 1:
			ret1 = r
	check(int(ret1.get("loyalty", -1)) == 45, "非嫡系忠诚 = rand+base = 45 (got %d)" % int(ret1.get("loyalty", -1)))
	# 忠诚下限保护
	var ret300: Dictionary = {}
	for r in inh.get("retainers", []):
		if int(r.get("pid", -1)) == 300:
			ret300 = r
	check(int(ret300.get("loyalty", -1)) == 30, "忠诚下限保护 <30 → 30 (got %d)" % int(ret300.get("loyalty", -1)))

	# —— 5) 主角状态面板反映有效職位/俸禄/居城 + 城主显示 ——
	gs.start_new_game(16)   # 木下藤吉郎（初始 rank 1）
	gs._rank_override[16] = 5
	gs._salary_override[16] = 100
	gs._merit_override[16] = 20000
	gs._city_override[16] = 66
	var st: Dictionary = gs.get_status()
	check(int(st.get("rank", -1)) == 5, "主角有效職位 = 5 (got %d)" % int(st.get("rank", -1)))
	check(st.get("rank_name", "") == "家老", "主角職位名 = 家老 (got %s)" % st.get("rank_name", ""))
	check(int(st.get("salary", -1)) == 100, "主角有效俸禄 = 100")
	check(int(st.get("city", -1)) == 66, "主角有效居城 = 66")
	check(int(st.get("merit", -1)) == 20000, "主角有效勲功 = 20000")
	# 任命为城主后，面板显示"城主"（需 礼法!=0 满足门槛）
	gs._skill_override[16] = [0,0,0,0,0,0,0,0,2,0]   # 礼法(索引8)=2
	var ap2: Dictionary = gs.appoint_castle_lord(16, 66)
	check(ap2.get("ok", false), "主角任命为城主(66) 成功（reason=%s）" % ap2.get("reason", ""))
	var st2: Dictionary = gs.get_status()
	check(st2.get("is_castle_lord", false) == true, "面板 is_castle_lord = true")
	check(st2.get("rank_name", "") == "城主", "城主显示覆盖：rank_name = 城主 (got %s)" % st2.get("rank_name", ""))
	# 重开局复位
	gs.start_new_game(16)
	var st3: Dictionary = gs.get_status()
	check(int(st3.get("rank", -1)) == 1 and int(st3.get("salary", -1)) == 1 and st3.get("is_castle_lord", true) == false,
		"重开局覆盖层复位（rank=1, salary=1, 非城主）")

	# —— 收尾 ——
	print("")
	if _fails == 0:
		print("[M5 PASS] 全部断言通过 ✅")
		quit(0)
	else:
		push_error("[M5 FAIL] %d 项断言失败 ❌" % _fails)
	quit(1)
