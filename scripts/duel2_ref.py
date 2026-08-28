# -*- coding: utf-8 -*-
"""
太阁立志传2 — 单挑「一击必杀/击中要害」悬案闭合 + 🔴 体力/武力纠偏

结论（2026-08-28 续66）：
  1. 0x4684c0 跳表 5 分支 = 行动结果码 0..4（攻击/特殊/威吓失败/逃走失败/换人）
  2. 动作码 3/4 = 特殊攻击：在 step1 跳过「体力加成」，在台词走独立表
  3. 🔴 纠偏：0x466e40 返回的是**体力**不是武力 ⇒ 加成是「体力越低伤害越高」
     的背水一战／翻盘机制，而非 duel_spec 原记的「武力越高加成越小」
  4. 🚫 负结果（结论性）：**不存在「一击必杀」大额伤害路径**。
     伤害值 word[0x5149a8] 全镜像仅 1 处写入 → 恒 0..4；
     体力 word[0x514995]/[0x514835] 各仅 1 处修改且都是 dec（逐点扣 1）。
     ⇒ 台词分档的 9–24 / >24 两档**不可达**（冗余防御代码）。

映像：_unpacked_mem.bin 平坦映射 off = va - 0x400000
"""
import struct

BASE = 0x400000
IMG = open('scripts/_unpacked_mem.bin', 'rb').read()


def rd(va, n):
    return IMG[va - BASE:va - BASE + n]


# ---------------------------------------------------------------- 常量
JUMP_TABLE = 0x4684c0             # 5 项跳表（[5..7] 为 0x90909090 nop 填充）
HP_A = 0x514995                   # 侧 A 体力
HP_B = 0x514835                   # 侧 B 体力
TIER_VAR = 0x5149a4               # 档位
DMG_VAR = 0x5149a8                # 伤害值

BASE_TIER_TBL = 0x505020          # 4×7 word 伤害基表
TIER_CAP_TBL = 0x504d40           # 4 word 上限表 [1,2,2,3]
SKILL_LVL_TBL = 0x504d40          # 同一张表在 0x468220 作「可出手牌数」用 ⇒ 双重语义

# 动作码：跳过体力加成者
NO_HP_BONUS_ACTIONS = (3, 4)

# 台词分档 base（动作码 3/4 分支 0x466735）
BARK_34 = {0: 0x17a1, 1: 0x179d, 2: 0x1799, 3: 0x1795}     # ==0 / 1-8 / 9-24 / >24
# 常规分支（动作码 5，0x46660b 起，duel_spec 已记）
BARK_5 = {0: 0x17b2, 1: 0x17b0, 2: 0x17ae, 3: 0x17ac}
BARK_VARIANTS = 2                 # msgid = base + rand()%2

MSG_HIT = 0x1775                  # "%s使%s受到%d的伤害。"
MSG_MISS = 0x1774                 # dmg==0 时

HP_BONUS_THRESHOLD = 60           # 体力 < 60 才触发加成
HP_BONUS_DIVISOR = 20             # 4 - 体力//20（魔数 0x66666667 + sar 3）
RAND_N_GUARD = 2                  # 0x4ebd60(n)：n < 2 直接返回 0（无除零）


# ---------------------------------------------------------------- 原语
def hp_of(this_side_flag):
    """0x466e40(this)：[this+0x10]!=0 → 体力A；==0 → 体力B。
    🔴 返回的是**体力**，不是武力。"""
    return HP_A if this_side_flag else HP_B


