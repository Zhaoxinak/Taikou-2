# economy.gd — 经济/物价子系统纯逻辑核心（1:1 复刻 scripts/economy_ref.py）
#
# 来源：脱壳映像逐指令反汇编 + Unicorn 2.1.4 叶函数实跑验证
#       （scripts/_emu_town_month.py 33/33 PASS / _emu_economy.py / economy_ref.py _selftest 49/49）
#
# 覆盖（全部纯函数，随机由调用方注入以保证可测）：
#   1. 算术基元            _imul_sar / div10 / div20 / div200 / div_94_12 / muldiv / sub_sat / add_cap
#   2. 城镇字段语义         town_type_base（0x49f960）
#   3. 月度城产公式         0x4a5aa0（4a5b50 生产率 + 4a5c80 产/消耗 + 4a5d80 米→军粮）
#   4. 农商软顶/开发        0x49f960 / 0x49f9b0 / 0x4aa290
#   5. 调度筑城物资         0x4593e0
#   6. 商店买价            0x445ff0（×1.5）
#   7. 茶具买卖            0x442270
#   8. 宝物买卖            0x44f4e0(buy) / 0x458000(sell)
#   9. 米市投机            0x4e2d80(buy) / 0x4e2f20(sell)
#
# 未闭合（诚实地沿用 ref 标注，非本模块引入）：
#   ① 0x513ea8 店面逐商品月度改价（已证伪 EXE 月结链含此项）
#   ② 0x51e1f0 物品池 category/level 首次种子来源（已证伪 EXE 内空槽工厂）
# 本模块只搬运「可由静态定义数据算出的定价/生产公式」，不碰运行时对象池。
extends RefCounted

# ============================================================ 算术基元
# _imul_sar：原版 imul reg32, imm32; sar reg, imm
#   prod = (x * magic) 取 64 位；若 ≥ 2^63 表示有符号溢出则回落；edx = prod>>32（高 32 位）；再算术右移 sar
static func _imul_sar(x: int, magic: int, sar: int) -> int:
	# ⚠️ GDScript int 已是 64 位有符号且乘法天然回绕，不可再手动掩码：
	#    `1 << 64` 的移位量会按 6 位取模变成 `1 << 0`，掩码退化为 0，结果恒 0。
	#    故直接取乘积（等价于 Python 侧 &0xFFFF..FFFF 后再转有符号）。
	var prod: int = x * magic
	var edx: int = prod >> 32
	edx >>= sar
	return edx + (1 if edx < 0 else 0)

static func div10(x: int) -> int:  return _imul_sar(x & 0xFFFF, 0x66666667, 2)
static func div20(x: int) -> int:  return _imul_sar(x & 0xFFFF, 0x66666667, 3)
static func div200(x: int) -> int: return _imul_sar(x & 0xFFFF, 0x51eb851f, 4)   # sar 4 = 1/200
static func div_94_12(x: int) -> int: return _imul_sar(x & 0xFFFFFFFF, 0xae147ae1, 6)

# 0x4ebc50(a,b,c) = a*b/c；c==0 → 0xFFFF（战斗同款哨兵）
static func muldiv(a: int, b: int, c: int) -> int:
	if (c & 0xFFFF) == 0:
		return 0xFFFF
	return ((a & 0xFFFF) * (b & 0xFFFF)) / (c & 0xFFFF)

# max(0, cur - delta)；0x4ebcd0
static func sub_sat(cur: int, delta: int) -> int:
	cur &= 0xFFFF
	delta &= 0xFFFF
	return cur - delta if cur > delta else 0

# min(cur+delta, cap)；0x4ebca0
static func add_cap(cur: int, delta: int, cap: int) -> int:
	return mini((cur & 0xFFFF) + (delta & 0xFFFF), cap & 0xFFFF)

# ============================================================ 城镇字段标签
# 城镇对象池 0x51eb88，stride 0x1f = 31B。下列为已确认语义（文档化/查询用）。
const TOWN_FIELDS := {
	"+0x9":   "农商乘数(高低 4bit 各 0..15；整字节×城种基档→49f9b0)",
	"+0xc":   "农商等级(cap 100；容量=+0xc×300；可经 4a32a0 加算)",
	"+0xd":   "次级等级(cap 250)",
	"+0xe":   "民心/治安(cap 200)",
	"+0xf":   "生产率(cap 100；prod=(+0xc*+0xf)/2)",
	"+0x10":  "军粮 word(cap 50000)",
	"+0x12":  "米持有 word(cap 30000)",
	"+0x14":  "资金 word(cap 30000)",
	"+0x1a":  "次级民情(cap 200)",
	"+0x1b&7": "城种(→49f960 基档 0..3)",
}

