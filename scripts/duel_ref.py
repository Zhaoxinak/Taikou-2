#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
太阁立志传2 — 单挑（一骑讨）卡牌对战系统 参考实现
================================================
来源：脱壳映像 scripts/_unpacked_mem.bin (base 0x400000)

破译要点（全部经反汇编坐实，见 duel_spec.json）：
  0x504fb0  卡牌/指令名表（stride 8，10 项）
  0x504ff8  主菜单 5 项（进攻/防御/特殊/逃走/替换）
  0x504fb8  「特殊」子菜单 4 项（瞄准/快刀/击中要害/一击必杀），stride 16
  0x47b5c0  菜单选择函数 (default_idx, callback, arg)
  0x4682f0  主菜单回调（取 5 项指针表）
  0x468250  特殊子菜单回调（取 4 项指针表）
  0x468340 / 0x468860  双方攻击处理（成员函数，thiscall）
  0x468290  攻击判定（返回 0..4，由 0x4684c0 跳表分发）
  0x4665d0  伤害分档 → 台词（4 档 × 2 视角）
  0x4675e0  挑衅（需「口才」技能）
  0x4673a0  丢沙子（需「忍术」技能）
  0x4670c0 / 0x467970  威吓
  0x467a70 / 0x467c80 / 0x468f00  烟雾弹 · 逃走
  0x468000 / 0x4691d0 / 0x469310  换人（替换）
  0x468cd0 / 0x46a030 / 0x46a680  求饶（金钱/物品）
  0x466490  体力耗尽（败北）

自检： python scripts/duel_ref.py
"""
import os
import re
import struct

BASE = 0x400000
HERE = os.path.dirname(os.path.abspath(__file__))
_mem = None
_texts = None


def mem():
    global _mem
    if _mem is None:
        with open(os.path.join(HERE, '_unpacked_mem.bin'), 'rb') as f:
            _mem = f.read()
    return _mem


def u8(va):
    return mem()[va - BASE]


def u16(va):
    return struct.unpack_from('<H', mem(), va - BASE)[0]


def cstr(va, maxn=16):
    m = mem()
    o = va - BASE
    e = m.find(b'\x00', o, o + maxn)
    if e < 0:
        e = o + maxn
    return m[o:e].decode('gbk', 'replace')


# ---------------------------------------------------------------- 常量
PROVOKE_STR = 0x504fb0       # '挑  衅'（挑衅指令名，单条，6B+2 null）

MAIN_MENU = 0x504ff8         # 主菜单 5 项（stride 8）
MENU_STRIDE = 8
MENU_COUNT = 5

SPECIAL_MENU = 0x504fb8      # 「特殊」子菜单 4 项
SPECIAL_STRIDE = 16
SPECIAL_COUNT = 4

# 0x4665d0 伤害分档阈值（从指令立即数读出自校验）
DMG_T1 = 8                   # cmp bx, 8   @0x46662c
DMG_T2 = 0x18                # cmp bx,0x18 @0x466644
DMG_SITES = (0x46662c, 0x466644)

# 台词 id（v = 1 表示 [this+0x10] != 0，即敌方视角）
BARK_BASE = {0: 0x17b2, 1: 0x17b0, 2: 0x17ae, 3: 0x17ac}

# 消息块
DUEL_MSGID_LO = 0x1770       # 6000
DUEL_MSGID_HI = 0x17dd       # 6045

MSG_FILES = ['MESSAGE1.LZW', 'MESSAGE2.LZW', 'MESSAGE3.LZW', 'MESSAGE4.LZW']
MSG_SLOTS = 2000


def load_texts():
    """载入 4 文件全部文本 → {id: text}（id = file*2000 + 序号）"""
    global _texts
    if _texts is not None:
        return _texts
    _texts = {}
    path = os.path.join(HERE, '_probe', 'msgx', 'all_messages.txt')
    for fi, fn in enumerate(MSG_FILES):
        pat = re.compile(r'^\[' + re.escape(fn) + r'#(\d+)\] (.*)$')
        for line in open(path, encoding='utf-8'):
            m = pat.match(line.rstrip('\n'))
            if m:
                _texts[fi * MSG_SLOTS + int(m.group(1))] = m.group(2)
    return _texts


def msgx_resolve(msgid):
    """0x493500：file = id // 2000，序号 = id - file*2000"""
    fid = (msgid & 0xffff) // MSG_SLOTS
    if fid > 3:
        return (None, None)
    return (MSG_FILES[fid], (msgid & 0xffff) - fid * MSG_SLOTS)


