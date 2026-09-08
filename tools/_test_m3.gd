# _test_m3.gd — M3 GameState 无头校验（extends SceneTree）
#
# 覆盖：开局校验 / 状态读取 / 修行（封顶+耗体力+推月）/ 休养 / 跨年滚动 / 缓存不被污染。
# 运行：Godot_v4.7.1/Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_m3.gd

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
	# ⚠️ --script 模式下 _initialize 时 autoload 尚未进树，
	#    挂到首个 process_frame 再跑断言（此时 GameState/GameData 已 ready）。
	process_frame.connect(_run, CONNECT_ONE_SHOT)

func _run() -> void:
	var t0 := Time.get_ticks_msec()
	var gs = root.get_node("/root/GameState")
	var gd = root.get_node("/root/GameData")

	# —— 1) 开局校验 ——
	check(not gs.start_new_game(0), "非可选武将 #0 林通胜 被拒绝")
	check(not gs.start_new_game(9999), "不存在武将 #9999 被拒绝")
	check(not gs.is_started(), "拒绝后仍未开局")
	check(gs.start_new_game(13), "#13 织田信长 开局成功")
	check(gs.is_started(), "开局状态成立")

	# —— 2) 状态读取 ——
	var st: Dictionary = gs.get_status()
	check(st.get("name", "") == "织田信长", "姓名 = 织田信长（got %s）" % st.get("name"))
	var f: Dictionary = st.get("forces", {})
	check(int(f.get("lead", 0)) == 96 and int(f.get("martial", 0)) == 85
		and int(f.get("domestic", 0)) == 92 and int(f.get("diplomacy", 0)) == 99
		and int(f.get("charm", 0)) == 90,
		"五维 = 96/85/92/99/90 (got %s)" % [f])
	check(st.get("rank_name", "") == "大名", "職位 = 大名 (got %s)" % st.get("rank_name"))
	check(int(st.get("year", 0)) == 1560 and int(st.get("month", 0)) == 1, "开局 1560 年 1 月")
	var skills0: Array = st.get("skill_levels", [])
	check(skills0.size() == 10, "技能数组 10 项")
	var stamina0: int = int(st.get("stamina", 0))
	var smax: int = int(st.get("stamina_max", 0))
	check(stamina0 == smax and smax > 0, "开局体力 = 上限 (%d/%d)" % [stamina0, smax])

	# 缓存基线：GameData 原表技能数组（污染检查用）
	var cache0: Array = (gd.get_officer(13).get("skill_levels", []) as Array).duplicate()

	# —— 3) 修行：非封顶技能 +1、耗体力、推 1 月 ——
	var idx := -1
	for k in skills0.size():
		if int(skills0[k]) < ConstsRef.SKILL_CAP:
			idx = k
			break
	check(idx >= 0, "存在可修行技能（idx=%d）" % idx)
	var lv_before: int = int(skills0[idx])
	var r1: Dictionary = gs.train_skill(idx)
	check(bool(r1.get("ok", false)), "修行 idx=%d 成功" % idx)
	var st1: Dictionary = gs.get_status()
	check(int(st1["skill_levels"][idx]) == lv_before + 1, "技能 %s %d→%d"
		% [ConstsRef.SKILL_NAMES[idx], lv_before, int(st1["skill_levels"][idx])])
	var expect_stamina: int = clampi(stamina0 - gs.TRAIN_STAMINA_COST + gs.MONTH_RECOVER, 0, smax)
	check(int(st1.get("stamina", 0)) == expect_stamina,
		"体力 = -20 耗 +15 月回 = %d (got %d)" % [expect_stamina, int(st1.get("stamina", 0))])
	var expect_m: int = 2
	check(int(st1.get("month", 0)) == expect_m, "推进到 2 月 (got %d)" % int(st1.get("month", 0)))
	check(st1.get("name", "") == "织田信长" and st1.get("rank_name", "") == "大名", "修行后状态其余字段不漂移")

	# 缓存不被污染：原表 skill_levels 仍等于开局值
	var cache1: Array = (gd.get_officer(13).get("skill_levels", []) as Array).duplicate()
	check(cache1 == cache0, "GameData 原表缓存未被修行污染")

	# —— 4) 修行封顶：反复修行同一技能，等级不超过 3 ——
	var capped_ok := true
	var lv := int(gs.get_status()["skill_levels"][idx])
	while lv < ConstsRef.SKILL_CAP:
		var r: Dictionary = gs.train_skill(idx)
		if not bool(r.get("ok", false)):
			capped_ok = false
			break
		lv = int(gs.get_status()["skill_levels"][idx])
	check(capped_ok and lv == ConstsRef.SKILL_CAP, "反复修行至封顶 level=3（途中不失败）")
	# 低体力守卫：确定性注入（覆盖层直写）。
	# 注：按当前参数（耗20/月回15，净-5）且信长修行容量仅14次，修行本身耗不尽体力——
	#     体力约束留给后续引入其他主命后自然生效，这里只验证守卫分支本身。
	gs._stamina_override[13] = gs.TRAIN_STAMINA_COST - 1
	# idx0 已被上一段练满，换任一未封顶技能来触发耗体分支
	var idx2 := -1
	var cur: Array = gs.get_status()["skill_levels"]
	for k in cur.size():
		if int(cur[k]) < ConstsRef.SKILL_CAP:
			idx2 = k
			break
	var r_low: Dictionary = gs.train_skill(idx2)
	check(String(r_low.get("reason", "")) == "low_stamina",
		"体力不足时修行被拒（low_stamina, reason=%s）" % r_low.get("reason"))

	# —— 5) 跨年滚动 ——
	gs.start_new_game(13)
	for i in 12:
		gs.advance_month()
	var st2: Dictionary = gs.get_status()
	check(int(st2.get("year", 0)) == 1561 and int(st2.get("month", 0)) == 1,
		"12 次推月 → 1561 年 1 月 (got %d/%d)" % [int(st2.get("year", 0)), int(st2.get("month", 0))])

	# —— 6) 重开局复位 ——
	check(gs.start_new_game(16), "#16 木下藤吉郎 重新开局")
	var st3: Dictionary = gs.get_status()
	check(st3.get("name", "") == "木下藤吉郎" and st3.get("rank_name", "") == "步兵头",
		"换主角后状态复位（got %s/%s）" % [st3.get("name"), st3.get("rank_name")])
	check(int(st3.get("year", 0)) == 1560 and int(st3.get("month", 0)) == 1, "重开局回到 1560/1")

	print("")
	if _fails > 0:
		push_error("M3 校验失败 %d 项" % _fails)
		quit(1)
	print("[ok] M3 GameState 全部通过（用时 %.0f ms）" % [float(Time.get_ticks_msec() - t0)])
	quit(0)
