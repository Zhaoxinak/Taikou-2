# _test_castle_town.gd — 城下町经济/背包 单元测试（Godot 侧）
# 触发：Godot --headless --script res://tools/_test_castle_town.gd
# ⚠️ --script 模式下 autoload 不是全局标识符，必须 root.get_node("/root/GameState") 取。
extends SceneTree

const EconomyRef = preload("res://src/core/economy.gd")
const ShopRef = preload("res://src/core/shop.gd")

var _pass := 0
var _fail := 0
var gs                                  # /root/GameState
var gd                                  # /root/GameData

func money() -> int:
	return int(gs.get_status()["money"])

func chk(name: String, cond: bool, detail: String = "") -> void:
	if cond:
		_pass += 1
	else:
		_fail += 1
		print("  FAIL  %s%s" % [name, ("  (%s)" % detail) if detail != "" else ""])

func _run() -> void:
	gs = root.get_node("/root/GameState")
	gd = root.get_node("/root/GameData")

	chk("start_new_game(13)", gs.start_new_game(13))
	chk("初始金 = START_MONEY 1000", money() == 1000)

	# 找一个买价 > 1000 的金贵物品（初始 1000 金应买不起）
	var hi_id: int = -1
	var hi_price: int = 0
	for id in gd.get_item_ids():
		var it: Dictionary = gd.get_item(int(id))
		var p: int = EconomyRef.item_buy_price(it)
		if p > hi_price:
			hi_price = p
			hi_id = int(id)
	chk("存在买价 > 1000 的物品", hi_price > 1000, "hi_price=%d" % hi_price)

	print("=== 买不起（初始 1000 金）===")
	var r: Dictionary = gs.shop_buy(hi_id)
	chk("金不足 → 失败 no_money", (not r["ok"]) and str(r["reason"]) == "no_money")
	chk("金不变", money() == 1000)
	chk("背包为空", gs.count_item(hi_id) == 0)

	print("=== 买得起（注入资金）===")
	gs.gain_money(200000)
	var before: int = money()
	r = gs.shop_buy(hi_id)
	chk("购买成功", r["ok"], str(r))
	chk("扣钱正确", money() == before - hi_price, "%d vs %d" % [money(), before - hi_price])
	chk("入库 1 件", gs.count_item(hi_id) == 1)

	print("=== 卖出回笼 ===")
	var before2: int = money()
	r = gs.shop_sell(hi_id, 1)
	chk("卖出成功", r["ok"], str(r))
	chk("加钱 = 卖价", money() == before2 + int(r["gain"]))
	chk("背包清空", gs.count_item(hi_id) == 0)

	print("=== 买薬 ===")
	gs.gain_money(100000)
	var mq: int = ShopRef.medicine_doses(money())
	chk("medicine_doses = gold//50", mq == money() / 50)
	var m: Dictionary = gs.buy_medicine(mq)
	chk("买薬成功", m["ok"], str(m))
	chk("薬数 = 服数", gs.get_medicines() == mq)

	print("=== 休養 / 修行 ===")
	gs.rest()
	var st: Dictionary = gs.get_status()
	chk("休養后体力=max", int(st["stamina"]) == int(st["stamina_max"]))
	var lvl_before: int = int(gs.get_status()["skill_levels"][0])
	var tr: Dictionary = gs.train_skill(0)
	chk("修行成功", tr["ok"], str(tr))
	chk("技能 +1", int(gs.get_status()["skill_levels"][0]) == lvl_before + 1)

	print("\n%d PASS / %d FAIL" % [_pass, _fail])
	quit(0 if _fail == 0 else 1)

func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)