def msgx_text(msgid):
    return load_texts().get(msgid & 0xffff)


# ---------------------------------------------------------------- 名表
def provoke_name():
    """挑衅指令名（单条 8B 槽）"""
    return cstr(PROVOKE_STR, 8)


def duel_vocab():
    """单挑全部指令名 = 挑衅 + 特殊 4 项 + 主菜单 5 项（共 10 个动作）"""
    return [provoke_name()] + [x.strip() for x in special_items()] + [x.strip() for x in menu_items()]


def menu_items():
    """主菜单 5 项：进攻/防御/特殊/逃走/替换"""
    return [cstr(MAIN_MENU + MENU_STRIDE * i, MENU_STRIDE) for i in range(MENU_COUNT)]


def special_items():
    """「特殊」子菜单 4 项：瞄准/快刀/击中要害/一击必杀"""
    return [cstr(SPECIAL_MENU + SPECIAL_STRIDE * i, 16) for i in range(SPECIAL_COUNT)]


# ---------------------------------------------------------------- 台词
def damage_bark(dmg, enemy_view=False):
    """0x4665d0：伤害 → 台词 msgid。
    档位：0 / 1-8 / 9-24 / >24；v = 1 时 id-1（敌方视角）。"""
    if dmg <= 0:
        tier = 0
    elif dmg <= DMG_T1:
        tier = 1
    elif dmg <= DMG_T2:
        tier = 2
    else:
        tier = 3
    v = 1 if enemy_view else 0
    return BARK_BASE[tier] - v


def damage_bark_tier(dmg):
    """伤害 → 台词档位（0/1/2/3），与下方伤害模型的 damage_tier 无关"""
    if dmg <= 0:
        return 0
    if dmg <= DMG_T1:
        return 1
    if dmg <= DMG_T2:
        return 2
    return 3


# ---------------------------------------------------------------- 自检
def _ok(cond, msg):
    print(('  [OK]   ' if cond else '  [FAIL] ') + msg)
    return bool(cond)


# ---------------------------------------------------------------- 伤害模型
# 0x4687b0：档位 tier → word[0x5149a4]
DMG_BASE_TABLE = 0x505020     # 4 × 7 word（值 0..3）
DMG_CAP_TABLE = 0x504d40      # 4 word：1 / 2 / 2 / 3
TIER_ROWS = 4
TIER_COLS = 7

# 0x4698d0：伤害值 = bonus + rand()%tier
BONUS_P15 = 0x0f              # 15%
BONUS_P55 = 0x37              # 55%


def rand_n(n):
    """0x4ebd60(n)：n < 2 时**直接返回 0**（无除零风险）；否则 rand()%n。"""
    if n < 2:
        return 0
    import random
    return random.randrange(n)


def dmg_base_table():
    """4 档 × 7 列的伤害基表（word，值 0..3）"""
    return [[u16(DMG_BASE_TABLE + 2 * (r * TIER_COLS + c)) for c in range(TIER_COLS)]
            for r in range(TIER_ROWS)]


def dmg_cap_table():
    return [u16(DMG_CAP_TABLE + 2 * i) for i in range(TIER_ROWS)]


def skill_tier(acting_side_flag, side_a_byte, side_b_byte):
    """0x466e80(this) → 技能档 0..3（byte & 3）"""
    return (side_a_byte if acting_side_flag else side_b_byte) & 3


