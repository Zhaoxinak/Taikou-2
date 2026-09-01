#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
太阁立志传2 · 经济/物价子系统 参考实现（1:1 复刻 TAIK2W95.exe 逻辑）

来源：脱壳映像 scripts/_unpacked_mem.bin（基址 0x400000）逐指令反汇编 + Unicorn 2.1.4
       叶函数实跑验证（脚本 scripts/_emu_town_month.py 33/33 PASS / _emu_economy.py）。

本文件是「单一入口」复刻模块，覆盖：
  1. 货币格式化（仅文档化,公式无)
  2. 城镇字段语义（0x51eb88 town stride 0x1f = 31B；+0xc/+0xd/+0xe/+0xf/+0x10/+0x12/+0x14/+0x1a/+0x1b&7）
  3. 月度城产公式  0x4a5aa0 (4a5b50 生产率 + 4a5c80 产/消耗 + 4a5d80 米→军粮)
  4. 农商软顶/开发 0x49f960/0x49f9b0/0x4a32a0/0x4aa290
  5. 调度筑城物资 0x459280/0x4593e0/0x4592e0
  6. 商店买价      0x445ff0（×1.5）
  7. 茶具买卖      0x442270 (offer = val×(100-(prog>>1))/100, 卖×0.9)
  8. 宝物买卖      0x44f4e0 (buy) / 0x458000 (sell)
  9. 米市投机      0x4e2d80 (buy) / 0x4e2f20 (sell)

未闭合：① 0x513ea8 店面逐商品月度改价（已证伪 EXE 月结链含此项）;② 0x51e1f0 物品池
       category/level 首次种子来源（已证伪 EXE 内空槽工厂）。

对象 VA 速查
------------
  word[0x51662e]           玩家金钱（结构 0x516610+0x1e）
  byte[0x5205f1]           当前月
  byte[0x5205f2]           当月已过天数
  byte[0x513e0e]           当前所在国(province)
  byte[0x513e10]           当前所在町(town index)
  dword[0x516610]          玩家结构基址
  dword[0x516624]          玩家 id（owner_key for 物品）
  0x51eb88                 城镇对象池（200×31B）
  0x51e1f0                 物品对象池（200×10B，vtable 0x4fc0e0）
  0x517728                 辅物品池（20×12B）
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


import os, random

BASE = 0x400000
_HERE = os.path.dirname(os.path.abspath(__file__))
_IMG = os.path.join(_HERE, _ROOT + '/scripts/_unpacked_mem.bin')


# ============================================================ 算术基元
def _imul_sar(x: int, magic: int, sar: int) -> int:
    """原版 imul reg32, imm32; sar reg, imm（0xcccccccd / 0x66666667 / 0xae147ae1 等）。"""
    prod = (x * magic) & ((1 << 64) - 1)
    if prod >= (1 << 63):
        prod -= 1 << 64
    edx = (prod >> 32)
    edx >>= sar
    return edx + (1 if edx < 0 else 0)


def div10(x: int) -> int:        return _imul_sar(x & 0xFFFF, 0x66666667, 2)
def div20(x: int) -> int:        return _imul_sar(x & 0xFFFF, 0x66666667, 3)
def div200(x: int) -> int:       return _imul_sar(x & 0xFFFF, 0x51eb851f, 4)  # sar 4 = 1/200
def div_94_12(x: int) -> int:    return _imul_sar(x & 0xFFFFFFFF, 0xae147ae1, 6)


def muldiv(a: int, b: int, c: int) -> int:
    """0x4ebc50(a,b,c) = a*b/c；c==0 → 0xFFFF（战斗同款）。"""
    if (c & 0xFFFF) == 0:
        return 0xFFFF
    return ((a & 0xFFFF) * (b & 0xFFFF)) // (c & 0xFFFF)


def sub_sat(cur: int, delta: int) -> int:
    """max(0, cur - delta)；0x4ebcd0 push 顺序视调用方而定,本处只用 max 版。"""
    cur &= 0xFFFF; delta &= 0xFFFF
    return cur - delta if cur > delta else 0


