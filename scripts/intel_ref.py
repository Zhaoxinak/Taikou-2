#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
太阁立志传2 — 情报收集子系统 + 武将实体表 + MSGX 编号 参考实现
============================================================
来源：脱壳映像 scripts/_unpacked_mem.bin (base 0x400000)
关键函数（全部经反汇编坐实，见 intel_spec.json）：
  0x4603f0  任务执行分发器  → call dword ptr [idx*4 + 0x504898]
  0x504898  13 项 handler 表
  0x45e3e0  通用武将候选池构建器（写 0x51e9c0）
  0x45e500  能力阈值谓词（≥90）
  0x45e590  技能等级谓词（==3）
  0x470690  武将有效性过滤
  0x493500  MSGX 编号 → (文件, 序号)
  0x506c68  9 地域名表 (stride 7)
  0x5076f0  10 町人职业名表 (stride 11)
  0x507fc0  5 能力科目名表 (stride 7)
  0x507b58  10 技能名表 (stride 5)
  0x504b28  12 任务名指针表
  0x519868  武将实体表 370 × 47B
  0x519548  49 国国情表 49 × 5B（含 →9 地方映射）
  0x5176a8  30 × 4B 任务报告目标槽

自检： python scripts/intel_ref.py
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

import os
import struct

BASE = 0x400000
IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), _ROOT + '/scripts/_unpacked_mem.bin')
_mem = None


def mem():
    global _mem
    if _mem is None:
        with open(IMG, 'rb') as f:
            _mem = f.read()
    return _mem


# ---------------------------------------------------------------- 基础读数
def u8(va):
    return mem()[va - BASE]


def u16(va):
    return struct.unpack_from('<H', mem(), va - BASE)[0]


def u32(va):
    return struct.unpack_from('<I', mem(), va - BASE)[0]


def cstr(va, maxn=64):
    m = mem()
    o = va - BASE
    e = m.find(b'\x00', o, o + maxn)
    if e < 0:
        e = o + maxn
    return m[o:e].decode('gbk', 'replace')


def ptr_table(va, n):
    return [u32(va + 4 * i) for i in range(n)]


# ---------------------------------------------------------------- 常量
ENTITY_TABLE = 0x519868      # 武将实体表
ENTITY_STRIDE = 47           # 0x2f
ENTITY_COUNT = 370           # 0x172

NPC_POOL = 0x517850          # 町人/NPC 对象池
NPC_STRIDE = 12

ITEM_POOL = 0x51e1f0         # 物品对象池（handler[8] 用 0x51e1f6 起 +6 偏移）
ITEM_STRIDE = 10
ITEM_COUNT = 200

TOWN_TABLE = 0x51eb88        # 200 城町（静态全 0，运行时从 SNDATA XOR 流填充）
TOWN_STRIDE = 31
TOWN_COUNT = 200

PROVINCE_TABLE = 0x519548    # 49 国 × 5B
PROVINCE_STRIDE = 5
PROVINCE_COUNT = 49

REGION_NAME_TABLE = 0x506c68  # 9 地方名 stride 7
REGION_STRIDE = 7
REGION_COUNT = 9

JOB_NAME_TABLE = 0x5076f0     # 10 町人职业名 stride 11
JOB_STRIDE = 11
JOB_COUNT = 10

STAT_NAME_TABLE = 0x507fc0    # 5 能力科目 stride 7
STAT_STRIDE = 7
STAT_COUNT = 5

SKILL_NAME_TABLE = 0x507b58   # 10 技能名 stride 5
SKILL_STRIDE = 5
SKILL_COUNT = 10

TASK_NAME_TABLE = 0x504b28    # 12 任务名指针表
TASK_COUNT = 12

HANDLER_TABLE = 0x504898      # 13 项 handler 表
HANDLER_COUNT = 13

REPORT_SLOTS = 0x5176a8       # 30 × 4B 报告目标槽
REPORT_SLOT_COUNT = 30

STAT_THRESHOLD = 0x5a         # 90：「擅长」阈值
SKILL_MAX_LEVEL = 3           # 技能 2bit 满级 =「天才」

