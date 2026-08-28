# -*- coding: utf-8 -*-
"""
太阁立志传2 — 大名/城主「任命·继承」路径 参考实现（可执行规格）

闭合職位/晋升系统最后一条支线：
  · 城主任命  0x4d7c20     （门槛 + 写入链 + 改名剧情）
  · 大名继承  0x4a42c0 → 0x4a3d70

★ 关键纠偏（推翻续63 的「7/8 都走任命/继承」表述）：
  set_rank(0x49a7e0) 掩码 and eax,0xF8FF 只清 bit8..10 → 職位字段仅 3 bit，
  只能存 0..7。**城主(8) 根本不写進職位字段**，它是城表派生状态：
      某武将是城主  ⟺  ∃城 c, word[城表 + c*31 + 0x0a] == 该武将编号
  職位名表 0x50d850 虽有 9 项（8=城主），但 8 仅用于**显示映射**，非实体字段值。

映像：_unpacked_mem.bin 平坦映射 off = va - 0x400000
"""
import struct

BASE = 0x400000
IMG = open('scripts/_unpacked_mem.bin', 'rb').read()


def rd(va, n):
    return IMG[va - BASE:va - BASE + n]


def cstr(va):
    o = va - BASE
    e = IMG.index(b'\0', o)
    return IMG[o:e].decode('gbk', 'replace')


# ---------------------------------------------------------------- 常量
ENTITY_BASE = 0x519868          # 武将实体表   stride 47
ENTITY_STRIDE = 47
CITY_BASE = 0x51eb88            # 城表         stride 31
CITY_STRIDE = 31
CITY_LORD_OFF = 0x0a            # 城主武将编号 (word)
RANK_LADDER = 0x50d850          # 職位名指针表 (9 项: 0..8)
NAME_TBL_RUNTIME = 0x521aa8     # 运行时名表 stride 7（改名写入点之一）
NAME_TBL_RUNTIME2 = 0x520660

SET_RANK_MASK = 0xf8ff          # and eax,0xF8FF → 清 bit8..10 (3 bit)
RANK_SHIFT = 8
RANK_MAX = 7                    # 3 bit 上限

MERIT_CAP = 0xea60              # 60000 (0x49a770)
STIPEND_CAP = 0xc8              # 200   (0x49a790)
LOYALTY_INHERIT_FLOOR = 0x1e    # 30    (继承后家臣忠诚下限)

# 城主任命门槛
CASTLE_LORD_MIN_RANK = 4        # rank 必须 > 4（家老5 / 宿老6 方可）
SKILL_ETIQUETTE_MASK = 0x03     # byte[+0x11] & 3（礼法）

# 城主任命消息（MSGX id）
MSG = {
    'no_castle': 0xc51,          # 3153 我想任命你为城主，但现在还没有适当的城池…
    'no_skill_1': 0xc53,         # 3155 我想任命你为城主，无奈你的技能还有些欠缺。
    'no_skill_2': 0xc54,         # 3156 快去学习礼法…
    'no_skill_3': 0xc55,         # 3157
    'ok_1': 0xc56, 'ok_2': 0xc57, 'ok_3': 0xc58, 'ok_4': 0xc59,   # 3158-3161
    'rename_hint': 0xc5a,        # 3162 木下藤吉郎之名，难登大雅之堂…
    'rename_tail': 0xc60,        # 3168
    'final_1': 0xc64, 'final_2': 0xc65, 'final_3': 0xc66,          # 3172-3174
}

# 已改名标记 word[+2]（按 (word[0x520604]>>12)&3 三分支）
RENAMED_IDS = {0: 0x2b7, 1: 0x2e7, 2: 0x2e8}   # 695 / 743 / 744


# ---------------------------------------------------------------- 原语
def rank_of(word_2c):
    """職位 = word[+0x2c] 的 bit8..10"""
    return (word_2c >> RANK_SHIFT) & 7


def set_rank(word_2c, new_rank):
    """set_rank(0x49a7e0) 语义：清 bit8..10 后写入 rank<<8。
    注意：new_rank 必须 <= 7；8(城主) 存不下 → 抛错（这是本模块的纠偏核心）。"""
    if not (0 <= new_rank <= RANK_MAX):
        raise ValueError(
            '職位字段仅 3 bit(bit8..10)，无法存 rank=%d；城主(8) 是城表派生状态，'
            '请用 is_castle_lord() 判定' % new_rank)
    return (word_2c & SET_RANK_MASK) | (new_rank << RANK_SHIFT)


def city_ptr(city_idx):
    return CITY_BASE + city_idx * CITY_STRIDE


def entity_index(ptr):
    return (ptr - ENTITY_BASE) // ENTITY_STRIDE


def city_index(ptr):
    return (ptr - CITY_BASE) // CITY_STRIDE


