# _test_models.gd — 数据模型补全校验（extends SceneTree）
#
# 覆盖：Castle / Province / Skill / Battle / Item 五类强类型模型
#       （load_from_dict 字段映射正确 + 便捷方法可用 + 计数齐整）。
# 运行：Godot_v4.7.1/Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_models.gd

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
	var t0 := Time.get_ticks_msec()
	var gd = root.get_node("/root/GameData")

	# —— 1) Castle ——
	var c0: Castle = gd.get_castle_obj(0)
	check(c0.id == 0, "Castle(0).id == 0")
	check(c0.name == "三户", "Castle(0).name == 三户 (got %s)" % c0.name)
	check(c0.troops == 2000, "Castle(0).troops(gunryo) == 2000 (got %d)" % c0.troops)
	check(c0.gold == 1200, "Castle(0).gold(shikin) == 1200 (got %d)" % c0.gold)
	check(c0.lord == 19, "Castle(0).lord(f0a) == 19 (got %d)" % c0.lord)
	check(c0.has_lord(), "Castle(0).has_lord() == true")
	check(c0.province_id == 0, "Castle(0).province_id == 0")
	check(c0.people == 130, "Castle(0).people(minkok) == 130")
	check(c0.produ == 70, "Castle(0).produ(seisan) == 70")
	check(c0.rice == 600, "Castle(0).rice(kome) == 600")
	check(c0.keep_type == 1292, "Castle(0).keep_type(castle_type) == 1292")
	check(c0.farmer == 8, "Castle(0).farmer(nousang) == 8")
	check(c0.status == 5, "Castle(0).status(f09) == 5")
	check(c0.unused == ConstsRef.SENTINEL_FFFF, "Castle(0).unused == 0xFFFF")
	# 与原始 dict 一致性（模型不污染、字段同源）
	var cd: Dictionary = gd.get_castle(0)
	check(int(cd.get("gunryo", -1)) == c0.troops, "Castle(0) 模型与 dict gunryo 一致")
	# 全量 200 城可建模无异常
	var c_ok := 0
	for i in range(ConstsRef.CASTLE_COUNT):
		var cc: Castle = gd.get_castle_obj(i)
		if cc.id == i and cc.name != "":
			c_ok += 1
	check(c_ok == ConstsRef.CASTLE_COUNT, "全部 %d 城可建模 (got %d)" % [ConstsRef.CASTLE_COUNT, c_ok])

	# —— 2) Province ——
	var p0: Province = gd.get_province_obj(0)
	check(p0.id == 0, "Province(0).id == 0")
	check(p0.name == "北陆奥", "Province(0).name == 北陆奥 (got %s)" % p0.name)
	var p_ok := 0
	for i in range(ConstsRef.PROVINCE_COUNT):
		var pp: Province = gd.get_province_obj(i)
		if pp.id == i:
			p_ok += 1
	check(p_ok == ConstsRef.PROVINCE_COUNT, "全部 %d 国可建模 (got %d)" % [ConstsRef.PROVINCE_COUNT, p_ok])

	# —— 3) Skill（目录项）——
	var s0: Skill = gd.get_skill_obj(0)
	check(s0.id == 0 and s0.name == "口才", "Skill(0) == 口才")
	check(s0.cap == ConstsRef.SKILL_CAP, "Skill cap == SKILL_CAP(%d)" % ConstsRef.SKILL_CAP)
	var s3: Skill = gd.get_skill_obj(3)
	check(s3.name == "剑术", "Skill(3) == 剑术 (got %s)" % s3.name)
	check(s0.is_maxed(3) and not s0.is_maxed(2), "Skill.is_maxed(level) 阈值正确")

	# —— 4) Battle ——
	var b0: Battle = gd.get_battle_obj(0)
	check(b0.id == 0, "Battle(0).id == 0")
	check(b0.group_count() > 0, "Battle(0).group_count > 0 (got %d)" % b0.group_count())
	check(b0.group_unit_count(0) > 0, "Battle(0) 组0 有出场单位 (%d)" % b0.group_unit_count(0))
	check(b0.total_units() > 0, "Battle(0) 总单位数 > 0 (%d)" % b0.total_units())
	check(b0.terrain.size() > 0, "Battle(0).terrain 已载入 (%d)" % b0.terrain.size())

	# —— 5) Item（data/items.json, 189 件，27→8 类目归并）——
	var it0: Item = gd.get_item_obj(0)
	check(it0.id == 0, "Item(0).id == 0")
	check(it0.name.begins_with("三刀屋"), "Item(0) 名称前缀 三刀屋 (got %s)" % it0.name)
	check(it0.def_cat == 5, "Item(0).def_cat == 5")
	check(it0.cat == 7, "Item(0).cat(主池) == 7")
	check(it0.cat_name == "茶具", "Item(0).cat_name == 茶具 (got %s)" % it0.cat_name)
	check(it0.val == 70 and it0.tier == 4, "Item(0).val==70 tier==4")
	check(it0.is_tea() and not it0.is_weapon(), "Item(0).is_tea() 便捷方法正确")
	var it_last: Item = gd.get_item_obj(188)
	check(it_last.id == 188 and it_last.name == "斗战经", "Item(188) == 斗战经")
	check(it_last.cat == 1 and it_last.cat_name == "书籍", "Item(188) 类目 书籍")
	# 全量计数
	var i_ok := 0
	for i in range(189):
		var ii: Item = gd.get_item_obj(i)
		if ii.id == i and ii.cat_name != "?" and ii.name != "":
			i_ok += 1
	check(i_ok == 189, "全部 189 物品可建模且类目有效 (got %d)" % i_ok)
	check(gd.get_item(188).size() > 0, "GameData.get_item(188) dict 可查")

	# —— 收尾 ——
	var dt := Time.get_ticks_msec() - t0
	if _fails == 0:
		print("\n[ALL PASS] 数据模型补全校验通过（%d ms）" % dt)
		quit(0)
	else:
		push_error("\n[%d FAIL] 数据模型校验存在失败" % _fails)
		quit(1)
