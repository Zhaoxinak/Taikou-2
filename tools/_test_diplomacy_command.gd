# _test_diplomacy_command.gd — 外交类主命（7..11）真实接线 diplomacy.gd 的无头校验
#
# 覆盖：can_dispatch 目标国筛选（按主从）/ friendly·pressure 关系写入 / 0x4b9250 功勋 /
#       朝廷·情报·谋略分支 / 非法目标 / 被拒不耗时。
# 运行：Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_diplomacy_command.gd

extends SceneTree

const DiplomacyRef = preload("res://src/core/diplomacy.gd")

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
	var gs = root.get_node("/root/GameState")

	check(gs.start_new_game(13), "#13 织田信长 开局成功")
	var my := int(gs.protagonist_province())
	check(my == 16, "主角所在省 = 16（尾張，got %d）" % my)
	check(int(gs.province_city_count(16)) == 6, "尾張城数 = 6（got %d）" % int(gs.province_city_count(16)))

	# —— 1) 进贡（cmd7 → work9 友好）：空白主从可派，成功 → 同盟+亲密+功勋600+资金-200 ——
	var r: Dictionary = gs.issue_command(7, {"target_province": 0})
	check(bool(r.get("ok", false)), "进贡 #0 成功")
	var d: Dictionary = r.get("diplomacy", {})
	check(int(d.get("mv_after", -1)) == 1, "主从 → 1 同盟（got %s）" % str(d.get("mv_after")))
	check(int(d.get("dipl_after", -1)) == 1, "外交 → 1 亲密（work_type=0 ⇒ lv=diff(1,0)=1）")
	check(int(r.get("merit_gain", 0)) == 600, "功勋 = 600（got %s）" % str(r.get("merit_gain")))
	check(int(r.get("deltas", {}).get("shikin", 0)) == -200, "资金占位 delta -200 保留")
	check(bool(r.get("month_advanced", false)), "成功耗时 1 月")

	# —— 2) 同目标再进贡：主从=同盟 ⇒ can_dispatch(1,1)=false ⇒ 拒绝且不耗时 ——
	var m_before := int(gs.get_status().get("month", 0))
	var r2: Dictionary = gs.issue_command(7, {"target_province": 0})
	check(not bool(r2.get("ok", false)), "对同盟国再进贡被拒")
	check(str(r2.get("reason", "")) == "dispatch_blocked", "reason=dispatch_blocked")
	check(int(gs.get_status().get("month", 0)) == m_before, "被拒不推进月份")

	# —— 3) 威吓（cmd8 → work10 高压）：成功 → 支配+功勋1000（0x47b5f0 恒成）——
	# 有向镜像约定（同 _test_diplomacy [8]）：mv(目标→我)=3 支配；我→目标 镜像=2
	var r3: Dictionary = gs.issue_command(8, {"target_province": 5})
	check(bool(r3.get("ok", false)), "威吓 #5 成功")
	var d3: Dictionary = r3.get("diplomacy", {})
	check(int(d3.get("mv_after", -1)) == 2, "我→目标 视角镜像 = 2（got %s）" % str(d3.get("mv_after")))
	check(int(gs.diplomacy.get_master_vassal(5, my)) == 3, "目标→我 视角 = 3 支配（结算写入向）")
	check(int(r3.get("merit_gain", 0)) == 1000, "功勋 = 1000")

	# —— 4) 对从属国威吓：主从=2 ⇒ can_dispatch(0,2)=false ——
	gs.diplomacy.set_master_vassal(my, 7, 2)
	var r4: Dictionary = gs.issue_command(8, {"target_province": 7})
	check(not bool(r4.get("ok", false)) and str(r4.get("reason", "")) == "dispatch_blocked",
		"对从属国威吓被拒（高压拒{2,3}）")

	# —— 5) 收集情报（cmd10 → work12）：任何主从可派；功勋 = 城数*(lv+5)+100 ——
	var cc := int(gs.province_city_count(3))
	var r5: Dictionary = gs.issue_command(10, {"target_province": 3})
	check(bool(r5.get("ok", false)), "收集情报 #3 成功（无条件可派）")
	check(int(r5.get("merit_gain", 0)) == cc * 6 + 100,
		"情报功勋 = 城数%d*(1+5)+100 = %d（got %s）" % [cc, cc * 6 + 100, str(r5.get("merit_gain"))])
	var d5: Dictionary = r5.get("diplomacy", {})
	check(int(d5.get("mv_after", -1)) == int(d5.get("mv_before", -2)),
		"情报不改主从関係")
	# g10/g0d 覆写：lv = min((g10&3) + g0d/20 + 1, 7) = min(3+5+1,7)=7 ⇒ 城数*12+100
	var r5b: Dictionary = gs.issue_command(10, {"target_province": 4, "g10": 3, "g0d": 100})
	var cc4 := int(gs.province_city_count(4))
	check(int(r5b.get("merit_gain", 0)) == cc4 * 12 + 100,
		"情报功勋（g10=3,g0d=100 ⇒ lv=7）= 城数%d*12+100 = %d" % [cc4, cc4 * 12 + 100])

	# —— 6) 朝廷工作（cmd9 → work11）：无关系写入；功勋 800/1000 ——
	var r6: Dictionary = gs.issue_command(9, {"target_province": 20})
	check(bool(r6.get("ok", false)), "朝廷工作成功")
	check(int(r6.get("merit_gain", 0)) == 800, "无官位功勋 = 800")
	var d6: Dictionary = r6.get("diplomacy", {})
	check(int(d6.get("dipl_after", -1)) == int(d6.get("dipl_before", -2)), "朝廷不改外交関係")
	var r6b: Dictionary = gs.issue_command(9, {"target_province": 20, "got_rank": true})
	check(int(r6b.get("merit_gain", 0)) == 1000, "得官位功勋 = 1000")

	# —— 7) 谋略（cmd11 → work13）：无静态模型 → 诚实占位、不耗时 ——
	var m2 := int(gs.get_status().get("month", 0))
	var r7: Dictionary = gs.issue_command(11, {"target_province": 30})
	check(not bool(r7.get("ok", false)) and str(r7.get("reason", "")) == "work_not_modeled",
		"谋略 work_not_modeled（RE 未逆，不发明）")
	check(int(gs.get_status().get("month", 0)) == m2, "谋略占位不推进月份")

	# —— 8) 非法目标 ——
	var r8: Dictionary = gs.issue_command(7, {"target_province": my})
	check(not bool(r8.get("ok", false)) and str(r8.get("reason", "")) == "bad_target", "目标=自国被拒")
	var r9: Dictionary = gs.issue_command(7, {"target_province": 99})
	check(not bool(r9.get("ok", false)) and str(r9.get("reason", "")) == "bad_target", "目标越界被拒")
	var r10: Dictionary = gs.issue_command(7, {})
	check(not bool(r10.get("ok", false)) and str(r10.get("reason", "")) == "bad_target", "缺目标被拒")

	# —— 9) work_type 覆写：friendly work_type=3 ⇒ lv=2（同 _test_diplomacy [8]：type2→0 / type3→2）——
	gs.diplomacy.set_master_vassal(my, 8, 0)   # 还原空白
	var r11: Dictionary = gs.issue_command(7, {"target_province": 8, "work_type": 3})
	check(int(r11.get("diplomacy", {}).get("dipl_after", -1)) == 2,
		"work_type=3 ⇒ 外交=2（opts 覆写生效）")

	print("RESULT: %d/%d checks passed" % [_pass, _pass + _fail])
	quit(1 if _fail > 0 else 0)