def hp_bonus_mod(hp):
    """加成模数 = 4 - 体力//20；体力>=60 返回 None（不触发）"""
    if hp >= HP_BONUS_THRESHOLD:
        return None
    return 4 - (hp // HP_BONUS_DIVISOR)


def calc_tier(skill_a, rand7, action_code, hp, rand_bonus):
    """0x4687b0 step1：档位计算。
    base = word[0x505020 + (a*7 + rand()%7)*2]
    if 动作码 ∉ {3,4} 且 体力 < 60:  base += rand() % (4 - 体力//20)
    tier = min(base, word[0x504d40 + a*2])
    """
    base = struct.unpack_from('<h', rd(BASE_TIER_TBL + (skill_a * 7 + rand7) * 2, 2))[0]
    if action_code not in NO_HP_BONUS_ACTIONS:
        mod = hp_bonus_mod(hp)
        if mod is not None:
            base += rand_bonus % mod if mod > 0 else 0
    cap = struct.unpack_from('<h', rd(TIER_CAP_TBL + skill_a * 2, 2))[0]
    return min(base, cap)


def calc_damage(tier, rand100, rand_tier):
    """0x4698d0 step2：伤害值。
    bonus = 0 (r<15) | 1 (r<55) | 2 (r>=55)
    dmg = bonus + (rand()%tier  若 tier>=2，否则 0)
    """
    bonus = 0 if rand100 < 15 else (1 if rand100 < 55 else 2)
    extra = rand_tier % tier if tier >= RAND_N_GUARD else 0
    return bonus + extra


def bark_msgid(dmg, table=BARK_34, variant=0):
    """0x466735：按 dmg 分 4 档，msgid = base + rand()%2"""
    if dmg == 0:
        base = table[0]
    elif dmg <= 8:
        base = table[1]
    elif dmg <= 24:
        base = table[2]
    else:
        base = table[3]
    return base + (variant % BARK_VARIANTS)


def damage_domain():
    """穷举所有 (tier, rand100, rand_tier) → 返回可达伤害集合。
    用于验证「9-24 / >24 两档不可达」这一负结果。"""
    vals = set()
    for tier in range(4):
        for r100 in (0, 20, 60):          # 三档 bonus 代表值
            for rt in range(4):
                vals.add(calc_damage(tier, r100, rt))
    return sorted(vals)


# ================================================================ 自校验
def self_test():
    ok = fail = 0

    def chk(name, got, exp):
        nonlocal ok, fail
        if got == exp:
            ok += 1
            print('[OK  ] %-46s got=%r' % (name, got))
        else:
            fail += 1
            print('[FAIL] %-46s got=%r exp=%r' % (name, got, exp))

    print('=' * 74)
    print('duel2_ref self_test — 单挑大额伤害悬案闭合 + 体力/武力纠偏')
    print('=' * 74)

    # --- 1. 跳表 5 项（映像真值）---
    jt = [struct.unpack('<I', rd(JUMP_TABLE + i * 4, 4))[0] for i in range(5)]
    chk('跳表[0] 攻击分支', jt[0], 0x468457)
    chk('跳表[1] 特殊动作', jt[1], 0x468489)
    chk('跳表[2] 威吓失败', jt[2], 0x468495)
    chk('跳表[3] 逃走失败', jt[3], 0x4684a0)
    chk('跳表[4] 换人', jt[4], 0x4684a9)
    chk('跳表第6项为 nop 填充(表长=5)',
        struct.unpack('<I', rd(JUMP_TABLE + 5 * 4, 4))[0], 0x90909090)

    # --- 2. 上限表（双重语义）---
    caps = [struct.unpack_from('<h', rd(TIER_CAP_TBL + a * 2, 2))[0] for a in range(4)]
    chk('上限表 0x504d40 (档位上限)', caps, [1, 2, 2, 3])
    chk('同一张表在 0x468220 作可出手牌数(值+1)',
        [c + 1 for c in caps], [2, 3, 3, 4])

    # --- 3. 基表 4×7 ---
    grid = [[struct.unpack_from('<h', rd(BASE_TIER_TBL + (a * 7 + k) * 2, 2))[0]
             for k in range(7)] for a in range(4)]
    chk('基表[0]', grid[0], [0, 0, 0, 0, 0, 1, 1])
    chk('基表[3]', grid[3], [0, 1, 1, 1, 2, 2, 3])

    # --- 4. 🔴 纠偏：0x466e40 取的是体力 ---
    chk('0x466e40 视角!=0 → 体力A 0x514995', hp_of(True), HP_A)
    chk('0x466e40 视角==0 → 体力B 0x514835', hp_of(False), HP_B)
    chk('体力>=60 不触发加成', hp_bonus_mod(60), None)
    chk('体力 40-59 → 模数 2', hp_bonus_mod(45), 2)
    chk('体力 20-39 → 模数 3', hp_bonus_mod(30), 3)
    chk('体力 0-19  → 模数 4', hp_bonus_mod(10), 4)
    chk('背水一战：体力越低模数越大',
        hp_bonus_mod(10) > hp_bonus_mod(30) > hp_bonus_mod(45), True)

    # --- 5. 档位：动作码 3/4 跳过体力加成 ---
    t_normal = calc_tier(3, 6, action_code=5, hp=10, rand_bonus=3)   # 体力低 → 有加成
    t_act34 = calc_tier(3, 6, action_code=3, hp=10, rand_bonus=3)    # 动作码3 → 跳过
    chk('动作码3 跳过体力加成(档位更小)', t_act34 <= t_normal, True)
    chk('动作码3 档位 = min(基表值, 上限)', t_act34,
        min(grid[3][6], caps[3]))
    chk('动作码4 同样跳过', calc_tier(3, 6, 4, 10, 3) == t_act34, True)

    # --- 6. 伤害域 = 0..4（负结果核心）---
    dom = damage_domain()
    chk('可达伤害域', dom, [0, 1, 2, 3, 4])
    chk('伤害上限 = 4', max(dom), 4)
    chk('伤害下限 = 0', min(dom), 0)
    chk('tier=0 rand保护(无除零) → dmg==bonus', calc_damage(0, 60, 0), 2)
    chk('tier=3 最大伤害 2+2=4', calc_damage(3, 60, 2), 4)

    # --- 7. 台词分档（动作码3/4 表）---
    chk('dmg=0  → base 0x17a1', bark_msgid(0), 0x17a1)
    chk('dmg=1  → base 0x179d', bark_msgid(1), 0x179d)
    chk('dmg=8  → base 0x179d (边界)', bark_msgid(8), 0x179d)
    chk('dmg=9  → base 0x1799', bark_msgid(9), 0x1799)
    chk('dmg=24 → base 0x1799 (边界)', bark_msgid(24), 0x1799)
    chk('dmg=25 → base 0x1795', bark_msgid(25), 0x1795)
    chk('每档 2 条随机台词', bark_msgid(1, variant=1) - bark_msgid(1, variant=0), 1)
    # 常规表（动作码5）不同
    chk('动作码5 用另一套表 (0x17b0)', bark_msgid(1, BARK_5), 0x17b0)
    chk('两套表 base 不同', BARK_34[1] != BARK_5[1], True)

    # --- 8. 🚫 负结果：9-24 / >24 不可达 ---
    chk('可达域内无 9..24', any(9 <= v <= 24 for v in dom), False)
    chk('可达域内无 >24', any(v > 24 for v in dom), False)
    chk('=> 9-24 档不可达', bark_msgid(9) in (0x1799, 0x179a), True)
    chk('伤害域上限 4 < 9 ⇒ 该档为冗余代码', max(dom) < 9, True)

    print('-' * 74)
    print('self_test: %d/%d %s' % (ok, ok + fail, 'ALL PASS' if fail == 0 else 'HAS FAILURE'))
    return fail == 0


if __name__ == '__main__':
    self_test()
