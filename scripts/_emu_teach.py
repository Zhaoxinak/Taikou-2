#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
续28/续29 — 授艺天数 / 花费 / 技能位与五维属性增长。

主路径：
  0x45f1e0  选天数 UI
  0x45f2b0  按日循环（每天扣 2 金 + 疲劳）
  0x45f710  选修行动作（0..7）
  0x45fca0  mode0-2 → 技能 2bit；mode≥3 → 0x45feb0 五维属性

旁路纠偏（非授艺）：
  0x4422b0 / 0x442270  茶具出售：price = getValue*(100-(prog>>1))/100*90/100
  0x51662e = 金钱（结构 0x516610+0x1e），非日历
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


# ─── days / cost (0x45f1e0) ───────────────────────────────────────────
def max_train_days(day_of_month: int, gold: int) -> int:
    """day_of_month = byte[0x5205f2]; gold = word[0x51662e]."""
    avail = 0x1F - (day_of_month & 0xFF)
    if avail < 0:
        avail = 0
    by_gold = gold >> 1
    return min(avail, by_gold) if gold >= 2 else 0


def train_cost(days: int) -> int:
    """Each day: 0x44e350(2) → subtract 2 gold."""
    return days * 2


# ─── signed /100 (magic 0x51EB851F), tea sell (0x442270/0x4422b0) ────
def div100(x: int) -> int:
    prod = x * 0x51EB851F
    prod &= (1 << 64) - 1
    if prod >= (1 << 63):
        prod -= (1 << 64)
    edx = prod >> 32
    edx >>= 5
    return edx + (1 if edx < 0 else 0)


def tea_sell_price(value: int, progress: int) -> int:
    """0x442270 then *90/100. progress = player.byte[+7]."""
    factor = 100 - ((progress & 0xFFFF) >> 1)
    base = div100(value * factor)
    return div100(base * 90)


# ─── skill 2-bit pack at NPC[+0xf .. +0x11] ──────────────────────────
SKILL_SLOTS = [
    (0, 0), (0, 2), (0, 4), (0, 6),
    (1, 0), (1, 2), (1, 4), (1, 6),
    (2, 0), (2, 2),
]


def get_skill(buf: bytearray, idx: int) -> int:
    off, sh = SKILL_SLOTS[idx]
    return (buf[off] >> sh) & 3


def inc_skill(buf: bytearray, idx: int) -> bool:
    """Mirror 0x4a3040 + idx*0x20 family; return True if leveled."""
    off, sh = SKILL_SLOTS[idx]
    cur = (buf[off] >> sh) & 3
    if cur >= 3:
        return False
    mask = ~(3 << sh) & 0xFF
    buf[off] = (buf[off] & mask) | ((cur + 1) << sh)
    return True


MODE_TO_SKILL = {0: 0, 1: 7, 2: 5}  # 口才 / 筑城 / 兵法


def growth_roll_mode0_or_2(sub: int, roll: int) -> bool:
    n = 16 - (sub & 0xF)
    if n <= 0:
        n = 1
    return (roll % n) == 0


def growth_roll_mode1(attr_sum: int, roll: int) -> bool:
    return (roll % 0x258) < attr_sum


def fame_for_new_level(level: int) -> int:
    return level * 500


# ─── mode≥3 attribute growth (0x45feb0 / 0x4600d0) ───────────────────
ATTR_NAMES = ['统御力', '武力', '内政力', '外交力', '魅力']
ATTR_OFF = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}  # relative to +0xa
MODE_EXPECTED_TIER = {3: 0, 4: 1, 5: 2, 6: 3}  # helper word[+8]>>8&3


def mode_ge3_base(mode: int) -> int:
    """esi after 0x45fec7..fedd: mode==4 → 16, else 20."""
    return 16 if mode == 4 else 20


def _abs_sar1(x: int) -> int:
    if x < 0:
        x = -x
    return x >> 1


def _abs_mul3_sar1(x: int) -> int:
    if x < 0:
        x = -x
    return (x * 3) >> 1


def growth_mode_ge3(mode: int, sub: int, helper_tier, roll_a: int, roll_b: int = 0):
    """
    Returns (learner_ok, helper_ok).
    helper_tier=None → solo (helper ptr null).
    """
    base = mode_ge3_base(mode)
    diff = base - (sub & 0xFFFF)
    if helper_tier is None:
        n = max(diff, 1)
        return (roll_a % n) == 0, False

    expected = MODE_EXPECTED_TIER.get(mode)
    if helper_tier == expected:
        n = max(_abs_sar1(diff), 1)
        ok = (roll_a % n) == 0
        return ok, ok

    n1 = max(diff, 1)
    n2 = max(_abs_mul3_sar1(diff), 1)
    return (roll_a % n1) == 0, (roll_b % n2) == 0