# 0x49f960: (byte[+0x1b]&7) → {0:0, 1:1, 2..4:2, 5..6:3}
static func town_type_base(t: int) -> int:
	t &= 7
	if t == 0: return 0
	if t == 1: return 1
	if t <= 4: return 2
	return 3

# ============================================================ 0x4a5aa0 月度城产
# 0x49fa40 简化（无国主匹配时）: cap = min(+0xc × 300, 50000)
static func rice_capacity(level_c: int) -> int:
	return mini((level_c & 0xFF) * 300, 0xC350)

# 0x4a5b50 增量(写入前): max(1, max(0, lord_stat/5 − (2×tile + 5)))
static func productivity_delta(lord_stat: int, tile_hi2: int, vassal: bool) -> int:
	var stat: int = lord_stat & 0xFFFF
	if vassal:
		stat = muldiv(stat, 4, 5)
	var factor: int = 2 * (tile_hi2 & 3) + 5
	var d: int = sub_sat(_imul_sar(stat, 0x66666667, 1), factor)
	return maxi(1, d)

# 满月 0x4a5b50: 先 +delta(cap 100)；若未领有且非本藩再 −15
static func productivity_month(cur_f: int, lord_stat: int, tile_hi2: int,
		vassal: bool, owned: bool, player_home: bool) -> int:
	var f: int = add_cap(cur_f, productivity_delta(lord_stat, tile_hi2, vassal), 0x64)
	if not owned and not player_home:
		f = sub_sat(f, 0xF)
	return f

# 完整 0x4a5c80(含缺金军粮税与资金置 0)。return dict
static func month_produce_full(c: int, f: int, food: int, rice: int, gold: int, order: int, rand6: int = 0) -> Dictionary:
	var prod: int = muldiv(c, f, 2)
	var rice2: int = add_cap(rice, prod / 4, 0x7530)
	var gold2: int = add_cap(gold, prod, 0x7530)
	var need: int = maxi(1, div20(food))
	if gold2 >= need:
		return {"prod": prod, "rice": rice2, "gold": sub_sat(gold2, need),
				"food": food, "order": order, "need": need, "famine": false}
	var shortfall: int = need - (gold2 & 0xFFFF)
	var pen: int = muldiv(shortfall, 0x32, need)
	var order2: int = maxi(1, sub_sat(order, pen))
	var tax: int = (div10((food & 0xFFFF) / ((rand6 & 0xFFFF) + 5)) * 10) & 0xFFFF
	return {"prod": prod, "rice": rice2, "gold": 0, "food": sub_sat(food, tax),
			"order": order2, "need": need, "famine": true, "tax": tax, "pen": pen}

# 0x4a5d80 米→军粮(49ace0 真时); 1 米 ≈ 10 军粮。return Array[rice2, food2, e/a, e/a, add]
static func rice_to_food(c: int, food: int, rice: int, order: int, trait_1a: int, tile_lo4: int) -> Array:
	var cap: int = rice_capacity(c)
	var take: int = mini(mini(div10(cap), muldiv(rice, 4, 10)), sub_sat(cap, food))
	var add: int = (div10(take) * 10) & 0xFFFF
	var rice2: int = sub_sat(rice, div10(add))
	var old_food: int = food
	var food2: int = add_cap(food, add, cap)
	if food2 == 0:
		return [rice2, food2, order, trait_1a, add]
	var new_e: int = mini(((order * old_food) + (tile_lo4 * add * 10)) / food2, 200)
	var new_1a: int = mini(((trait_1a * old_food) + (add * 50)) / food2, 200)
	return [rice2, food2, new_e, new_1a, add]

# 0x49f9b0 = max(1, type_base × +9 × 4/3)
static func commerce_rating(type_1b: int, mult9: int) -> int:
	return maxi(1, muldiv(town_type_base(type_1b) * (mult9 & 0xFF), 4, 3))

# 0x4aa290 开发农商(门控通过后): grow = (内政-30)/10 + 1; add = min(rating - town[+0xc], grow)
static func develop_commerce_gain(officer_naisei: int, town_c: int, rating: int) -> int:
	var grow: int = div10(sub_sat(officer_naisei, 0x1E)) + 1
	return mini(sub_sat(rating, town_c), grow)

# ============================================================ 0x4593e0 调度筑城
# days = (special?12:14) − player[+6](本月已过日)。special = (town[+0x1b]&7) ∈ {2,3,6}
static func castle_materials_days(player_day_count: int, town_type_1b: int) -> int:
	var base: int = 12 if (town_type_1b & 7) in [2, 3, 6] else 14
	return base - (player_day_count & 0xFF)