def damage_tier(tier_idx, action_code, might, r_base, r_bonus):
    """复刻 0x4687b0 → word[0x5149a4]
    tier_idx   : 0..3（0x466e80 取的技能档）
    action_code: word[this+0xc]（3 或 4 时跳过武力加成）
    might      : 武力 word（0x466e40，仅 < 60 时生效，魔数 0x66666667 → ÷20）
    """
    base = dmg_base_table()[tier_idx][r_base % TIER_COLS]
    if action_code not in (3, 4) and might < 60:
        mod = 4 - (might // 20)
        base += r_bonus % mod if mod >= 2 else 0
    cap = dmg_cap_table()[tier_idx]
    return base if base < cap else cap


def damage_value(tier, r100, r_rand):
    """复刻 0x4698d0 → word[0x5149a8]：bonus(rand%100) + rand()%tier"""
    if r100 < BONUS_P15:
        bonus = 0
    elif r100 < BONUS_P55:
        bonus = 1
    else:
        bonus = 2
    return bonus + (r_rand % tier if tier >= 2 else 0)


def duel_damage(tier_idx, action_code, might, r_base, r_bonus, r100, r_rand):
    """一次攻击的完整伤害：档位 → 伤害值"""
    t = damage_tier(tier_idx, action_code, might, r_base, r_bonus)
    return t, damage_value(t, r100, r_rand)


def apply_damage(hp_a, hp_b, attacker_flag, dmg):
    """复刻 0x466340：逐点扣血（每点一帧动画），返回 (hp_a, hp_b)。
    attacker_flag = dword[0x514808]；非 0 → 扣 hp_b，否则扣 hp_a。
    hp_a = word[0x514995]，hp_b = word[0x514835]。
    """
    a, b = hp_a, hp_b
    for _ in range(max(0, dmg)):
        if attacker_flag:
            b -= 1
        else:
            a -= 1
    return a, b


def damage_distribution(tier_idx, action_code, might, samples=4000, seed=1):
    """蒙特卡洛：给定档位/武力下的伤害分布（用于平衡性核对）"""
    import random
    rnd = random.Random(seed)
    hist = {}
    for _ in range(samples):
        t = damage_tier(tier_idx, action_code, might,
                        rnd.randrange(TIER_COLS), rnd.randrange(100))
        v = damage_value(t, rnd.randrange(100), rnd.randrange(100))
        hist[v] = hist.get(v, 0) + 1
    return {k: hist[k] / samples for k in sorted(hist)}


def selfcheck():
    print('== 太阁2 单挑（一骑讨）卡牌系统 自检 ==')
    p = n = 0

    # 1) 文本库完整（含 MESSAGE4）
    t = load_texts()
    n += 1; p += _ok(len(t) == 6211, f'MSGX 文本库 {len(t)} 条（4 文件：1735+1559+1876+1041）')

    # 2) 主菜单 5 项
    mi = menu_items()
    n += 1; p += _ok(mi == [' 进攻 ', ' 防御 ', ' 特殊 ', ' 逃走 ', ' 替换 '],
                     '主菜单 0x504ff8 = ' + ' / '.join(x.strip() for x in mi))

    # 3) 特殊子菜单 4 项
    si = special_items()
    n += 1; p += _ok(si == ['  瞄准  ', '  快刀  ', '击中要害', '一击必杀'],
                     '特殊子菜单 0x504fb8 = ' + ' / '.join(x.strip() for x in si))

    # 4) 挑衅名 + 10 个动作词表
    n += 1; p += _ok(provoke_name() == '挑  衅', f'挑衅指令名 0x504fb0 = {provoke_name()!r}')
    vocab = duel_vocab()
    n += 1; p += _ok(len(vocab) == 10, '单挑动作词 10 个 = ' + ' / '.join(vocab))

    # 5) 伤害阈值从指令立即数读出（cmp bx, imm8 → 66 83 FB xx）
    got = []
    for site in DMG_SITES:
        o = site - BASE
        got.append((mem()[o], mem()[o + 1], mem()[o + 2], mem()[o + 3]))
    n += 1; p += _ok(got[0] == (0x66, 0x83, 0xfb, DMG_T1) and got[1] == (0x66, 0x83, 0xfb, DMG_T2),
                     f'伤害阈值自指令读出：cmp bx,{DMG_T1} / cmp bx,{DMG_T2}')

    # 6) 分档映射
    n += 1; p += _ok([damage_bark_tier(d) for d in (0, 1, 8, 9, 24, 25)] == [0, 1, 1, 2, 2, 3],
                     '伤害分档 0 / 1-8 / 9-24 / >24 边界正确')

    # 7) 台词 id 落在单挑消息块内且能取到文本
    ids = [damage_bark(d, v) for d in (0, 5, 15, 30) for v in (False, True)]
    n += 1; p += _ok(all(DUEL_MSGID_LO <= i <= DUEL_MSGID_HI for i in ids)
                     and all(msgx_text(i) for i in ids),
                     '8 条伤害台词 id 全部落在 0x1770-0x17dd 且有文本')

    # 8) 台词语义抽查：最大档（我方视角 / 敌方视角各一条）
    top_self = msgx_text(damage_bark(30, False))
    top_foe = msgx_text(damage_bark(30, True))
    n += 1; p += _ok('高手' in (top_self or '') and '厉害' in (top_foe or ''),
                     f'最大伤害档台词：我={top_self!r} 敌={top_foe!r}')

    # 9) 最小档 = 零伤害嘲讽
    zero = msgx_text(damage_bark(0))
    n += 1; p += _ok(zero is not None and '两下子' in zero, f'零伤害台词 = {zero!r}')

    # 10) 单挑模块关键消息可解析（攻击/伤害/落空）
    trio = [msgx_text(0x1770), msgx_text(0x1775), msgx_text(0x1777)]
    n += 1; p += _ok(all(trio) and '%s的攻击' == trio[0],
                     '关键消息解析：' + ' | '.join(trio))

    # ---- 伤害模型（续63）----
    # 11) 伤害基表 4×7
    bt = dmg_base_table()
    n += 1; p += _ok(bt == [[0, 0, 0, 0, 0, 1, 1],
                            [0, 0, 0, 1, 1, 1, 2],
                            [0, 0, 1, 1, 1, 2, 2],
                            [0, 1, 1, 1, 2, 2, 3]],
                     f'伤害基表 0x505020 = {bt}')

    # 12) 上限表
    cap = dmg_cap_table()
    n += 1; p += _ok(cap == [1, 2, 2, 3], f'伤害上限表 0x504d40 = {cap}')

    # 13) rand()%n 在 n<2 时返回 0（0x4ebd60 的 cmp si,2 保护）
    n += 1; p += _ok(rand_n(0) == 0 and rand_n(1) == 0,
                     'rand()%n 边界保护：n<2 → 0（无除零）')

    # 14) 档位钳制生效
    worst = [damage_tier(i, 1, 10, 6, 0) for i in range(4)]
    n += 1; p += _ok(all(worst[i] <= cap[i] for i in range(4)),
                     f'档位被上限钳制：{worst} ≤ {cap}')

    # 15) 伤害值上限 = 2 + (tier-1)
    hi = max(damage_value(3, 99, r) for r in range(100))
    lo = min(damage_value(3, 0, r) for r in range(100))
    n += 1; p += _ok(hi == 4 and lo == 0, f'单次伤害取值域 [{lo}, {hi}]（bonus 0-2 + rand%3）')

    # 16) 扣血方向
    a1, b1 = apply_damage(10, 10, 0, 3)
    a2, b2 = apply_damage(10, 10, 1, 3)
    n += 1; p += _ok((a1, b1) == (7, 10) and (a2, b2) == (10, 7),
                     '扣血方向正确（0x514808=0 扣 A / ≠0 扣 B）')

    # 17) 蒙特卡洛：武力越高伤害越低（4-B//20 修正方向）
    low = damage_distribution(3, 1, 10)          # 武力 10 → mod = 4
    high = damage_distribution(3, 1, 55)         # 武力 55 → mod = 2
    exp_low = sum(k * v for k, v in low.items())
    exp_high = sum(k * v for k, v in high.items())
    n += 1; p += _ok(exp_low > exp_high,
                     f'武力修正方向正确：武力10 期望 {exp_low:.2f} > 武力55 期望 {exp_high:.2f}')

    print(f'\n自检 {p}/{n} 通过' + ('  ✅ ALL PASS' if p == n else '  ❌ 有失败项'))
    return p == n


if __name__ == '__main__':
    import sys
    ok = selfcheck()
    if '--dump' in sys.argv:
        print('\n== 单挑模块导出 ==')
        print('动作词:', duel_vocab())
        print('主菜单   :', menu_items())
        print('特殊子菜单:', special_items())
        print('\n伤害分档台词:')
        for d in (0, 5, 15, 30):
            for v in (False, True):
                i = damage_bark(d, v)
                print(f'  dmg={d:3d} {"敌" if v else "我"}  0x{i:04x}  {msgx_text(i)}')
    sys.exit(0 if ok else 1)