def attr_target_for_mode(mode: int, read_roll_lt_50: bool = False) -> int:
    """0x4600d0 attr index. 读书: 0x4ebe40(50) → 内政力 else 统御力."""
    if mode == 3:
        return 1
    if mode == 4:
        return 2 if read_roll_lt_50 else 0
    if mode == 5:
        return 4
    if mode == 6:
        return 3
    raise ValueError(mode)


def bump_attr(attrs: bytearray, idx: int, delta: int = 1) -> int:
    """min(cur+delta, 100); attrs = 5 bytes at character+0xa."""
    off = ATTR_OFF[idx]
    v = min(attrs[off] + delta, 100)
    attrs[off] = v
    return v


def main():
    print('=== teach days / cost ===')
    check('day1 gold100 → max 30', max_train_days(1, 100) == 30, str(max_train_days(1, 100)))
    check('day1 gold40 → max 20 (gold/2)', max_train_days(1, 40) == 20)
    check('day28 gold100 → max 3', max_train_days(28, 100) == 3)
    check('day1 gold3 → max 1', max_train_days(1, 3) == 1)
    check('gold1 → 0 (need >=2)', max_train_days(1, 1) == 0)
    check('cost 10d = 20', train_cost(10) == 20)

    print('=== tea sell price (commerce, not teach) ===')
    check('v100 p0 → 90', tea_sell_price(100, 0) == 90)
    check('v100 p100 → 45', tea_sell_price(100, 100) == 45)
    check('v200 p50 → 135', tea_sell_price(200, 50) == 135)

    print('=== skill bit pack ===')
    buf = bytearray(3)
    for i in range(10):
        assert get_skill(buf, i) == 0
        check(f'inc skill{i} 0→1', inc_skill(buf, i) and get_skill(buf, i) == 1)
        inc_skill(buf, i); inc_skill(buf, i)
        check(f'skill{i} cap3', get_skill(buf, i) == 3 and not inc_skill(buf, i))

    print('=== growth odds mode0-2 ===')
    check('mode0 sub0: roll0 ok', growth_roll_mode0_or_2(0, 0))
    check('mode0 sub0: roll1 fail', not growth_roll_mode0_or_2(0, 1))
    check('mode0 sub8: mod8', growth_roll_mode0_or_2(8, 0) and not growth_roll_mode0_or_2(8, 1))
    check('mode1 sum100: roll99 ok', growth_roll_mode1(100, 99))
    check('mode1 sum100: roll100 fail', not growth_roll_mode1(100, 100))
    check('fame lv2 = 1000', fame_for_new_level(2) == 1000)
    check('mode map 0/1/2', MODE_TO_SKILL == {0: 0, 1: 7, 2: 5})

    print('=== mode≥3 attribute growth ===')
    check('base mode3/5/6=20', mode_ge3_base(3) == mode_ge3_base(5) == mode_ge3_base(6) == 20)
    check('base mode4=16', mode_ge3_base(4) == 16)
    check('solo mode3 sub0 roll0', growth_mode_ge3(3, 0, None, 0) == (True, False))
    check('solo mode3 sub0 roll1', growth_mode_ge3(3, 0, None, 1) == (False, False))
    check('solo mode4 sub0 n=16', growth_mode_ge3(4, 0, None, 0)[0] and not growth_mode_ge3(4, 0, None, 1)[0])
    check('match tier mode3', growth_mode_ge3(3, 0, 0, 0) == (True, True))
    check('match fail', growth_mode_ge3(3, 0, 0, 1) == (False, False))
    L, H = growth_mode_ge3(3, 0, 1, 0, 0)
    check('mismatch both', (L, H) == (True, True))
    L, H = growth_mode_ge3(3, 0, 1, 1, 1)
    check('mismatch none', (L, H) == (False, False))

    check('剑术→武力', attr_target_for_mode(3) == 1)
    check('读书 50%→内政', attr_target_for_mode(4, True) == 2)
    check('读书 else→统御', attr_target_for_mode(4, False) == 0)
    check('艺术→魅力', attr_target_for_mode(5) == 4)
    check('宝物→外交', attr_target_for_mode(6) == 3)

    attrs = bytearray([90, 99, 50, 100, 0])
    check('bump 武力 99→100', bump_attr(attrs, 1) == 100)
    check('bump cap', bump_attr(attrs, 1) == 100)
    check('外交 already 100 stays', bump_attr(bytearray([0, 0, 0, 100, 0]), 3) == 100)
    check('attr names', ATTR_NAMES == ['统御力', '武力', '内政力', '外交力', '魅力'])

    print(f'\n{PASS} PASS / {FAIL} FAIL')
    return 0 if FAIL == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