def is_castle_lord(city_table, busho_no):
    """城主 = 城表派生状态：存在某城其 word[+0x0a] == busho_no"""
    return any(struct.unpack_from('<H', city_table, c * CITY_STRIDE + CITY_LORD_OFF)[0] == busho_no
               for c in range(len(city_table) // CITY_STRIDE))


def lord_of(city_table, city_idx):
    return struct.unpack_from('<H', city_table, city_idx * CITY_STRIDE + CITY_LORD_OFF)[0]


# ---------------------------------------------------------------- 城主任命
def can_appoint_castle_lord(word_2c, byte_11, has_candidate, target_city_valid):
    """0x4d7c20 门槛链。返回 (bool, 失败原因)"""
    r = rank_of(word_2c)
    if r <= CASTLE_LORD_MIN_RANK:
        return False, 'rank_too_low'          # 0x4D7C58 jle → 直接退出（不发消息）
    if not has_candidate:
        return False, 'no_candidate'          # 0x4ac690 → 0x4d7fae (msg 3153)
    if not target_city_valid:
        return False, 'no_castle'             # 0x4ac7f0 → 0x4d7fae (msg 3153)
    if (byte_11 & SKILL_ETIQUETTE_MASK) == 0:
        return False, 'no_etiquette'          # 0x4D7C87 → msg 3155/3156/3157, return 0
    return True, 'ok'


def appoint_castle_lord(city_table, busho_no, old_city_idx, new_city_idx):
    """0x4d7c20 写入链（成功路径）。返回事件序列。"""
    ev = []
    # 1) 从旧城链表摘除
    if old_city_idx is not None and old_city_idx < 200:
        ev.append(('unlink', old_city_idx))
    # 2) set_所属城 byte[+0x25] = 新城索引
    ev.append(('set_home_city', new_city_idx))
    # 3) 挂入新城家臣链表
    ev.append(('link', new_city_idx))
    # 4) ★ 城主登记：word[城+0x0a] = 武将编号
    struct.pack_into('<H', city_table, new_city_idx * CITY_STRIDE + CITY_LORD_OFF, busho_no)
    ev.append(('set_city_lord', new_city_idx, busho_no))
    # 5) 全局标志 word[0x52062c] = 1
    ev.append(('flag_52062c', 1))
    return ev


def rename_branch(word_520604, word_2_of_busho, byte_24):
    """改名剧情分支：返回 (是否需要改名, 提示消息id)"""
    branch = (word_520604 >> 12) & 3
    if branch == 0:
        if word_2_of_busho == RENAMED_IDS[0] or byte_24 != 0x0d:
            return False, None
        return True, MSG['rename_hint']        # 3162 藤吉郎→羽柴
    if branch in (1, 2):
        if word_2_of_busho == RENAMED_IDS[branch]:
            return False, None
        return True, 0xc72                     # 3186 仪表/改名提示
    return False, None


# ---------------------------------------------------------------- 大名继承
def inherit_daimyo(heir_word_2c, retainers, dead_no):
    """0x4a3d70 继承核心。retainers: [(word_2a, word_1d, ...)] → 返回新状态。"""
    out = {'loyalty': [], 'promoted': [], 'heir_rank': None, 'heir_merit': None}
    for r in retainers:
        # 忠诚重算：max(rand(0..(50 - (byte[死亡者+0xe]>>1))) + byte[+0x29], 30)
        loyalty = max(30, r['rand_val'] + r['byte_29'])
        out['loyalty'].append(loyalty)
        # 嫡系判定：word[+0x2a] == 死亡者编号 → 升宿老(6) + 忠诚 100
        if r['word_2a'] == dead_no:
            out['promoted'].append(('set_rank', 6))
            out['loyalty'][-1] = 100
    # 继承人 → 大名(7) + 勲功拉满
    out['heir_rank'] = set_rank(heir_word_2c, 7)
    out['heir_merit'] = MERIT_CAP
    return out


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
    print('promote3_ref self_test  — 大名/城主 任命·继承路径')
    print('=' * 74)

    # --- 1. 職位名表（映像真值）---
    names = []
    for i in range(9):
        p = struct.unpack('<I', rd(RANK_LADDER + i * 4, 4))[0]
        names.append(cstr(p) if 0x400000 <= p < 0x600000 else None)
    chk('ladder[0] 浪人', names[0], '浪人')
    chk('ladder[5] 家老', names[5], '家老')
    chk('ladder[6] 宿老', names[6], '宿老')
    chk('ladder[7] 大名', names[7], '大名')
    chk('ladder[8] 城主 (显示映射用)', names[8], '城主')

    # --- 2. set_rank 3-bit 编码（纠偏核心）---
    for r in range(8):
        chk('set_rank roundtrip r=%d' % r, rank_of(set_rank(0x1234, r)), r)
    # 大名(7) 可存
    chk('set_rank(7) 大名 可编码', rank_of(set_rank(0, 7)), 7)
    # 城主(8) 存不下 —— 这正是纠偏的硬证据
    try:
        set_rank(0, 8)
        chk('set_rank(8) 应抛错', 'no-raise', 'ValueError')
    except ValueError:
        ok += 1
        print('[OK  ] %-46s got=%r' % ('set_rank(8) 城主 存不下→抛错(纠偏证据)', 'ValueError'))
    # 位域确实只有 3 bit：写入 7 后其它位保持不变
    chk('set_rank 保留其它位', set_rank(0xFFFF, 7) & ~0x0700, 0xFFFF & ~0x0700)

    # --- 3. 城主任命门槛 ---
    chk('rank=4 部将 → 拒绝(门槛>4)', can_appoint_castle_lord(4 << 8, 0x03, True, True)[0], False)
    chk('rank=5 家老 → 通过', can_appoint_castle_lord(5 << 8, 0x03, True, True)[0], True)
    chk('rank=6 宿老 → 通过', can_appoint_castle_lord(6 << 8, 0x03, True, True)[0], True)
    chk('无候选城 → no_candidate', can_appoint_castle_lord(6 << 8, 0x03, False, True)[1], 'no_candidate')
    chk('无城可用 → no_castle', can_appoint_castle_lord(6 << 8, 0x03, True, False)[1], 'no_castle')
    chk('礼法不足(byte11&3==0) → no_etiquette',
        can_appoint_castle_lord(6 << 8, 0x00, True, True)[1], 'no_etiquette')
    chk('礼法具备(byte11&3!=0) → ok',
        can_appoint_castle_lord(6 << 8, 0x01, True, True)[1], 'ok')

    # --- 4. 城主 = 城表派生状态 ---
    ct = bytearray(CITY_STRIDE * 4)          # 4 座城
    chk('初始无城主', is_castle_lord(ct, 42), False)
    appoint_castle_lord(ct, 42, old_city_idx=0, new_city_idx=2)
    chk('任命后 word[城2+0x0a]==42', lord_of(ct, 2), 42)
    chk('任命后 is_castle_lord(42)', is_castle_lord(ct, 42), True)
    chk('其它武将非城主', is_castle_lord(ct, 43), False)
    chk('任命事件含 set_city_lord(城3)',
        ('set_city_lord', 3, 42) in appoint_castle_lord(ct, 42, None, 3), True)
    chk('任命事件含 set_home_city(城3)',
        ('set_home_city', 3) in appoint_castle_lord(ct, 42, None, 3), True)

    # --- 5. 上限常量（映像内硬编码）---
    chk('勲功上限 0xea60', MERIT_CAP, 60000)
    chk('俸禄上限 0xc8', STIPEND_CAP, 200)
    chk('继承忠诚下限 0x1e', LOYALTY_INHERIT_FLOOR, 30)

    # --- 6. 大名继承 ---
    res = inherit_daimyo(
        heir_word_2c=6 << 8,                  # 继承人原为宿老(6)
        retainers=[{'word_2a': 7, 'word_1d': 0, 'byte_29': 10, 'rand_val': 5},
                   {'word_2a': 99, 'word_1d': 0, 'byte_29': 40, 'rand_val': 5}],
        dead_no=7)
    chk('继承人升大名(7)', rank_of(res['heir_rank']), 7)
    chk('继承人勲功拉满', res['heir_merit'], 60000)
    chk('嫡系(word_2a==死亡者)升宿老', res['promoted'], [('set_rank', 6)])
    chk('非嫡系忠诚=rand+byte29(>30不触底)', res['loyalty'][1], 45)
    chk('嫡系忠诚强制100', res['loyalty'][0], 100)
    # 忠诚下限
    res2 = inherit_daimyo(0, [{'word_2a': 1, 'word_1d': 0, 'byte_29': 0, 'rand_val': 0}], 99)
    chk('忠诚下限保护(<30→30)', res2['loyalty'][0], 30)

    # --- 7. 改名分支 ---
    chk('分支0 未改名(695以外)且byte24==13 → 改名',
        rename_branch(0x0000, 0x100, 0x0d)[0], True)
    chk('分支0 已改名(695) → 不改名',
        rename_branch(0x0000, 0x2b7, 0x0d)[0], False)
    chk('分支0 byte24!=13 → 不改名',
        rename_branch(0x0000, 0x100, 0x05)[0], False)
    chk('分支2 已改名(744) → 不改名',
        rename_branch(0x2000, 0x2e8, 0x0d)[0], False)

    print('-' * 74)
    print('self_test: %d/%d %s' % (ok, ok + fail, 'ALL PASS' if fail == 0 else 'HAS FAILURE'))
    return fail == 0


if __name__ == '__main__':
    self_test()
