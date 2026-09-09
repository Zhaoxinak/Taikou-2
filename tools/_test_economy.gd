# _test_economy.gd — economy.gd 单元测试
# 触发：Godot --headless --script res://tools/_test_economy.gd
# 本机 --script 主循环已知失效，逻辑验证走 scripts/_test_economy_mirror.py（49/49 PASS）；
# 此文件用于环境恢复后实跑，以及 --check-only 编译校验（零 Parse Error 即视为通过）。
extends SceneTree

const EconomyRef = preload("res://src/core/economy.gd")

var _pass := 0
var _fail := 0

func chk(name: String, cond: bool, detail: String = "") -> void:
	if cond:
		_pass += 1
	else:
		_fail += 1
		print("  FAIL  %s%s" % [name, ("  (%s)" % detail) if detail != "" else ""])

func _run() -> void:
	print("=== helpers ===")
	chk("div10(123)=12", EconomyRef.div10(123) == 12)
	chk("div20(400)=20", EconomyRef.div20(400) == 20)
	chk("muldiv 3*5/2=7", EconomyRef.muldiv(3, 5, 2) == 7)
	chk("sub_sat", EconomyRef.sub_sat(100, 30) == 70 and EconomyRef.sub_sat(10, 30) == 0)
	chk("add_cap", EconomyRef.add_cap(29900, 200, 0x7530) == 0x7530)

	print("=== 0x4a5c80 生产/消费 (gold 充足) ===")
	var r: Dictionary = EconomyRef.month_produce_full(10, 8, 200, 100, 50, 80)
	chk("prod=40", r["prod"] == 40, str(r["prod"]))
	chk("rice=110", r["rice"] == 110, str(r["rice"]))
	chk("gold 扣 need=10", r["gold"] == 80, str(r["gold"]))
	chk("no famine", not r["famine"])

	print("=== 0x4a5c80 饥荒 ===")
	r = EconomyRef.month_produce_full(4, 2, 400, 0, 0, 50, 1)
	chk("famine flag", r["famine"])
	chk("gold wiped", r["gold"] == 0)
	chk("need=20", r["need"] == 20)
	chk("order drop=10", r["order"] == 10, str(r["order"]))
	chk("food tax=60", r["food"] == 340, str(r))

	print("=== 0x4a5d80 米→军粮 ===")
	var rt: Array = EconomyRef.rice_to_food(10, 1000, 500, 80, 40, 3)
	var rice2: int = rt[0]; var food2: int = rt[1]; var order2: int = rt[2]; var t1a: int = rt[3]; var add: int = rt[4]
	chk("add=200", add == 200, str(add))
	chk("rice left=480", rice2 == 480, str(rice2))
	chk("food=1200", food2 == 1200, str(food2))
	chk("order blend=71", order2 == 71, str(order2))
	chk("trait blend=41", t1a == 41, str(t1a))

	print("=== 0x4a5b50 生产率 ===")
	chk("type_base(2)=2", EconomyRef.town_type_base(2) == 2 and EconomyRef.town_type_base(6) == 3)
	chk("lord=100,tile=0 → Δ=15", EconomyRef.productivity_delta(100, 0, false) == 15)
	chk("lord=20,tile=3 → Δ=1", EconomyRef.productivity_delta(20, 3, false) == 1)
	chk("vassal ×4/5=11", EconomyRef.productivity_delta(100, 0, true) == 11)
	chk("非领有非本藩 -15", EconomyRef.productivity_month(50, 100, 0, false, false, false) == 50)
	chk("本藩不加罚", EconomyRef.productivity_month(50, 100, 0, false, true, false) == 65)

	print("=== 0x49f9b0 + 0x4aa290 农商软顶/开发 ===")
	chk("type0×99 → 1", EconomyRef.commerce_rating(0, 99) == 1)
	chk("type2×10=26", EconomyRef.commerce_rating(2, 10) == maxi(1, 2 * 10 * 4 / 3))
	chk("dev gain=3", EconomyRef.develop_commerce_gain(50, 30, 40) == 3)
	chk("dev capped by gap=2", EconomyRef.develop_commerce_gain(100, 38, 40) == 2)

	print("=== 0x4593e0 调度筑城 ===")
	chk("普通城 day0=14", EconomyRef.castle_materials_days(0, 0) == 14)
	chk("城种 2 day0=12", EconomyRef.castle_materials_days(0, 2) == 12)
	chk("城种 3 day0=12", EconomyRef.castle_materials_days(0, 3) == 12)
	chk("城种 6 day0=12", EconomyRef.castle_materials_days(0, 6) == 12)
	chk("已过 5 天", EconomyRef.castle_materials_days(5, 0) == 9)

	print("=== 0x445ff0 商店买价 ===")
	chk("base=10 →15", EconomyRef.shop_buy_price(10) == 15)
	chk("base=100 →150", EconomyRef.shop_buy_price(100) == 150)
	chk("base=999 →1498", EconomyRef.shop_buy_price(999) == 1498)

	print("=== 0x442270 茶具 ===")
	chk("offer=val=1000,prog=0 →1000", EconomyRef.tea_offer(1000, 0) == 1000)
	chk("offer prog=50 →750", EconomyRef.tea_offer(1000, 50) == 750)
	chk("sell coef=0.9", EconomyRef.tea_sell_price(1000, 50) == 675)

	print("=== 0x458000 / 0x44f4e0 宝物 ===")
	var v: int = 2000
	var bq: int = EconomyRef.treasure_buy_quote(v, 0)
	chk("buy base=200, prog=0 →400", bq == 400, str(bq))
	var sq: int = EconomyRef.treasure_sell_quote(v, 50, 0)
	chk("sell 普通", 300 <= sq and sq <= 320, str(sq))
	var sq5: int = EconomyRef.treasure_sell_quote(v, 100, 5)
	chk("sell 南蛮 cat=5 prog=100 →300", sq5 == 300, str(sq5))

	print("=== 0x4e2d80/0x4e2f20 米市 ===")
	chk("buy qty price=5,gold=0 → min(10,30000*10)", EconomyRef.rice_buy_qty(5, 0) == 10)
	chk("sell qty price<500 →0", EconomyRef.rice_sell_qty(100, 1000) == 0)
	chk("sell qty price=600,gold=0 → 1000", EconomyRef.rice_sell_qty(600, 0) == 1000)
	chk("tier<5 便宜", EconomyRef.rice_tier(3) == "便宜")
	chk("tier 6 普通", EconomyRef.rice_tier(6) == "普通")
	chk("tier 12 昂贵", EconomyRef.rice_tier(12) == "昂贵")

	print("\n%d PASS / %d FAIL" % [_pass, _fail])
	quit(0 if _fail == 0 else 1)

func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)