def add_cap(cur: int, delta: int, cap: int) -> int:
    """min(cur+delta, cap)；0x4ebca0。"""
    return min((cur & 0xFFFF) + (delta & 0xFFFF), cap & 0xFFFF)


# ============================================================ 城镇字段标签
TOWN_FIELDS = {
    "+0x9":  "农商乘数(高低 4bit 各 0..15；整字节×城种基档→49f9b0)",
    "+0xc":  "农商等级(cap 100；容量=+0xc×300；可经 4a32a0 加算)",
    "+0xd":  "次级等级(cap 250)",
    "+0xe":  "民心/治安(cap 200)",
    "+0xf":  "生产率(cap 100；prod=(+0xc*+0xf)/2)",
    "+0x10": "军粮 word(cap 50000)",
    "+0x12": "米持有 word(cap 30000)",
    "+0x14": "资金 word(cap 30000)",
    "+0x1a": "次级民情(cap 200)",
    "+0x1b&7": "城种(→49f960 基档 0..3)",
}


def town_type_base(t: int) -> int:
    """0x49f960: (byte[+0x1b]&7) → {0:0, 1:1, 2..4:2, 5..6:3}。"""
    t &= 7
    if t == 0: return 0
    if t == 1: return 1
    if t <= 4: return 2
    return 3


# ============================================================ 0x4a5aa0 月度城产
def rice_capacity(level_c: int) -> int:
    """0x49fa40 简化（无国主匹配时）: cap = min(+0xc × 300, 50000)。"""
    return min((level_c & 0xFF) * 300, 0xC350)


def productivity_delta(lord_stat: int, tile_hi2: int, vassal: bool) -> int:
    """0x4a5b50 增量(写入前): max(1, max(0, lord_stat/5 − (2×tile + 5)))。"""
    stat = lord_stat & 0xFFFF
    if vassal:
        stat = muldiv(stat, 4, 5)
    factor = 2 * (tile_hi2 & 3) + 5
    d = sub_sat(_imul_sar(stat, 0x66666667, 1), factor)
    return max(1, d)


def productivity_month(cur_f: int, lord_stat: int, tile_hi2: int,
                       vassal: bool, owned: bool, player_home: bool) -> int:
    """满月 0x4a5b50: 先 +delta(cap 100)；若未领有且非本藩再 −15。"""
    f = add_cap(cur_f, productivity_delta(lord_stat, tile_hi2, vassal), 0x64)
    if not owned and not player_home:
        f = sub_sat(f, 0xF)
    return f