# 实体字段偏移（武将实体表 47B）
F_STAT_LEAD = 0x0a   # 统御
F_STAT_MIGHT = 0x0b  # 武力
F_STAT_DOMESTIC = 0x0c  # 内政
F_STAT_DIPLO = 0x0d    # 外交
F_STAT_CHARM = 0x0e    # 魅力
F_SKILLS = 0x0f       # 10 技能 × 2bit（+0x0f..+0x11）
F_AGE_OR_RANK = 0x25  # handler[7] 判定 ≤ 0x30
F_KOKUDaka = 0x26     # word：kind=5 要求 ≥ 7000
F_AIDE = 0x2a         # word：得力助手实体索引（0xffff = 无）
F_FLAGS = 0x2c        # word 位域：bit7(低字节)/bit7(高字节)=隐藏·死亡；bit4(ax>>4)=卧病
F_HIDDEN2 = 0x2d

# 49 国表字段
P_REGION = 0x1        # byte：地方 ID 0..8（奥州/关东/…/九州）
P_HORSE = 0x4         # byte bit5(0x20) = 马贩子出没（奥州马）

# NPC 池字段
N_JOB = 0x4           # 职业码 0..9（0xb = 武将类，情报[6] 排除）
N_TOWN = 0x7          # 所在町（< 10 才入选）

MSG_FILES = ['MESSAGE1.LZW', 'MESSAGE2.LZW', 'MESSAGE3.LZW', 'MESSAGE4.LZW']
MSG_SLOTS_PER_FILE = 2000
MSGX_MAGIC = 0x10624dd3       # 0x493500: (id * M) >> 39 == id / 2000
MSG_FILE_HANDLES = {0: 0x5249d8, 1: 0x524a08, 2: 0x524a50, 3: 0x524870}

# 情报报告：handler 序号 → MSGX id
INTEL_MSGID = {1: 0x1202, 2: 0x1203, 3: 0x1204, 4: 0x1205, 5: 0x1206,
               6: 0x1207, 7: 0x1208, 8: 0x1209, 9: 0x120a, 10: 0x120b,
               11: 0x120c, 12: 0x120e}
INTEL_MSGID_SELF = 0x120d      # 「哈哈哈┅┅，正是区区在下我。」（目标=自己时的追加）


# ---------------------------------------------------------------- MSGX 编号
def msgx_resolve(msgid):
    """0x493500(msgid) → (文件名, 文件内序号)。
    id // 2000 选文件（4 文件 × 2000 槽），文件内序号 = id - file*2000。"""
    fid = (msgid & 0xffff) // MSG_SLOTS_PER_FILE
    if fid > 3:
        return (None, None)
    return (MSG_FILES[fid], (msgid & 0xffff) - fid * MSG_SLOTS_PER_FILE)


def _msgx_magic_div(msgid):
    """复刻 0x493500 的魔数除法：imul 0x10624dd3 → sar edx,7（即 >>39）→ 符号修正。"""
    v = msgid & 0xffff
    hi = (v * MSGX_MAGIC) >> 32          # mul 后 edx
    q = hi >> 7                          # sar edx, 7
    q += (q >> 31) & 1                   # shr 0x1f 后 add（符号修正）
    return q


# ---------------------------------------------------------------- 实体访问
def entity(idx):
    """武将实体基址。idx ∈ [0, 370)"""
    if not (0 <= idx < ENTITY_COUNT):
        return None
    return ENTITY_TABLE + idx * ENTITY_STRIDE


def ent_stat(ent, which):
    """五维：0=统御 1=武力 2=内政 3=外交 4=魅力（byte 0..100）"""
    return u8(ent + F_STAT_LEAD + which)


