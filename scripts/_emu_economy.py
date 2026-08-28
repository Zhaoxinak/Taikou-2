#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
续30/续31/续32 — 经济公式：茶具 / 宝物买卖 / 米市投机 / 店面×1.5 / 调度筑城天数。

宝物（町菜单 购入/卖出宝物）:
  base = getValue // 10          # 0x66666667 sar2
  buy  0x44f4e0: base + base*(100-(prog>>1))//100
  sell 0x458000:
    cat==5(南蛮): base + base*prog//200
    else:         base + magic_AE147AE1_sar6((100-prog)*base)
  成交金 = sell_quote * 10（0x44e2f0）

调度筑城物资 0x4593e0（非「商业加成」）:
  days = (12 if town[+0x1b]&7 in {2,3,6} else 14) - player[+6]
  写入 player[+0xa]（与统御力槽位复用）

注意：米市路径里同一魔数 sar2 实为 gold/10（续30 误记 /5，续31 纠偏）。
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
    prod = x * magic
    prod &= (1 << 64) - 1
    if prod >= (1 << 63):
        prod -= 1 << 64
    edx = (prod >> 32) >> sar
    return edx + (1 if edx < 0 else 0)


def div100(x: int) -> int:
    return _imul_sar(x, 0x51EB851F, 5)


def div10(x: int) -> int:
    return _imul_sar(x, 0x66666667, 2)


def div200(x: int) -> int:
    return _imul_sar(x, 0x51EB851F, 6)


def sell_extra_normal(x: int) -> int:
    return _imul_sar(x, 0xAE147AE1, 6)


def tea_offer(value: int, progress: int) -> int:
    return div100(value * (100 - ((progress & 0xFFFF) >> 1)))


def tea_buy_price(value: int, progress: int) -> int:
    return tea_offer(value, progress)


def tea_sell_price(value: int, progress: int) -> int:
    return div100(tea_offer(value, progress) * 90)


def treasure_buy_quote(value: int, progress: int) -> int:
    base = div10(value)
    return base + div100(base * (100 - (progress >> 1)))


def treasure_sell_quote(value: int, progress: int, cat: int) -> int:
    base = div10(value)
    if cat == 5:
        return base + div200(base * progress)
    return base + sell_extra_normal(base * (100 - progress))


def treasure_sell_gold(quote: int) -> int:
    return quote * 10


def shop_buy_price(base: int) -> int:
    return (base * 3) // 2


def rice_buy_cap(price: int, gold: int) -> int:
    return min(price * 2, (30000 - div10(gold)) * 10)


def rice_sell_cap(price: int, gold: int) -> int | None:
    if price <= 500:
        return None
    if div10(gold) > 0x1766:
        return None
    return min((price - 500) * 10, (6000 - div10(gold)) * 2)


def rice_tier_label(level: int) -> str:
    if level < 5:
        return '便宜'
    if level < 12:
        return '普通'
    return '昂贵'


def town_special_for_castle(town_1b: int) -> bool:
    """0x4b36a0: (byte[+0x1b] & 7) in {2,3,6}."""
    return (town_1b & 7) in (2, 3, 6)


def castle_materials_days(town_1b: int, player_rank6: int) -> int:
    """0x459456: base 12|14 then sub player[+6] (unsigned 16-bit arithmetic in game)."""
    base = 12 if town_special_for_castle(town_1b) else 14
    return (base - (player_rank6 & 0xFF)) & 0xFFFF


def main():
    print('=== tea buy/sell ===')
    check('tea buy 100/0 = 100', tea_buy_price(100, 0) == 100)
    check('tea sell 90%', tea_sell_price(100, 0) == 90)
    check('tea high prog', tea_buy_price(100, 100) == 50 and tea_sell_price(100, 100) == 45)

    print('=== treasure buy/sell (base=value/10) ===')
    check('div10(1000)=100', div10(1000) == 100)
    check('treas buy v1000 p0 = 200', treasure_buy_quote(1000, 0) == 200)
    check('treas buy v1000 p100 = 150', treasure_buy_quote(1000, 100) == 150)
    check('treas sell normal p0 = 206', treasure_sell_quote(1000, 0, 3) == 206)
    check('treas sell normal p100 = 100', treasure_sell_quote(1000, 100, 3) == 100)
    check('treas sell nanban p0 = 100', treasure_sell_quote(1000, 0, 5) == 100)
    check('treas sell nanban p100 = 150', treasure_sell_quote(1000, 100, 5) == 150)
    check('sell gold *10', treasure_sell_gold(250) == 2500)

    print('=== shop ×1.5 ===')
    check('shop 100→150', shop_buy_price(100) == 150)

    print('=== rice (gold/10 in caps) ===')
    check('rice buy cap', rice_buy_cap(1000, 5000) == 2000)
    check('rice sell blocked', rice_sell_cap(400, 1000) is None)
    check('rice sell ok', rice_sell_cap(1000, 5000) == 5000)
    check('tier', rice_tier_label(3) == '便宜' and rice_tier_label(12) == '昂贵')

    print('=== castle materials days (0x459456) ===')
    check('special type2 →12', castle_materials_days(2, 0) == 12)
    check('normal type0 →14', castle_materials_days(0, 0) == 14)
    check('type6 rank3 →9', castle_materials_days(6, 3) == 9)
    check('type3 rank5 →7', castle_materials_days(0x13, 5) == 7)
    check('not special mask', not town_special_for_castle(1) and town_special_for_castle(0x1a))

    print(f'\n{PASS} PASS / {FAIL} FAIL')
    return 0 if FAIL == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
