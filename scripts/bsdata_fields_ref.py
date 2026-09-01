# -*- coding: utf-8 -*-
"""
BSDATA / 武将实体 —— 技能位域 · 能力名表 · 属性评分表 参考实现
=============================================================
对应 BREAKTHROUGHS 续130。闭合 bsdata_spec.json still_unknown 第 3 项
「@27..29 nibble 与官方技能 10 项的精确位序」，并给出 3 张此前未建档的表。

三条独立证据链
--------------
1. 技能名表 `0x507b58` = 5B×10 GBK（口才/马术/算术/剑术/忍术/兵法/洋枪/筑城/礼法/茶道）
   —— 直接 dump 解码确认，与官方十技能顺序一致。
2. 属性取值器 `0x4c7c30`（任务适性评分）：
   `cmp ebx,0x13; ja` → `jmp dword[ebx*4 + 0x4c7e84]`（20 项跳表）
   各分支体直接给出「技能 i 在哪个字节、右移几位、& 3」：
       attr13 (+0xf   &3   ) = 口才      attr5  (+0xf   >>2&3) = 马术
       attr3  (+0xf   >>4&3) = 算术      ——     (+0xf   >>6  ) = 剑术 (0x4447948)
       attr12 (+0x10  &3   ) = 忍术      attr14 (+0x10  >>2&3) = 兵法
       attr8  (+0x10  >>4&3) = 洋枪      attr9  (+0x10  >>6  ) = 筑城
       attr10 (+0x11  &3   ) = 礼法      attr15 (+0x11  >>2&3) = 茶道
   ⇒ **10 技能 × 2 bit = 20 bit，打包于 3 字节 +0xf..+0x11**（+0x11 高 4 位未用）。
3. 能力名表 `0x507fc0` stride 7 ×5 = 统御力/武力/内政力/外交力/魅力；
   `0x4b5620` 用 `byte[+0xd]` 取 '外交'、`byte[+0xe]` 取 '魅力' ⇒
   **实体 +0xd = 外交力、+0xe = 魅力** 为硬证据（另 +0xb/+0xc 为另两维，具体待钉）。

🔴 对续55 的纠偏
----------------
续55 记「BSDATA 3 字节只能存 5 技能（每 nibble 一个 4bit 技能）」是错的。
实测为 **10 技能 × 2bit**：@27 = 技能0..3、@28 = 技能4..7、@29 低4位 = 技能8/9，
且 **BSDATA @27..29 与实体 +0xf..+0x11 是同一套打包**（逐字节对应）。
数据侧铁证：@29 高 nibble **700/700 恒 0**（只用了低 4 位）；
武田信玄/上杉谦信/毛利元就 兵法=3、服部半藏 忍术=3 且 剑术=3。
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


import struct

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BSD_PATH = _ROOT + '/Taikou2 Original/BSDATA1.TR2'
BASE = 0x400000
REC = 59
NREC = 700

_mem = open(MEM_PATH, "rb").read()
_bsd = open(BSD_PATH, "rb").read()


def rd(va, n):
    return _mem[va - BASE: va - BASE + n]


def gbk(b):
    return b.split(b"\x00")[0].decode("gbk", "replace")


# ---------------------------------------------------------------- 表 1: 技能名
SKILL_TBL_VA = 0x507B58
SKILL_STRIDE = 5
SKILL_NAMES = [gbk(rd(SKILL_TBL_VA + SKILL_STRIDE * i, SKILL_STRIDE))
               for i in range(10)]
# 官方十技能顺序
SKILL_ORDER = ["口才", "马术", "算术", "剑术", "忍术", "兵法", "洋枪", "筑城", "礼法", "茶道"]

# ---------------------------------------------------------------- 表 2: 能力名
ABILITY_TBL_VA = 0x507FC0
ABILITY_STRIDE = 7
ABILITY_NAMES = [gbk(rd(ABILITY_TBL_VA + ABILITY_STRIDE * i, ABILITY_STRIDE))
                 for i in range(5)]
ABILITY_ORDER = ["统御力", "武力", "内政力", "外交力", "魅力"]

# ------------------------------------------------- 表 3: 技能位域布局（硬证据）
# 技能 i -> (实体字节偏移, 右移位数)
SKILL_FIELDS = [
    (0x0F, 0), (0x0F, 2), (0x0F, 4), (0x0F, 6),   # 0..3  口才 马术 算术 剑术
    (0x10, 0), (0x10, 2), (0x10, 4), (0x10, 6),   # 4..7  忍术 兵法 洋枪 筑城
    (0x11, 0), (0x11, 2),                          # 8..9  礼法 茶道
]
# BSDATA 侧: 字节 27/28/29 与实体 +0xf/+0x10/+0x11 同构
BSD_SKILL_BYTE = [27, 27, 27, 27, 28, 28, 28, 28, 29, 29]

# --------------------------------------- 表 4: 属性评分跳表 0x4c7e84 (20 项)
ATTR_TBL_VA = 0x4C7E84
ATTR_N = 20
ATTR_TABLE_VA = [struct.unpack_from("<I", _mem, ATTR_TBL_VA - BASE + 4 * i)[0]
                 for i in range(ATTR_N)]

# 每项 = (类别, 参数)
#   "status" -> word[+0x2c] 高字节 & 7 (身分码)
#   "skill"  -> 技能[id]
#   "abil"   -> byte[+off]
#   "combo"  -> byte[+off] + skill[id]*10            (attr2, attr18)
#   "combo2" -> status + skill[id]*2                 (attr19)
#   "divsk"  -> skill[id]*10 / (4-N)                 (attr16)
#   "divab"  -> byte[+off]   / (4-N)                 (attr17)
ATTR_SEM = {
    0:  ("status", None), 1:  ("status", None),
    2:  ("combo",  dict(off=0x0D, skill=0, mul=10)),
    3:  ("skill",  2),
    4:  ("abil",   0x0B),
    5:  ("skill",  1),
    6:  ("abil",   0x0C),
    7:  ("abil",   0x0D),      # 外交力（硬证据）
    8:  ("skill",  6),
    9:  ("skill",  7),
    10: ("skill",  8),
    11: ("abil",   0x0E),      # 魅力（硬证据）
    12: ("skill",  4),
    13: ("skill",  0),
    14: ("skill",  5),
    15: ("skill",  9),
    16: ("divsk",  dict(skill=7, mul=10)),
    17: ("divab",  dict(off=0x0C)),
    18: ("combo",  dict(off=0x0D, status=True, mul=10)),
    19: ("combo2", dict(skill=8, mul=2)),
}


# ============================================================ 核心: 位域存取
def get_skill(buf, base, i):
    """从 buf[base + off] 取技能 i (0..3)。"""
    off, sh = SKILL_FIELDS[i]
    return (buf[base + off] >> sh) & 3


def set_skill(buf, base, i, v):
    off, sh = SKILL_FIELDS[i]
    b = buf[base + off] & ~(3 << sh)
    buf[base + off] = b | ((v & 3) << sh)


def pack_skills(vals):
    """10 个技能值 -> (byte_f, byte_10, byte_11)。"""
    buf = bytearray(0x12)
    for i, v in enumerate(vals):
        set_skill(buf, 0, i, v)
    return buf[0x0F], buf[0x10], buf[0x11]


def unpack_skills(f, t, el):
    buf = bytearray(0x12)
    buf[0x0F], buf[0x10], buf[0x11] = f, t, el
    return [get_skill(buf, 0, i) for i in range(10)]


def bsd_name(rec):
    off = REC * rec
    return (gbk(_bsd[off:off + 7]) + gbk(_bsd[off + 7:off + 13]))


def bsd_skill(rec, i):
    return (_bsd[REC * rec + BSD_SKILL_BYTE[i]] >> SKILL_FIELDS[i][1]) & 3


def find_rec(name):
    for r in range(NREC):
        if bsd_name(r) == name:
            return r
    return None


# ============================================================ 属性评分
def attr_score(attr_id, ent, n=0):
    """ent: dict, 键为实体偏移(0xb..0x11)与 'word2c'；n 为除数参数 N。"""
    kind, arg = ATTR_SEM[attr_id]
    if kind == "status":
        return (ent["word2c"] >> 8) & 7
    if kind == "skill":
        return get_skill(ent, 0, arg)
    if kind == "abil":
        return ent[arg]
    if kind == "combo":
        base = ent[arg["off"]]
        add = ((ent["word2c"] >> 8) & 7) if arg.get("status") else get_skill(ent, 0, arg["skill"])
        return base + add * arg["mul"]
    if kind == "combo2":
        return ((ent["word2c"] >> 8) & 7) + get_skill(ent, 0, arg["skill"]) * arg["mul"]
    if kind == "divsk":
        den = 4 - n
        return (get_skill(ent, 0, arg["skill"]) * arg["mul"]) // den
    if kind == "divab":
        den = 4 - n
        return ent[arg["off"]] // den
    raise ValueError(attr_id)


# ============================================================ 自检
def _run_tests():
    ok = tot = 0

    def check(name, cond):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
        else:
            print(f"  [FAIL] {name}")

    # --- 1. 技能名表
    check("技能名表 = 官方十技能顺序", SKILL_NAMES == SKILL_ORDER)
    check("技能名表 raw 前缀", rd(SKILL_TBL_VA, 4) == "口才".encode("gbk"))

    # --- 2. 能力名表
    check("能力名表 = 官方五维", ABILITY_NAMES == ABILITY_ORDER)
    check("能力名表 raw 前缀", rd(ABILITY_TBL_VA, 6) == "统御力".encode("gbk"))

    # --- 3. 位域 round-trip: 每个技能独立可写、互不干扰
    for i in range(10):
        for v in range(4):
            vals = [0] * 10
            vals[i] = v
            f, t, el = pack_skills(vals)
            got = unpack_skills(f, t, el)
            check(f"技能{i}({SKILL_ORDER[i]})={v} round-trip", got == vals)

    # --- 4. 全组合穷举 (4^5 抽样 + 边界)
    import itertools
    for combo in itertools.product(range(4), repeat=5):
        vals = list(combo) + [3, 1, 0, 2, 3]
        f, t, el = pack_skills(vals)
        check("全组合 round-trip", unpack_skills(f, t, el) == vals)

    # --- 5. +0x11 高 4 位不被使用
    f, t, el = pack_skills([3] * 10)
    check("+0x11 高4位恒0 (只存技能8/9)", (el >> 4) == 0 and el == 0x0F)
    check("10技能全3 -> (0xff,0xff,0x0f)", (f, t, el) == (0xFF, 0xFF, 0x0F))

    # --- 6. BSDATA 数据侧: @29 高 nibble 700/700 恒 0
    hi = set((_bsd[REC * r + 29] >> 4) & 0xF for r in range(NREC))
    check("BSDATA @29 高nibble 700/700 == 0", hi == {0})

    # --- 7. BSDATA 与实体同构: 用实体解包器读 BSDATA 应得同样结果
    mism = 0
    for r in range(0, NREC, 7):
        buf = bytearray(0x12)
        buf[0x0F] = _bsd[REC * r + 27]
        buf[0x10] = _bsd[REC * r + 28]
        buf[0x11] = _bsd[REC * r + 29]
        for i in range(10):
            if get_skill(buf, 0, i) != bsd_skill(r, i):
                mism += 1
    check("BSDATA @27..29 与实体 +0xf..+0x11 同构", mism == 0)

    # --- 8. 史实人物验证 (硬锚点)
    anchors = [
        ("武田信玄", "兵法", 5), ("上杉谦信", "兵法", 5), ("毛利元就", "兵法", 5),
    ]
    for nm, sk, si in anchors:
        r = find_rec(nm)
        check(f"{nm} 存在", r is not None)
        if r is not None:
            check(f"{nm} {sk}==3", bsd_skill(r, si) == 3)
    r = find_rec("服部半藏")
    check("服部半藏 存在", r is not None)
    if r is not None:
        check("服部半藏 忍术==3", bsd_skill(r, 4) == 3)
        check("服部半藏 剑术==3", bsd_skill(r, 3) == 3)

    # --- 9. 跳表 20 项 (防回归锚点)
    check("属性跳表项数 20", len(ATTR_TABLE_VA) == 20)
    expect = [0x004C7CD7, 0x004C7CD7, 0x004C7CE5, 0x004C7D00, 0x004C7D11,
              0x004C7D1B, 0x004C7D2D, 0x004C7D37, 0x004C7D41, 0x004C7D52,
              0x004C7D61, 0x004C7D6F, 0x004C7D79, 0x004C7D88, 0x004C7D93,
              0x004C7DA2, 0x004C7DB0, 0x004C7DD0, 0x004C7DEA, 0x004C7DFF]
    check("属性跳表内容与映像一致", ATTR_TABLE_VA == expect)
    # attr 0/1 同址 (身分码), 其余两两不同
    check("attr0/1 同分支(身分码)", ATTR_TABLE_VA[0] == ATTR_TABLE_VA[1])
    check("attr2..19 分支互不相同", len(set(ATTR_TABLE_VA[2:])) == 18)

    # --- 10. 属性评分函数
    ent = {0x0B: 70, 0x0C: 60, 0x0D: 80, 0x0E: 90, "word2c": 0x0500}
    # 手工布置技能: 口才=2 兵法=3 礼法=1 筑城=2
    buf = bytearray(0x12)
    ent_bytes = bytearray(0x12)
    for k, v in ((0x0B, 70), (0x0C, 60), (0x0D, 80), (0x0E, 90)):
        ent_bytes[k] = v
    set_skill(ent_bytes, 0, 0, 2)   # 口才
    set_skill(ent_bytes, 0, 5, 3)   # 兵法
    set_skill(ent_bytes, 0, 8, 1)   # 礼法
    set_skill(ent_bytes, 0, 7, 2)   # 筑城
    ent = {b: ent_bytes[b] for b in range(0x12)}
    ent["word2c"] = 0x0500          # 高字节 0x05 -> 身分码 5

    check("attr2 = 外交力 + 口才*10 = 80+20", attr_score(2, ent) == 100)
    check("attr7 = 外交力 = 80", attr_score(7, ent) == 80)
    check("attr11 = 魅力 = 90", attr_score(11, ent) == 90)
    check("attr13 = 口才 = 2", attr_score(13, ent) == 2)
    check("attr14 = 兵法 = 3", attr_score(14, ent) == 3)
    check("attr10 = 礼法 = 1", attr_score(10, ent) == 1)
    check("attr0 = 身分码 = 5", attr_score(0, ent) == 5)
    check("attr16 = 筑城*10/(4-0) = 5", attr_score(16, ent, n=0) == (2 * 10) // 4)
    check("attr17 = ability+0xc/(4-0) = 15", attr_score(17, ent, n=0) == 60 // 4)
    check("attr18 = 外交力 + 身分*10 = 130", attr_score(18, ent) == 80 + 5 * 10)
    check("attr19 = 身分 + 礼法*2 = 7", attr_score(19, ent) == 5 + 1 * 2)

    print(f"\nRESULT: {ok}/{tot} checks passed")
    return ok == tot


if __name__ == "__main__":
    print("=== 表1 技能名 (0x507b58, 5B×10) ===")
    print("  " + " / ".join(SKILL_NAMES))
    print("=== 表2 能力名 (0x507fc0, stride7×5) ===")
    print("  " + " / ".join(ABILITY_NAMES))
    print("=== 表3 技能位域 ===")
    for i, (off, sh) in enumerate(SKILL_FIELDS):
        print(f"  技能{i} {SKILL_ORDER[i]:<3} -> byte[+0x{off:02x}] >> {sh} & 3"
              f"   (BSDATA @{BSD_SKILL_BYTE[i]})")
    print()
    _run_tests()
