# -*- coding: utf-8 -*-
"""
_test_economy_mirror.py — economy.gd 的 Python 等价镜像（逻辑验证用）

本机 Godot headless `--script` 主循环失效，按项目约定走 Python 镜像复跑同一套断言来验证
economy.gd 的逻辑与期望值。函数体逐条对齐 src/core/economy.gd（亦即 economy_ref.py 的 1:1 复刻），
断言集合取自 economy_ref.py 的 _selftest（49 项，源端已 49/49 PASS）。

运行：python3 scripts/_test_economy_mirror.py
"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>


# ============================================================ 算术基元
def _imul_sar(x, magic, sar):
    prod = (x * magic) & ((1 << 64) - 1)
    if prod >= (1 << 63):
        prod -= (1 << 64)
    edx = (prod >> 32)
    edx >>= sar
    return edx + (1 if edx < 0 else 0)

def div10(x):  return _imul_sar(x & 0xFFFF, 0x66666667, 2)
def div20(x):  return _imul_sar(x & 0xFFFF, 0x66666667, 3)
def div200(x): return _imul_sar(x & 0xFFFF, 0x51eb851f, 4)
def div_94_12(x): return _imul_sar(x & 0xFFFFFFFF, 0xae147ae1, 6)

def muldiv(a, b, c):
    if (c & 0xFFFF) == 0:
        return 0xFFFF
    return ((a & 0xFFFF) * (b & 0xFFFF)) // (c & 0xFFFF)

def sub_sat(cur, delta):
    cur &= 0xFFFF; delta &= 0xFFFF
    return cur - delta if cur > delta else 0

def add_cap(cur, delta, cap):
    return min((cur & 0xFFFF) + (delta & 0xFFFF), cap & 0xFFFF)

# 城镇字段
def town_type_base(t):
    t &= 7
    if t == 0: return 0
    if t == 1: return 1
    if t <= 4: return 2
    return 3

# 月度城产
def rice_capacity(level_c):
    return min((level_c & 0xFF) * 300, 0xC350)

def productivity_delta(lord_stat, tile_hi2, vassal):
    stat = lord_stat & 0xFFFF
    if vassal:
        stat = muldiv(stat, 4, 5)
    factor = 2 * (tile_hi2 & 3) + 5
    d = sub_sat(_imul_sar(stat, 0x66666667, 1), factor)
    return max(1, d)

def productivity_month(cur_f, lord_stat, tile_hi2, vassal, owned, player_home):
    f = add_cap(cur_f, productivity_delta(lord_stat, tile_hi2, vassal), 0x64)
    if not owned and not player_home:
        f = sub_sat(f, 0xF)
    return f

def month_produce_full(c, f, food, rice, gold, order, rand6=0):
    prod = muldiv(c, f, 2)
    rice2 = add_cap(rice, prod // 4, 0x7530)
    gold2 = add_cap(gold, prod, 0x7530)
    need = max(1, div20(food))
    if gold2 >= need:
        return {"prod": prod, "rice": rice2, "gold": sub_sat(gold2, need),
                "food": food, "order": order, "need": need, "famine": False}
    shortfall = need - (gold2 & 0xFFFF)
    pen = muldiv(shortfall, 0x32, need)
    order2 = max(1, sub_sat(order, pen))
    tax = (div10((food & 0xFFFF) // ((rand6 & 0xFFFF) + 5)) * 10) & 0xFFFF
    return {"prod": prod, "rice": rice2, "gold": 0, "food": sub_sat(food, tax),
            "order": order2, "need": need, "famine": True, "tax": tax, "pen": pen}

def rice_to_food(c, food, rice, order, trait_1a, tile_lo4):
    cap = rice_capacity(c)
    take = min(div10(cap), muldiv(rice, 4, 10), sub_sat(cap, food))
    add = (div10(take) * 10) & 0xFFFF
    rice2 = sub_sat(rice, div10(add))
    old_food = food
    food2 = add_cap(food, add, cap)
    if food2 == 0:
        return [rice2, food2, order, trait_1a, add]
    new_e = min(((order * old_food) + (tile_lo4 * add * 10)) // food2, 200)
    new_1a = min(((trait_1a * old_food) + (add * 50)) // food2, 200)
    return [rice2, food2, new_e, new_1a, add]

def commerce_rating(type_1b, mult9):
    return max(1, muldiv(town_type_base(type_1b) * (mult9 & 0xFF), 4, 3))

def develop_commerce_gain(officer_naisei, town_c, rating):
    grow = div10(sub_sat(officer_naisei, 0x1E)) + 1
    return min(sub_sat(rating, town_c), grow)

# 调度筑城
def castle_materials_days(player_day_count, town_type_1b):
    base = 12 if (town_type_1b & 7) in (2, 3, 6) else 14
    return base - (player_day_count & 0xFF)

# 商店买价
def shop_buy_price(base):
    if base < 0:
        return 0
    return (base * 3) // 2

# 茶具
def tea_offer(value, progress):
    return (value * (100 - ((progress >> 1) & 0xFF))) // 100

def tea_buy_price(value, progress):
    return tea_offer(value, progress)

def tea_sell_price(value, progress):
    return (tea_offer(value, progress) * 9) // 10

# 宝物
def treasure_value(level, sub, category):
    lvl, s, cat = level & 0xFF, sub & 0xFF, category & 7
    if cat == 0: return max(1, min(lvl, 250))
    if cat == 1: return max(10, min((lvl + s * 10) * 10, 6500))
    if cat == 2: return max(20, min(lvl * 20, 5000))
    if cat == 3: return max(100, min((lvl + s * 50) * 10, 32496))
    if cat == 4: return max(200, min((lvl + max(s - 5, 0) * 5) * 200, 60000))
    return max(200, min((lvl * (s + 5)) << 2, 50000))

def treasure_buy_quote(item_value, progress):
    base = div10(item_value)
    delta = muldiv(base, 100 - ((progress >> 1) & 0xFF), 100)
    return base + delta

def treasure_sell_quote(item_value, progress, category):
    base = div10(item_value)
    if (category & 7) == 5:
        delta = muldiv(base, progress & 0xFF, 200)
    else:
        delta = div_94_12(((100 - (progress & 0xFF)) & 0xFF) * (base & 0xFFFFFFFF))
    return base + delta

def treasure_sell_gold(quote):
    return (quote & 0xFFFF) * 10

# 米市
def rice_buy_qty(price, gold):
    cap_a = (price & 0xFFFF) * 2
    cap_b = (30000 - div10(gold & 0xFFFF)) * 10
    return min(cap_a, cap_b)

def rice_sell_qty(price, gold):
    if price <= 500 or div10(gold) > 5990:
        return 0
    return min((price - 500) * 10, (6000 - div10(gold)) * 2)

def rice_tier(price):
    if price < 5: return "便宜"
    if price < 12: return "普通"
    return "昂贵"


# ============================================================ 断言集（取自 economy_ref._selftest）
PASS = FAIL = 0
_failures = []

def chk(name, cond, detail=''):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        _failures.append((name, detail))
        print("  FAIL  %s%s" % (name, ("  (%s)" % detail) if detail else ''))
    return cond

print("=== helpers ===")
chk("div10(123)=12", div10(123) == 12)
chk("div20(400)=20", div20(400) == 20)
chk("muldiv 3*5/2=7", muldiv(3, 5, 2) == 7)
chk("sub_sat", sub_sat(100, 30) == 70 and sub_sat(10, 30) == 0)
chk("add_cap", add_cap(29900, 200, 0x7530) == 0x7530)

print("=== 0x4a5c80 生产/消费 (gold 充足) ===")
r = month_produce_full(c=10, f=8, food=200, rice=100, gold=50, order=80)
chk("prod=40", r["prod"] == 40, str(r["prod"]))
chk("rice=110", r["rice"] == 110, str(r["rice"]))
chk("gold 扣 need=10", r["gold"] == 80, str(r["gold"]))
chk("no famine", not r["famine"])

print("=== 0x4a5c80 饥荒 ===")
r = month_produce_full(c=4, f=2, food=400, rice=0, gold=0, order=50, rand6=1)
chk("famine flag", r["famine"])
chk("gold wiped", r["gold"] == 0)
chk("need=20", r["need"] == 20)
chk("order drop=10", r["order"] == 10, str(r["order"]))
chk("food tax=60", r["food"] == 340, str(r))

print("=== 0x4a5d80 米→军粮 ===")
rice, food, order, t1a, add = rice_to_food(c=10, food=1000, rice=500, order=80, trait_1a=40, tile_lo4=3)
chk("add=200", add == 200, str(add))
chk("rice left=480", rice == 480, str(rice))
chk("food=1200", food == 1200, str(food))
chk("order blend=71", order == 71, str(order))
chk("trait blend=41", t1a == 41, str(t1a))

print("=== 0x4a5b50 生产率 ===")
chk("type_base(2)=2", town_type_base(2) == 2 and town_type_base(6) == 3)
chk("lord=100,tile=0 → Δ=15", productivity_delta(100, 0, False) == 15)
chk("lord=20,tile=3 → Δ=1", productivity_delta(20, 3, False) == 1)
chk("vassal ×4/5=11", productivity_delta(100, 0, True) == 11)
chk("非领有非本藩 -15", productivity_month(50, 100, 0, False, False, False) == 50)
chk("本藩不加罚", productivity_month(50, 100, 0, False, True, False) == 65)

print("=== 0x49f9b0 + 0x4aa290 农商软顶/开发 ===")
chk("type0×99 → 1", commerce_rating(0, 99) == 1)
chk("type2×10=26", commerce_rating(2, 10) == max(1, 2*10*4//3))
chk("dev gain=3", develop_commerce_gain(50, 30, 40) == 3)
chk("dev capped by gap=2", develop_commerce_gain(100, 38, 40) == 2)

print("=== 0x4593e0 调度筑城 ===")
chk("普通城 day0=14", castle_materials_days(0, 0) == 14)
chk("城种 2 day0=12", castle_materials_days(0, 2) == 12)
chk("城种 3 day0=12", castle_materials_days(0, 3) == 12)
chk("城种 6 day0=12", castle_materials_days(0, 6) == 12)
chk("已过 5 天", castle_materials_days(5, 0) == 9)

print("=== 0x445ff0 商店买价 ===")
chk("base=10 →15", shop_buy_price(10) == 15)
chk("base=100 →150", shop_buy_price(100) == 150)
chk("base=999 →1498", shop_buy_price(999) == 1498)

print("=== 0x442270 茶具 ===")
chk("offer=val=1000,prog=0 →1000", tea_offer(1000, 0) == 1000)
chk("offer prog=50 →750", tea_offer(1000, 50) == 750)
chk("sell coef=0.9", tea_sell_price(1000, 50) == 675)

print("=== 0x458000 / 0x44f4e0 宝物 ===")
v = 2000
bq = treasure_buy_quote(v, 0)
chk("buy base=200, prog=0 →400", bq == 400, str(bq))
sq = treasure_sell_quote(v, 50, 0)
chk("sell 普通", 300 <= sq <= 320, str(sq))
sq5 = treasure_sell_quote(v, 100, 5)
chk("sell 南蛮 cat=5 prog=100 →300", sq5 == 300, str(sq5))

print("=== 0x4e2d80/0x4e2f20 米市 ===")
chk("buy qty price=5,gold=0 → min(10,30000*10)", rice_buy_qty(5, 0) == 10)
chk("sell qty price<500 →0", rice_sell_qty(100, 1000) == 0)
chk("sell qty price=600,gold=0 → 1000", rice_sell_qty(600, 0) == 1000)
chk("tier<5 便宜", rice_tier(3) == "便宜")
chk("tier 6 普通", rice_tier(6) == "普通")
chk("tier 12 昂贵", rice_tier(12) == "昂贵")

print("\n%d PASS / %d FAIL" % (PASS, FAIL))
if FAIL:
    print("FAILED:")
    for n, d in _failures:
        print("  -", n, d)
raise SystemExit(1 if FAIL else 0)
