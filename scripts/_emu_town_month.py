#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
续33/续34 — 月度城产公式（0x4a5aa0 族）叶函数验证。

字段（0x51eb88 town，证据见 economy_spec.town_domestic_tick）:
  +0x9  byte  农商乘数（低/高 4bit 各 0..15；整字节参与 49f9b0）
  +0xc  byte  农商等级（cap 100；容量×300；可经 4a32a0 加算）
  +0xd  byte  次级等级（cap 250；4a32c0）
  +0xe  byte  民心/治安类（cap 200；缺金时下降）
  +0xf  byte  生产率（与 +0xc 一起决定月产；月增 4a5b50）
  +0x10 word  军粮（cap 50000=0xc350）
  +0x12 word  米持有（cap 30000；米市买卖写入）
  +0x14 word  资金（cap 30000）
  +0x1a byte  次级民情（cap 200）
  +0x1b&7    城种 → 49f960 基档 0..3

0x4a5b50 生产率；0x4a5c80 生产/消费；0x4a5d80 米→军粮；农商软顶 49f9b0。
"""
from __future__ import annotations
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PASS = FAIL = 0


def check(name, cond, detail=''):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f'  PASS  {name}' + (f'  ({detail})' if detail else ''))
    else:
        FAIL += 1
        print(f'  FAIL  {name}' + (f'  ({detail})' if detail else ''))


def _imul_sar(x: int, magic: int, sar: int) -> int:
    prod = (x * magic) & ((1 << 64) - 1)
    if prod >= (1 << 63):
        prod -= 1 << 64
    edx = prod >> 32
    edx >>= sar
    return edx + (1 if edx < 0 else 0)


def div10(x: int) -> int:
    return _imul_sar(x & 0xFFFF, 0x66666667, 2)


def div20(x: int) -> int:
    return _imul_sar(x & 0xFFFF, 0x66666667, 3)


def muldiv(a: int, b: int, c: int) -> int:
    """0x4ebc50(a,b,c) = a*b/c；c==0 → 0xFFFF."""
    if (c & 0xFFFF) == 0:
        return 0xFFFF
    return ((a & 0xFFFF) * (b & 0xFFFF)) // (c & 0xFFFF)


def sub_sat(cur: int, delta: int) -> int:
    """0x4ebcd0(cur, delta) via push order in setters: max(0, cur-delta)."""
    cur &= 0xFFFF
    delta &= 0xFFFF
    return cur - delta if cur > delta else 0


def add_cap(cur: int, delta: int, cap: int) -> int:
    """0x4ebca0(cur, delta, cap)."""
    s = (cur & 0xFFFF) + (delta & 0xFFFF)
    return min(s, cap & 0xFFFF)


def rice_capacity(level_c: int) -> int:
    """0x49fa40 简化：无国主匹配时 esi = +0xc * 300，cap 50000。"""
    return min((level_c & 0xFF) * 300, 0xC350)


def month_produce_full(c, f, food, rice, gold, order, rand6=0):
    """完整 0x4a5c80（含缺金后的军粮税与资金置 0）。"""
    prod = muldiv(c, f, 2)
    rice2 = add_cap(rice, prod // 4, 0x7530)
    gold2 = add_cap(gold, prod, 0x7530)
    need = max(1, div20(food))
    if gold2 >= need:
        gold2 = sub_sat(gold2, need)
        return {
            'prod': prod, 'rice': rice2, 'gold': gold2, 'food': food,
            'order': order, 'need': need, 'famine': False,
        }
    shortfall = need - (gold2 & 0xFFFF)
    pen = muldiv(shortfall, 0x32, need)
    order2 = sub_sat(order, pen)
    if order2 < 1:
        order2 = 1
    denom = (rand6 & 0xFFFF) + 5
    q = (food & 0xFFFF) // denom
    tax = (div10(q) * 10) & 0xFFFF
    food2 = sub_sat(food, tax)
    gold2 = 0
    return {
        'prod': prod, 'rice': rice2, 'gold': gold2, 'food': food2,
        'order': order2, 'need': need, 'famine': True, 'tax': tax, 'pen': pen,
    }


def town_type_base(type_1b: int) -> int:
    """0x49f960: (byte[+0x1b]&7) → {0:0, 1:1, 2..4:2, 5..6:3}."""
    t = type_1b & 7
    if t == 0:
        return 0
    if t == 1:
        return 1
    if t <= 4:
        return 2
    return 3


def commerce_rating(type_1b: int, mult9: int) -> int:
    """0x49f9b0 = max(1, type_base * +9 * 4 / 3)."""
    return max(1, muldiv(town_type_base(type_1b) * (mult9 & 0xFF), 4, 3))


def productivity_delta(lord_stat: int, tile_hi2: int, vassal: bool) -> int:
    """
    0x4a5b50 核心增量（写入前）:
      stat = lord_stat；若 49ac90 真则 ×4/5
      factor = 2*tile_tier + 5（tile = map>>4 & 3）
      delta = max(1, max(0, stat/5 - factor))
    """
    stat = lord_stat & 0xFFFF
    if vassal:
        stat = muldiv(stat, 4, 5)
    factor = 2 * (tile_hi2 & 3) + 5
    d = sub_sat(_imul_sar(stat, 0x66666667, 1), factor)
    return max(1, d)


def productivity_month(cur_f: int, lord_stat: int, tile_hi2: int,
                       vassal: bool, owned: bool, player_home: bool) -> int:
    """满月 0x4a5b50：先 +delta（cap100），若未领有且非本藩再 −15。"""
    d = productivity_delta(lord_stat, tile_hi2, vassal)
    f = add_cap(cur_f, d, 0x64)
    if not owned and not player_home:
        f = sub_sat(f, 0xF)
    return f


def develop_commerce_gain(officer_naisei: int, town_c: int, rating: int) -> int:
    """
    0x4aa290 开发农商（门控通过后）:
      grow = max(0, officer[+0xc]-30)/10 + 1
      add  = min(max(0, rating - town[+0xc]), grow)
      → 4a32a0(add)  cap 100
    """
    grow = div10(sub_sat(officer_naisei, 0x1E)) + 1
    gap = sub_sat(rating, town_c)
    return min(gap, grow)


def rice_to_food(c, food, rice, order, trait_1a, tile_lo4):
    """
    0x4a5d80 米→军粮（假设 49ace0 真）:
      cap = rice_capacity(c)
      take = min(cap//10, rice*4//10, max(0, cap-food))
      add = (take//10)*10
      rice -= add//10
      food = min(food+add, cap)
      若 food>0: 混合 +0xe / +0x1a
    """
    cap = rice_capacity(c)
    take = min(div10(cap), muldiv(rice, 4, 10), sub_sat(cap, food))
    add = (div10(take) * 10) & 0xFFFF
    rice2 = sub_sat(rice, div10(add))
    old_food = food
    food2 = add_cap(food, add, cap)
    if food2 == 0:
        return rice2, food2, order, trait_1a, add
    old = food2 - add  # = old_food if no cap clip; use tracked
    old = old_food
    # new_e = ((order*old) + (tile_lo4*add*10)) / food2
    new_e = ((order * old) + (tile_lo4 * add * 10)) // food2
    new_e = min(new_e, 200)
    # new_1a = ((trait_1a*old) + (add*50)) / food2
    new_1a = ((trait_1a * old) + (add * 50)) // food2
    new_1a = min(new_1a, 200)
    return rice2, food2, new_e, new_1a, add


def main():
    print('=== helpers ===')
    check('div20(100)=5', div20(100) == 5)
    check('muldiv 3*5/2=7', muldiv(3, 5, 2) == 7)
    check('capacity c=10 →3000', rice_capacity(10) == 3000)
    check('capacity c=200 →50000', rice_capacity(200) == 0xC350)
    check('sub_sat', sub_sat(100, 30) == 70 and sub_sat(10, 30) == 0)
    check('add_cap', add_cap(29900, 200, 0x7530) == 0x7530)

    print('=== 0x4a5c80 produce (enough gold) ===')
    r = month_produce_full(c=10, f=8, food=200, rice=100, gold=50, order=80)
    # prod=40; rice+=10→110; gold+=40→90; need=max(1,10)=10; gold=80
    check('prod', r['prod'] == 40, str(r['prod']))
    check('rice', r['rice'] == 110, str(r['rice']))
    check('gold after upkeep', r['gold'] == 80, str(r['gold']))
    check('no famine', r['famine'] is False)

    print('=== 0x4a5c80 famine ===')
    r = month_produce_full(c=10, f=8, food=400, rice=0, gold=0, order=50, rand6=1)
    # prod=40; rice=10; gold=40; need=20; shortfall path from gold=40>=20? 
    # gold after prod=40, need=20 → enough. Use lower gold path:
    r = month_produce_full(c=4, f=2, food=400, rice=0, gold=0, order=50, rand6=1)
    # prod=4; rice=1; gold=4; need=20; famine
    check('famine flag', r['famine'] is True)
    check('gold wiped', r['gold'] == 0)
    check('need=20', r['need'] == 20)
    # pen = (20-4)*50/20 = 16*50/20 = 40; order = max(1, 50-40)=10
    check('order drop', r['order'] == 10, str(r['order']))
    # tax: 400/(1+5)=66; div10*10=60; food=340
    check('food tax', r['food'] == 340 and r['tax'] == 60, str(r))

    print('=== 0x4a5d80 rice→food ===')
    rice, food, order, t1a, add = rice_to_food(
        c=10, food=1000, rice=500, order=80, trait_1a=40, tile_lo4=3)
    check('add', add == 200, str(add))
    check('rice left', rice == 480, str(rice))
    check('food', food == 1200, str(food))
    check('order blend', order == 71, str(order))
    check('trait blend', t1a == 41, str(t1a))

    print('=== 0x4a5b50 productivity ===')
    check('type base', town_type_base(0) == 0 and town_type_base(2) == 2 and town_type_base(6) == 3)
    check('rating type2×9=10', commerce_rating(2, 10) == max(1, 2 * 10 * 4 // 3), str(commerce_rating(2, 10)))
    check('rating type0 →1', commerce_rating(0, 99) == 1)
    # lord=100, tile=0 → factor=5; 100/5=20; delta=15
    check('delta strong', productivity_delta(100, 0, False) == 15)
    # lord=20, tile=3 → factor=11; 20/5=4; delta=0→1
    check('delta floor1', productivity_delta(20, 3, False) == 1)
    check('vassal shrink', productivity_delta(100, 0, True) == max(1, sub_sat(muldiv(100, 4, 5) // 5, 5)))
    # simplify: 100*4/5=80; 80/5=16; 16-5=11
    check('vassal delta', productivity_delta(100, 0, True) == 11)
    check('unowned penalty', productivity_month(50, 100, 0, False, False, False) == 50)
    # 50+15=65; -15=50
    check('owned no penalty', productivity_month(50, 100, 0, False, True, False) == 65)

    print('=== develop +0xc ===')
    # officer 内政 50 → grow=(50-30)/10+1=3; rating 40, town 30 → add=3
    check('develop gain', develop_commerce_gain(50, 30, 40) == 3)
    check('develop capped by gap', develop_commerce_gain(100, 38, 40) == 2)
    check('develop at softcap', develop_commerce_gain(100, 40, 40) == 0)
    check('add_cap commerce', add_cap(98, 5, 100) == 100)

    print(f'\n{PASS} PASS / {FAIL} FAIL')
    return 0 if FAIL == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