# ============================================================ 0x445ff0 商店买价
# ×1.5 (lea [eax+eax*2]×3 + sar eax,1 = ×3/2)。纯净调用下 0x4ebc80 为恒等(不传 cap)
static func shop_buy_price(base: int) -> int:
	if base < 0:
		return 0
	return (base * 3) / 2

# ============================================================ 物品真实价值（item_pricing_ref 的 getValue 模型）
# 物品数据无 grp 字段 → CAT 由 cat_name 映射 8 类；SUB 用 tier 近似（诚实未接：grp 未导出，SUB 为近似）。
const ITEM_CAT8 : Dictionary = {
	"茶具": 7, "美术品": 6, "南蛮物": 5, "书籍": 1, "道具": 2, "武器": 4, "财宝": 3,
}
static func item_value(item: Dictionary) -> int:
	var cat_name: String = str(item.get("cat_name", ""))
	var cat8: int = int(ITEM_CAT8.get(cat_name, 0))
	var level: int = int(item.get("val", 1))      # 旧称 val，实为 LEVEL（1..200）
	var sub: int = int(item.get("tier", 0))       # grp 未导出 → tier 近似 SUB
	return treasure_value(level, sub, cat8)

static func item_buy_price(item: Dictionary) -> int:
	return shop_buy_price(item_value(item))

# 玩家卖回：真实价值半价（简化；原版 treasure_sell_quote 含 progress，本期未接）
static func item_sell_value(item: Dictionary) -> int:
	return item_value(item) / 2

# ============================================================ 0x442270 茶具买卖
# offer = value × (100 − (progress >> 1)) / 100
static func tea_offer(value: int, progress: int) -> int:
	return (value * (100 - ((progress >> 1) & 0xFF))) / 100

static func tea_buy_price(value: int, progress: int) -> int:
	return tea_offer(value, progress)

# 卖价 = offer × 0.9
static func tea_sell_price(value: int, progress: int) -> int:
	return (tea_offer(value, progress) * 9) / 10

# ============================================================ 0x458000 / 0x44f4e0 宝物买卖
# 物品池 vtable[0] = 0x49c070; 按 category 分段 clamp(level, …)。单位: 文(mon)
static func treasure_value(level: int, sub: int, category: int) -> int:
	var lvl: int = level & 0xFF
	var s: int = sub & 0xFF
	var cat: int = category & 7
	if cat == 0: return maxi(1, mini(lvl, 250))
	if cat == 1: return maxi(10, mini((lvl + s * 10) * 10, 6500))
	if cat == 2: return maxi(20, mini(lvl * 20, 5000))
	if cat == 3: return maxi(100, mini((lvl + s * 50) * 10, 32496))
	if cat == 4: return maxi(200, mini((lvl + maxi(s - 5, 0) * 5) * 200, 60000))
	return maxi(200, mini((lvl * (s + 5)) << 2, 50000))

# 0x44f4e0: base + base*(100 − (prog>>1))/100, base = getValue/10
static func treasure_buy_quote(item_value: int, progress: int) -> int:
	var base: int = div10(item_value)
	var delta: int = muldiv(base, 100 - ((progress >> 1) & 0xFF), 100)
	return base + delta

# 0x458000: 普通类 quote = base + (100−prog)×base/94.12; 南蛮(cat=5) quote = base + base×prog/200。成交金 = quote×10
static func treasure_sell_quote(item_value: int, progress: int, category: int) -> int:
	var base: int = div10(item_value)
	var delta: int
	if (category & 7) == 5:
		delta = muldiv(base, progress & 0xFF, 200)
	else:
		delta = div_94_12(((100 - (progress & 0xFF)) & 0xFF) * (base & 0xFFFFFFFF))
	return base + delta

# 成交金 = quote × 10（上限钳制在 0x46f940）
static func treasure_sell_gold(quote: int) -> int:
	return (quote & 0xFFFF) * 10

# ============================================================ 0x4e2ce0 米市
# 0x4e2d80: 上限 min(price×2, (30000 − gold/10)×10); 成交扣金 qty×10
static func rice_buy_qty(price: int, gold: int) -> int:
	var cap_a: int = (price & 0xFFFF) * 2
	var cap_b: int = (30000 - div10(gold & 0xFFFF)) * 10
	return mini(cap_a, cap_b)

# 0x4e2f20: price>500 且 gold/10≤5990 时 min((price−500)×10, (6000−gold/10)×2); 成交加金 qty×10
static func rice_sell_qty(price: int, gold: int) -> int:
	if price <= 500 or div10(gold) > 5990:
		return 0
	return mini((price - 500) * 10, (6000 - div10(gold)) * 2)

# 0x462280: <5 便宜 / 5..11 普通 / ≥12 昂贵
static func rice_tier(price: int) -> String:
	if price < 5: return "便宜"
	if price < 12: return "普通"
	return "昂贵"