def month_produce_full(c, f, food, rice, gold, order, rand6=0):
    """完整 0x4a5c80(含缺金军粮税与资金置 0)。return dict. """
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
    """0x4a5d80 米→军粮(49ace0 真时); 1 米 ≈ 10 军粮。"""
    cap = rice_capacity(c)
    take = min(div10(cap), muldiv(rice, 4, 10), sub_sat(cap, food))
    add = (div10(take) * 10) & 0xFFFF
    rice2 = sub_sat(rice, div10(add))
    old_food = food
    food2 = add_cap(food, add, cap)
    if food2 == 0:
        return rice2, food2, order, trait_1a, add
    new_e = min(((order * old_food) + (tile_lo4 * add * 10)) // food2, 200)
    new_1a = min(((trait_1a * old_food) + (add * 50)) // food2, 200)
    return rice2, food2, new_e, new_1a, add


def commerce_rating(type_1b: int, mult9: int) -> int:
    """0x49f9b0 = max(1, type_base × +9 × 4/3)。"""
    return max(1, muldiv(town_type_base(type_1b) * (mult9 & 0xFF), 4, 3))


def develop_commerce_gain(officer_naisei: int, town_c: int, rating: int) -> int:
    """0x4aa290 开发农商(门控通过后): grow = (内政-30)/10 + 1; add = min(rating - town[+0xc], grow)。"""
    grow = div10(sub_sat(officer_naisei, 0x1E)) + 1
    return min(sub_sat(rating, town_c), grow)


# ============================================================ 0x459280 调度筑城
def castle_materials_days(player_day_count: int, town_type_1b: int) -> int:
    """0x4593e0 启动: days = (special?12:14) − player[+6](本月已过日)。
    special = (town[+0x1b]&7) ∈ {2, 3, 6}; 0x4b36a0.
    """
    base = 12 if (town_type_1b & 7) in (2, 3, 6) else 14
    return base - (player_day_count & 0xFF)


# ============================================================ 0x445ff0 商店买价
def shop_buy_price(base: int) -> int:
    """0x445ff0: ×1.5 (lea [eax+eax*2]×3 + sar eax,1 = ×3/2); base≥500 时再走 0x4ebc80 钳制。
    纯净调用下 0x4ebc80 为恒等(0x445ff0 不传入 cap); 见 BREAKTHROUGHS §续30 / _emu_economy.py。
    """
    if base < 0:
        return 0
    return (base * 3) // 2


# ============================================================ 0x442270 茶具买卖
def tea_offer(value: int, progress: int) -> int:
    """0x442270: offer = value × (100 − (progress >> 1)) / 100。"""
    return (value * (100 - ((progress >> 1) & 0xFF))) // 100


def tea_buy_price(value: int, progress: int) -> int:
    return tea_offer(value, progress)


def tea_sell_price(value: int, progress: int) -> int:
    """卖价 = offer × 0.9。"""
    return (tea_offer(value, progress) * 9) // 10


# ============================================================ 0x458000 / 0x44f4e0 宝物买卖
def treasure_value(level: int, sub: int, category: int) -> int:
    """物品池 vtable[0] = 0x49c070; 按 category 分段 clamp(level, …)。
       返回单位: 文(mon), 与 0x44f4e0/0x458000 的 quote 共单位。"""
    lvl, s, cat = level & 0xFF, sub & 0xFF, category & 7
    if cat == 0: return max(1, min(lvl, 250))
    if cat == 1: return max(10, min((lvl + s * 10) * 10, 6500))
    if cat == 2: return max(20, min(lvl * 20, 5000))
    if cat == 3: return max(100, min((lvl + s * 50) * 10, 32496))
    if cat == 4: return max(200, min((lvl + max(s - 5, 0) * 5) * 200, 60000))
    return max(200, min((lvl * (s + 5)) << 2, 50000))


def treasure_buy_quote(item_value: int, progress: int) -> int:
    """0x44f4e0: base + base*(100 − (prog>>1))/100, base = getValue/10。"""
    base = div10(item_value)
    delta = muldiv(base, 100 - ((progress >> 1) & 0xFF), 100)
    return base + delta


def treasure_sell_quote(item_value: int, progress: int, category: int) -> int:
    """0x458000: base = getValue/10;
       普通类: quote = base + (100 − prog) × base / 94.12 (sar 6, 0xae147ae1);
       南蛮(cat=5): quote = base + base × prog / 200.
       成交金 = quote × 10。"""
    base = div10(item_value)
    if (category & 7) == 5:
        delta = muldiv(base, progress & 0xFF, 200)
    else:
        delta = div_94_12(((100 - (progress & 0xFF)) & 0xFF) * (base & 0xFFFFFFFF))
    return base + delta


def treasure_sell_gold(quote: int) -> int:
    """成交金 = quote × 10(0x44e2f0 加金; 上限钳制在 0x46f940(quote*10))。"""
    return (quote & 0xFFFF) * 10


# ============================================================ 0x4e2ce0 米市
def rice_buy_qty(price: int, gold: int) -> int:
    """0x4e2d80: 上限 min(price×2, (30000 − gold/10)×10); 成交扣金 qty×10。"""
    cap_a = (price & 0xFFFF) * 2
    cap_b = (30000 - div10(gold & 0xFFFF)) * 10
    return min(cap_a, cap_b)


def rice_sell_qty(price: int, gold: int) -> int:
    """0x4e2f20: price>500 且 gold/10≤5990 时:
       min((price−500)×10, (6000−gold/10)×2); 成交加金 qty×10。"""
    if price <= 500 or div10(gold) > 5990:
        return 0
    return min((price - 500) * 10, (6000 - div10(gold)) * 2)


def rice_tier(price: int) -> str:
    """0x462280: <5 便宜 / 5..11 普通 / ≥12 昂贵。"""
    if price < 5: return "便宜"
    if price < 12: return "普通"
    return "昂贵"


# ============================================================ 演示 / 自检
def _selftest():
    PASS = FAIL = 0
    def chk(name, cond, detail=''):
        nonlocal PASS, FAIL
        if cond: PASS += 1; print(f"  PASS  {name}" + (f"  ({detail})" if detail else ''))
        else:    FAIL += 1; print(f"  FAIL  {name}" + (f"  ({detail})" if detail else ''))

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
    v = 2000  # getValue
    bq = treasure_buy_quote(v, 0)        # base=200, +200 → 400
    chk("buy base=200, prog=0 →400", bq == 400, str(bq))
    sq = treasure_sell_quote(v, 50, 0)   # base=200, +(50*200/94.12)≈106
    chk("sell 普通", 300 <= sq <= 320, str(sq))
    sq5 = treasure_sell_quote(v, 100, 5) # 南蛮: base=200, +200*100/200=100 →300
    chk("sell 南蛮 cat=5 prog=100 →300", sq5 == 300, str(sq5))

    print("=== 0x4e2d80/0x4e2f20 米市 ===")
    chk("buy qty price=5,gold=0 → min(10,30000*10)", rice_buy_qty(5, 0) == 10)
    chk("sell qty price<500 →0", rice_sell_qty(100, 1000) == 0)
    chk("sell qty price=600,gold=0 → 1000", rice_sell_qty(600, 0) == 1000)
    chk("tier<5 便宜", rice_tier(3) == "便宜")
    chk("tier 6 普通", rice_tier(6) == "普通")
    chk("tier 12 昂贵", rice_tier(12) == "昂贵")

    print(f"\n{PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


# ============================================================ 映像自校验
def verify_against_image():
    """对脱壳映像做可选的字符串/常量级自校验(凡能在静态段读到的均核对)。"""
    if not os.path.exists(_IMG):
        print("[skip] 未找到 %s，跳过映像自校验" % _IMG)
        return None
    mem = open(_IMG, "rb").read()

    def rd(va, n): return list(mem[va - BASE: va - BASE + n])
    checks = []

    # 货币格式化串(GBK)
    def gbk(s): return list(s.encode("gbk"))
    fmt_gold = gbk("所持金∶%4u贯 %u00文")
    checks.append(("0x509b88 所持金串", rd(0x509B88, len(fmt_gold)), fmt_gold))

    # 米市 3 档显示名
    cheap = gbk("便宜")
    checks.append(("0x504978 便宜", rd(0x504978, len(cheap)), cheap))
    # 续94 修正: 映像内为简体「昂贵」(GBK B0BA B9F3), 原断言误写繁体「昂貴」
    # (GBK B0BA D946) 致 [NG] 误报。全表其余项均为简体, 此处系笔误。
    expensive = gbk("昂贵")
    checks.append(("0x504988 昂贵", rd(0x504988, len(expensive)), expensive))

    # 城镇菜单(城种索引→设施名)前 3 项
    shangye = gbk("商业")
    chadao = gbk("茶道")
    checks.append(("0x504658 商业", rd(0x504658, len(shangye)), shangye))
    checks.append(("0x50465d 茶道", rd(0x50465D, len(chadao)), chadao))

    # 调度筑城物资菜单串
    diaodu = gbk("调度筑城物资")
    checks.append(("0x504625 调度筑城物资", rd(0x504625, len(diaodu)), diaodu))

    ok = True
    for name, got, want in checks:
        good = got == want
        ok &= good
        print(("  [OK] " if good else "  [NG] ") + name + "  " + str(got))
    return ok


if __name__ == "__main__":
    print("=== 经济参考实现 · 自检 ===")
    rc = _selftest()
    print("\n=== 经济参考实现 · 映像自校验 ===")
    r = verify_against_image()
    print("  => %s" % ("全部一致" if r else ("不一致！" if r is False else "已跳过")))
    raise SystemExit(rc if r is None else rc)
