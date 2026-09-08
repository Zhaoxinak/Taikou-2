# _test_shop.gd — M7 店铺/商业核心逻辑无头校验（extends SceneTree）
#
# 复刻结构：src/core/shop.gd
# 比对参考实现：scripts/shop_record_head_ref.py（续247）
#              scripts/shop_npc_record_ref.py（续242：id→slot 表 / 关系值饱和）
#              scripts/msgx_text_tables.json['S8_dialogue_30x12B']（30 记录）
#
# 覆盖：30 记录加载与字段 / ID_SLOT_TABLE 30 字节 / JOB_NAMES(12) / 入店分发边界
#  (<30 有效, ≥30 空) / favor 饱和 cap100·floor1 / 买药÷50（含边界 49→0,50→1,500→10）
#  / slot→设施名映射。
#
# 运行：Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_shop.gd

extends SceneTree

const ShopRef = preload("res://src/core/shop.gd")

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
	var sh: RefCounted = ShopRef.new()
	var gs = root.get_node("/root/GameState")

	# ---- [1] 30 记录加载 + 字段完整性 ----
	check(sh.records.size() == 30, "载入 30 条店铺记录")
	var ok_fields: bool = true
	for r in sh.records:
		if not ("id" in r and "name_key" in r and "shop_msg" in r and "job" in r
				and "province" in r and "rank" in r and "favor" in r
				and "facility" in r and "progress" in r and "flags" in r
				and "talk" in r and "shop" in r and "slot" in r):
			ok_fields = false
	check(ok_fields, "每条记录含 12B 字段 + talk/shop/slot")

	# 记录 #0 / #11 / #28 / #29 关键字段
	var r0: Dictionary = sh.get_record(0)
	check(r0["name_key"] == 1000 and r0["shop_msg"] == 700, "记录#0 name_key=1000/shop_msg=700")
	check(r0["job"] == 0 and r0["province"] == 29 and r0["rank"] == 3, "记录#0 大商人/国29/rank3")
	check(r0["talk"] == "您哪位？", "记录#0 对话文本(MSGX 1000)")
	var r29: Dictionary = sh.get_record(29)
	check(r29["shop_msg"] == 65535, "记录#29 shop_msg=0xffff(闇商人)")
	check(r29["job"] == 11 and r29["slot"] == 12, "记录#29 神秘商人码/ slot=12")

	# ---- [2] ID_SLOT_TABLE 30 字节 ----
	check(ShopRef.ID_SLOT_TABLE.size() == 30, "ID_SLOT_TABLE 长度 = 30")
	var exp_slot: Array = [0,0,0,0,0, 1,2,2,2,3, 3,4,4,5,5,5,
		6,6,6,7,7, 8,8,8,9,9, 10,10,10,12]
	check(Array(ShopRef.ID_SLOT_TABLE) == exp_slot, "ID_SLOT_TABLE 全 30 字节 == 续242 A5 表")
	check(sh.slot_of(0) == 0 and sh.slot_of(5) == 1 and sh.slot_of(11) == 4, "slot_of 0/5/11 = 0/1/4")
	check(sh.slot_of(26) == 10 and sh.slot_of(29) == 12, "slot_of 26/29 = 10/12")
	check(sh.slot_of(30) == -1 and sh.slot_of(-1) == -1, "slot_of 越界 = -1")

	# ---- [3] JOB_NAMES(12) ----
	check(ShopRef.JOB_NAMES.size() == 12, "JOB_NAMES 长度 = 12")
	check(ShopRef.JOB_NAMES[0] == "大商人" and ShopRef.JOB_NAMES[11] == "神秘商人", "JOB_NAMES 首尾")
	check(sh.facility_name_of(0) == "大商人", "设施名#0(slot0 商家) = 大商人")
	check(sh.facility_name_of(11) == "传教士", "设施名#11(slot4 教会) = 传教士")
	check(sh.facility_name_of(26) == "名医", "设施名#26(slot10 医师) = 名医")
	check(sh.facility_name_of(29) == "闇商人(专属事件流)", "设施名#29 = 闇商人专属事件流")

	# ---- [4] 入店分发器边界（0x44e710 / 0x44e7d4）----
	check(not sh.enter_shop(0).is_empty(), "enter_shop(0) 有效")
	check(not sh.enter_shop(29).is_empty(), "enter_shop(29) 有效")
	check(sh.enter_shop(30).is_empty(), "enter_shop(30) 空(NULL)")
	check(sh.enter_shop(-1).is_empty(), "enter_shop(-1) 空(NULL)")
	# GameState 转发
	check(not gs.enter_shop(3).is_empty() and gs.enter_shop(30).is_empty(), "GameState.enter_shop 转发一致")

	# ---- [5] 关系值 favor 饱和运算 ----
	check(sh.favor_add(50, 30) == 80, "favor_add 50+30=80")
	check(sh.favor_add(90, 20) == 100, "favor_add 封顶 100 (90+20→100)")
	check(sh.favor_add(0, -5) == 0, "favor_add 地板 0 (0-5→0)")
	check(sh.favor_sub(10, 3) == 7, "favor_sub 10-3=7")
	check(sh.favor_sub(1, 5) == 1, "favor_sub floor1 (1-5→1)")
	check(sh.favor_set(150) == 100 and sh.favor_set(-10) == 0, "favor_set 钳 0..100")

	# ---- [6] 买药 ÷50（0x445679 魔数 0x51eb851f + sar4）----
	check(sh.medicine_doses(0) == 0, "买药 gold0 → 0 服")
	check(sh.medicine_doses(49) == 0, "买药 gold49 → 0 服(不足1服)")
	check(sh.medicine_doses(50) == 1, "买药 gold50 → 1 服")
	check(sh.medicine_doses(99) == 1, "买药 gold99 → 1 服")
	check(sh.medicine_doses(100) == 2, "买药 gold100 → 2 服")
	check(sh.medicine_doses(500) == 10, "买药 gold500 → 10 服")
	check(sh.medicine_doses(5000) == 100, "买药 gold5000 → 100 服")
	check(sh.medicine_cost(10) == 500, "买药 10 服 = 500 内单位")
	check(sh.can_buy_medicine(49) == false and sh.can_buy_medicine(50) == true, "买药门槛 gold>=50")

	# ---- 收尾 ----
	print("")
	if _fails == 0:
		print("[SHOP PASS] 全部断言通过 ✅")
		quit(0)
	else:
		push_error("[SHOP FAIL] %d 项断言失败 ❌" % _fails)
		quit(1)