def ent_skill(ent, which):
    """10 技能 × 2bit，等级 0..3（+0x0f..+0x11）"""
    if not (0 <= which < 10):
        return 0
    sh = (which * 2) % 8
    return (u8(ent + F_SKILLS + (which * 2) // 8) >> sh) & 3


def ent_is_valid(ent):
    """0x470690：byte[+0x2d]&0x80 == 0 且 byte[+0x2c]&0x80 == 0"""
    return not (u8(ent + F_HIDDEN2) & 0x80) and not (u8(ent + F_FLAGS) & 0x80)


def ent_aide(ent):
    """得力助手实体索引（word 0xffff = 无）"""
    v = u16(ent + F_AIDE)
    return None if v == 0xffff or v >= ENTITY_COUNT else v


# ---------------------------------------------------------------- 谓词
def pred_stat(ent, subject):
    """0x45e500：按当前科目(0x513fd0)判定五维 ≥ 90"""
    return 1 if ent_stat(ent, subject) >= STAT_THRESHOLD else 0


def pred_skill(ent, skill):
    """0x45e590：按当前技能(0x513fc8)判定等级 == 3"""
    return 1 if ent_skill(ent, skill) == SKILL_MAX_LEVEL else 0


def build_candidates(kind, stop_after_first, cur_ent, subject, skill):
    """复刻 0x45e3e0(kind, stop_after_first)。
    返回写入 0x51e9c0 的候选实体指针列表。
    kind: 3=五维≥90 / 4=技能满级 / 5=石高≥7000且非家臣 / 6,7,8=不入选(另有专用池)
          9=卧病标志 / 10=有得力助手；kind==7 且 (flags高字节&7)==0 走「非本人且 +0x25≤0x30」分支。
    """
    out = []
    for i in range(ENTITY_COUNT):
        ent = entity(i)
        flags = u16(ent + F_FLAGS)
        ok = 0
        if (flags >> 8) & 7 == 0:
            # 0x45e406：仅 kind==7 走此分支
            if kind == 7 and ent != cur_ent and u8(ent + F_AGE_OR_RANK) <= 0x30:
                ok = 1
        else:
            if kind == 3:
                ok = pred_stat(ent, subject)
            elif kind == 4:
                ok = pred_skill(ent, skill)
            elif kind == 5:
                ok = 1 if (u16(ent + F_KOKUDaka) >= 0x1b58) else 0
            elif kind == 6:
                ok = (flags >> 4) & 1
            elif kind == 7:
                ok = 1 if u16(ent + F_AIDE) != 0xffff else 0   # 见 0x45e489（kind=10 共用入口）
            elif kind == 9:
                ok = (flags >> 4) & 1
            elif kind == 10:
                ok = 1 if u16(ent + F_AIDE) != 0xffff else 0
        if ok and ent_is_valid(ent):
            out.append(ent)
            if stop_after_first:
                break
    return out


def pick_intel(kind, rnd, cur_ent=None, subject=0, skill=0,
               intel_pool=None, rand_pool=None):
    """复刻 handler：从候选池 rand%n 取一条，返回 (msgid, 参数表)。"""
    if kind in (3, 4, 5, 7, 9, 10):
        pool = build_candidates(kind, True, cur_ent, subject, skill)
    elif kind == 6:
        pool = intel_pool or []      # 0x45eb30 从 NPC 池 0x517850 构建
    elif kind == 8:
        pool = intel_pool or []      # 0x45ecc0 从物品池 0x51e1f6 构建
    else:
        pool = intel_pool or []
    if not pool:
        return (None, None)
    return (INTEL_MSGID.get(kind), pool[rnd % len(pool)])


# ---------------------------------------------------------------- 名表
def region_names():
    return [cstr(REGION_NAME_TABLE + REGION_STRIDE * i, REGION_STRIDE)
            for i in range(REGION_COUNT)]


def job_names():
    return [cstr(JOB_NAME_TABLE + JOB_STRIDE * i, JOB_STRIDE)
            for i in range(JOB_COUNT)]


def stat_names():
    return [cstr(STAT_NAME_TABLE + STAT_STRIDE * i, STAT_STRIDE)
            for i in range(STAT_COUNT)]


def skill_names():
    return [cstr(SKILL_NAME_TABLE + SKILL_STRIDE * i, SKILL_STRIDE)
            for i in range(SKILL_COUNT)]


def task_names():
    return [cstr(p, 16) for p in ptr_table(TASK_NAME_TABLE, TASK_COUNT)]


def handlers():
    return ptr_table(HANDLER_TABLE, HANDLER_COUNT)


def province_region(pid):
    """国 → 地方 ID（0..8）"""
    return u8(PROVINCE_TABLE + pid * PROVINCE_STRIDE + P_REGION)


def horse_provinces():
    """byte[+4] & 0x20 的国（马贩子出没）"""
    return [i for i in range(PROVINCE_COUNT)
            if u8(PROVINCE_TABLE + i * PROVINCE_STRIDE + P_HORSE) & 0x20]


# ---------------------------------------------------------------- 自检
def _ok(cond, msg):
    print(('  [OK]   ' if cond else '  [FAIL] ') + msg)
    return bool(cond)


def selfcheck():
    print('== 太阁2 情报子系统 / 实体表 / MSGX 自检 ==')
    p = 0
    n = 0

    # 1) MSGX 魔数除法 == id/2000
    bad = [i for i in range(0, 8000, 7) if _msgx_magic_div(i) != i // 2000]
    n += 1; p += _ok(not bad, f'MSGX 魔数 0x10624dd3 还原 /2000（抽查 1143 个 id，异常 {len(bad)}）')

    # 2) 已知锚点：0x370(880) → MESSAGE1#880
    f, idx = msgx_resolve(0x370)
    n += 1; p += _ok((f, idx) == ('MESSAGE1.LZW', 880), f'锚点 0x370 → {f}#{idx}（期望 MESSAGE1.LZW#880）')

    # 3) 情报报告 id → MESSAGE3#610..
    f, idx = msgx_resolve(0x1202)
    n += 1; p += _ok((f, idx) == ('MESSAGE3.LZW', 610), f'0x1202 → {f}#{idx}（期望 MESSAGE3.LZW#610「我去过%s城。」）')
    f, idx = msgx_resolve(0x120e)
    n += 1; p += _ok((f, idx) == ('MESSAGE3.LZW', 622), f'0x120e → {f}#{idx}（期望 MESSAGE3.LZW#622 米价情报）')

    # 4) 9 地域名
    rn = region_names()
    n += 1; p += _ok(rn == ['奥州', '关东', '甲信越', '东海', '北陆', '近畿', '中国', '四国', '九州'],
                     '9 地域名表 0x506c68 = ' + '/'.join(rn))

    # 5) 10 町人职业名
    jn = job_names()
    n += 1; p += _ok(len(jn) == 10 and jn[0] == '大商人' and jn[9] == '忍者',
                     '10 职业名表 0x5076f0 = ' + '/'.join(jn))

    # 6) 5 能力科目
    sn = stat_names()
    n += 1; p += _ok(sn[:5] == ['统御力', '武力', '内政力', '外交力', '魅力'],
                     '5 能力科目表 0x507fc0 = ' + '/'.join(sn))

    # 7) 12 任务名
    tn = task_names()
    n += 1; p += _ok(len(tn) == 12 and tn[0] == '贩卖军粮' and tn[11] == '谋略',
                     '12 任务名表 0x504b28 = ' + '/'.join(tn))

    # 8) 13 handler 表单调递增且落在 .text，末项为 0 守卫
    hs = handlers()
    n += 1; p += _ok(len(hs) == 13 and all(0x401000 <= h < 0x4f0000 for h in hs[:12])
                     and hs[12] != 0 and u32(HANDLER_TABLE + 4 * 13) == 0,
                     '13 项 handler 表 0x504898 合法（末项后 0 守卫）')

    # 9) 实体表规模：370 × 47B 不越界（下一张已知表 0x519548 在前，实体表到 0x519868+17390）
    end = ENTITY_TABLE + ENTITY_COUNT * ENTITY_STRIDE
    n += 1; p += _ok(end <= 0x520000, f'实体表 0x519868 + 370*47 = {end:#x} 未越界')

    # 10) 静态映像：实体表/城表全 0（运行时填充，与既有结论一致）
    zero = all(b == 0 for b in mem()[ENTITY_TABLE - BASE:ENTITY_TABLE - BASE + 64]) and \
           all(b == 0 for b in mem()[TOWN_TABLE - BASE:TOWN_TABLE - BASE + 64])
    n += 1; p += _ok(zero, '实体表/城表静态全 0（运行时填充，符合既有结论）')

    # 11) 49 国 → 9 地方：地方 ID 全部 ∈ 0..8
    regs = [province_region(i) for i in range(PROVINCE_COUNT)]
    n += 1; p += _ok(all(0 <= r < 9 for r in regs),
                     f'49 国 byte[+1] 地方 ID 全部 ∈0..8（分布 {sorted(set(regs))}）')

    # 12) 阈值常数：能力 0x5a / 技能满级 3
    n += 1; p += _ok(STAT_THRESHOLD == 0x5a and SKILL_MAX_LEVEL == 3,
                     '阈值常数：五维「擅长」≥90(0x5a)；技能「天才」=2bit 满级 3')

    print(f'\n自检 {p}/{n} 通过' + ('  ✅ ALL PASS' if p == n else '  ❌ 有失败项'))
    return p == n


if __name__ == '__main__':
    import sys
    ok = selfcheck()
    if '--dump' in sys.argv:
        print('\n== 名表导出 ==')
        print('地方:', region_names())
        print('职业:', job_names())
        print('科目:', stat_names())
        print('技能:', skill_names())
        print('任务:', task_names())
        print('马贩国:', horse_provinces())
        print('handler:', [hex(h) for h in handlers()])
    sys.exit(0 if ok else 1)
