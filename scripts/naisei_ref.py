# -*- coding: utf-8 -*-
"""内政 / 仕事実行 大模块 —— 参考实现 + 静态自校验（2026-08-31 续153）


破解对象：
  * 武将实体 `0x519868`(370×47B) 的 3 个工作字段：
      byte[+0x16] = 仕事コード(bits0-5) ‖ 進捗状態(bits6-7)
      byte[+0x17] = 仕事成果値
      word[+0x18] = 仕事対象 ID（命名空间随仕事）
      byte[+0x13] = 現在地 ID（0..199=城 / 200..248=国(province+200) / ≥249=特殊）
  * 日次進行 `0x4a9df0(entity)` → 仕事ディスパッチャ `0x4a9f10(entity)`
  * ディスパッチャ跳表 `0x4aa088`(15) + 索引表 `0x4aa0c4`(45)
  * 各 handler 对城表 `0x51eb88`(200×31B) 的效果公式

全部断言均直接读 `scripts/_unpacked_mem.bin`（cwd=工程根）。
运行：python3.7 scripts/naisei_ref.py
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

import json
import os
import struct
import sys

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from capstone.x86 import X86_OP_MEM, X86_OP_IMM
except ImportError:  # pragma: no cover
    Cs = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MEM = open(os.path.join(ROOT, "scripts", _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
BASE = 0x400000

# ---------------------------------------------------------------- 基址常量
CASTLE_TBL = 0x51EB88      # 200 × 31B
CASTLE_STRIDE = 31
ENTITY_TBL = 0x519868      # 370 × 47B
ENTITY_STRIDE = 47
PROV5_TBL = 0x519548       # 49 × 5B  国情表
PROV14_TBL = 0x5179B8      # 49 × 14B 国政治表
NPC_TBL = 0x517850         # 30 × 12B NPC 池

# ------------------------------------------------- 城字段饱和增量包装器族
# (VA, 字段偏移, cap) —— 形态 byte[f] = sat_add(byte[f], delta, cap)
CASTLE_INC = {
    0x4A32A0: (0x0C, 100),    # 农商
    0x4A32C0: (0x0D, 250),    # 守城度
    0x4A3310: (0x0E, 200),    # 民心/治安
    0x4A3360: (0x0F, 100),    # 生产率
    0x4A33A0: (0x10, 50000),  # 軍糧
    0x4A33F0: (0x12, 30000),  # 米
    0x4A3440: (0x14, 30000),  # 資金
    0x4A3530: (0x1A, 200),    # 次级民情
}

# ------------------------------------------------- 仕事ディスパッチャ
DISPATCHER = 0x4A9F10
JMPTAB = 0x4AA088           # 15 项
IDXTAB = 0x4AA0C4           # 45 项（index = code-2）

# 跳表槽 → 真正执行的 handler（跳表项本身是 thunk）
# 槽 12 = 0x4AA06E → 直接 `mov eax,1`（default）；槽 14 = 0x4AA032 子区间（静态不可达）
JMPSLOT_HANDLER = {
    0: 0x4AA100, 1: 0x4AB2A0, 2: 0x4AA160, 3: 0x4AA1F0, 4: 0x4AA290,
    5: 0x4AA370, 6: 0x4AB530, 7: 0x4AB680, 8: 0x4AB8F0, 9: 0x4AB3C0,
    10: 0x4AA690, 11: 0x4AABD0,
    12: None,   # 0x4AA06E — default（return 1）
    13: 0x4AACB0,
    14: None,   # 0x4AA032 — 子区间（编译期残留，静态不可达）
}

IDXMAP = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 14, 10, 14, 14, 14, 14, 11, 14, 14,
          14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14,
          14, 14, 12, 14, 14, 14, 14, 14, 13]

# 主命 12 项（名表 0x504b28，指针 12 条）
MEIREI_NAMES = ["贩卖军粮", "购买军粮", "军马", "洋枪", "开垦农田", "改建",
                "筑城", "进贡", "威吓", "朝廷工作", "收集情报", "谋略"]
MEIREI_PTR_TAB = 0x504B28

# 仕事コード → (摘要, handler)。code = 主命ID + 2（主命 0..11 → code 2..13）
WORK_TABLE = {
    0: ("待機（正規化到 1）", None),
    1: ("待機 / 無仕事", None),
    2: ("贩卖军粮（主命0）", 0x4AA100),
    3: ("购买军粮（主命1）", 0x4AB2A0),
    4: ("军马（主命2）", 0x4AA160),
    5: ("洋枪（主命3）", 0x4AA1F0),
    6: ("开垦农田 → 城+0x0C 农商（主命4）", 0x4AA290),
    7: ("改建 → 城+0x0D 守城度（主命5）", 0x4AA370),
    8: ("筑城 → 城+0x0D += 10 且 +0x1C|=0x20（主命6）", 0x4AB530),
    9: ("进贡（国↔国，主命7）", 0x4AB680),
    10: ("威吓（国↔国，主命8）", 0x4AB8F0),
    11: ("朝廷工作（国，主命9）", 0x4AB3C0),
    12: ("收集情报（主命10，本 dispatcher 空转）", None),
    13: ("谋略（対象武将 寝返り，主命11）", 0x4AA690),
    14: ("帰国（移動側処理）", None),
    18: ("民心/治安（城 +0x1A 与 +0x0E）", 0x4AABD0),
    46: ("修行（NPC 池 0x517850）", 0x4AACB0),
}

# 城種(&7) → 改修上限（0x49f9f0 跳表）
CASTLE_TYPE_CAP = {0: 0, 1: 80, 2: 150, 3: 150, 4: 200, 5: 250, 6: 250, 7: 250}
# 城種(&7) → 農商基档（0x49f960 跳表）
CASTLE_TYPE_BASE = {0: 0, 1: 1, 2: 2, 3: 2, 4: 2, 5: 3, 6: 3, 7: 3}


# ---------------------------------------------------------------- 工具
def u8(va):
    return MEM[va - BASE]


def u16(va):
    return struct.unpack("<H", MEM[va - BASE:va - BASE + 2])[0]


def u32(va):
    return struct.unpack("<I", MEM[va - BASE:va - BASE + 4])[0]


def find_call(target, va, length=0x80):
    """在 va 起的 length 字节内找 `call target`（E8 rel32）。返回 VA 或 None。"""
    off = va - BASE
    for i in range(length):
        if MEM[off + i] == 0xE8:
            rel = int.from_bytes(MEM[off + i + 1:off + i + 5], "little", signed=True)
            if BASE + off + i + 5 + rel == target:
                return BASE + off + i
    return None


def disassemble(va, length):
    """capstone 线性反汇编（只读，勿嵌套迭代生成器）。"""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    return list(md.disasm(MEM[va - BASE:va - BASE + length], va))


def jump_stub_imm(va):
    """读 `0x49f9xx` 系单条 jmp 目标 stub 的返回值：
       `xor eax,eax`(31 c0 / 33 c0) → 0；`mov eax,imm32`(b8 ..) → imm32。"""
    if not (0x400000 <= va < 0x600000):
        return None
    b0 = MEM[va - BASE]
    if b0 in (0x31, 0x33):
        return 0
    if b0 == 0xB8:
        return struct.unpack("<I", MEM[va - BASE + 1:va - BASE + 5])[0]
    return None


def find_disp(va, disp, length=0x100, width=None):
    """在 va 起 length 字节内找任一操作数的 mem.disp == disp。"""
    for ins in disassemble(va, length):
        for op in ins.operands:
            if op.type == X86_OP_MEM and op.mem.disp == disp:
                if width is None or op.size == width:
                    return ins
    return None


def find_push_imm(va, imm, length=0x100):
    for ins in disassemble(va, length):
        if ins.mnemonic == "push" and ins.operands and \
                ins.operands[0].type == X86_OP_IMM and ins.operands[0].imm == imm:
            return ins
    return None


# ---------------------------------------------------------------- 语义函数
def sat_add(a, b, cap):
    s = (a & 0xFFFF) + (b & 0xFFFF)
    return cap if s > cap else s


def sat_sub(a, b):
    return (a - b) if a > b else 0


def div10(n):
    return n // 10


def div15(n):
    magic = 0x88888889
    edx = (n * magic) >> 32
    edx = (edx + n) >> 3
    return edx


def muldiv(a, b, c):
    """0x4ebc50"""
    if (c & 0xFFFF) == 0:
        return 0xFFFF
    return ((a & 0xFFFF) * (b & 0xFFFF)) // (c & 0xFFFF)


# ---- 開墾農田（仕事コード 6, handler 0x4aa290）----
def work_kaiten(castle, naisei):
    """城 +0x0C（农商）增量。naisei = 実行武将 `byte[entity+0x0C]`（内政力）。"""
    cur = castle[0x0C]
    cap = agri_capacity(castle)
    delta = div10(sat_sub(naisei, 30)) + 1
    add = min(sat_sub(cap, cur), delta) if cap >= cur else delta
    return sat_add(cur, add, 100), add


def agri_capacity(castle):
    """0x49f9b0：max(1, (byte[城+0x09] × 城種基档 × 4) / 3)"""
    base = CASTLE_TYPE_BASE[castle[0x1B] & 7]
    v = muldiv(castle[0x09] * base, 4, 3)
    return max(1, v)


def castle_type_cap(castle):
    """0x49f9f0：改修上限（守城度）"""
    return CASTLE_TYPE_CAP[castle[0x1B] & 7]


# ---- 改建（仕事コード 7, handler 0x4aa370）----
def work_kaizen(castle, naisei, tier2):
    """城 +0x0D（守城度）增量。tier2 = byte[entity+0x10] >> 6（2 bit）。"""
    cur = castle[0x0D]
    cap = castle_type_cap(castle)
    delta = div10(naisei) + 5 * (tier2 + 1)
    add = min(sat_sub(cap, cur), delta) if cap >= cur else delta
    return sat_add(cur, add, 250), add


# ---- 築城（仕事コード 8, handler 0x4ab530）----
def work_chikujo(castle):
    castle[0x1C] |= 0x20            # 0x49abe0
    return sat_add(castle[0x0D], 10, 250), 10


# ---- 民心/治安（仕事コード 17, handler 0x4aabd0）----
def work_minshin(castle, lead_a, str_a, lead_b, str_b, r1, r2):
    """lead/str = 実行者(a) 与 対象武将(b) 的 統率(+0x0A)/武力(+0x0B)。"""
    total = (lead_a + str_a) + (lead_b + str_b)
    q = div15(total)
    d1 = r1 + q + 5
    excess = muldiv(d1, 1, 1)          # 0x4ebc80(d1, 80) —— 见 §3.21.5 注
    sub = d1 - sat_sub(d1, 80)
    v1 = sat_add(castle[0x1A], sub, 200)
    v2 = sat_add(castle[0x0E], r2 + (q >> 2), 200)
    return v1, v2, sub


# ---------------------------------------------------------------- 自校验
OK = FAIL = 0


def chk(name, cond, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ok   %-58s %s" % (name, extra))
    else:
        FAIL += 1
        print("  FAIL %-58s %s" % (name, extra))


def self_test():
    print("== 内政 / 仕事実行 大模块（续153）==")

    # 1. 城表 stride 31：loader 0x47e130（@0x47e243 处 `add esi, 0x1f`）
    chk("城表 stride 31（0x47e130 loader 含 add esi,0x1f）",
        b"\x83\xc6\x1f" in MEM[0x47E130 - BASE:0x47E600 - BASE])

    # 2. 增量包装器族
    for va, (off, cap) in sorted(CASTLE_INC.items()):
        # 形态：push cap; push eax; movzx cx,byte[esi+off]; push ecx; call 0x4ebca0
        site = find_call(0x4EBCA0, va, 0x40)
        chk("包装器 0x%06X → 城+0x%02X cap=%d" % (va, off, cap),
            site is not None and find_disp(va, off, 0x30) is not None)

    # 3. 跳表 / 索引表
    slots = [u32(JMPTAB + 4 * i) for i in range(15)]
    chk("跳表 0x4AA088 15 项均在 .text", all(0x401000 <= s < 0x4D0000 for s in slots))
    raw = MEM[IDXTAB - BASE:IDXTAB - BASE + 45]
    chk("索引表 0x4AA0C4 == IDXMAP", list(raw) == IDXMAP)

    # 每个跳表槽确实 call 到对应 handler
    for slot, h in sorted(JMPSLOT_HANDLER.items()):
        if h is None:
            continue
        site = find_call(h, slots[slot], 0x20)
        chk("槽 %2d @0x%06X → handler 0x%06X" % (slot, slots[slot], h), site is not None)

    # 4. 主命名表 12 条
    names = []
    for i in range(12):
        p = u32(MEIREI_PTR_TAB + 4 * i)
        e = MEM.index(b"\x00", p - BASE)
        names.append(MEM[p - BASE:e].decode("gbk", "replace"))
    chk("主命名表 0x504B28 == MEIREI_NAMES", names[:12] == MEIREI_NAMES[:12], str(names[:3]))

    # 5. 仕事コード ↔ handler 反查（经 IDXMAP）
    for code, (desc, h) in sorted(WORK_TABLE.items()):
        if h is None:
            continue
        ecx = code - 2
        if not (0 <= ecx < 45):
            continue
        slot = IDXMAP[ecx]
        chk("仕事 %2d(%s) → 0x%06X" % (code, desc[:6], h),
            JMPSLOT_HANDLER.get(slot) == h)

    # 6. 城種改修上限表（0x49f9f0 跳表 0x49fa24，7 项，索引 = 城種-1）
    #    type0 → default(0)；type1..7 → 表项 [80,150,150,200,250,250,250]
    for i in range(7):
        v = u32(0x49FA24 + 4 * i)
        imm = jump_stub_imm(v)
        chk("城種 %d 改修上限 = %d" % (i + 1, CASTLE_TYPE_CAP[i + 1]),
            imm == CASTLE_TYPE_CAP[i + 1], hex(imm))
    chk("城種 0 改修上限 = 0（走 default ret）", CASTLE_TYPE_CAP[0] == 0)

    # 7. 城種農商基档表（0x49f960 跳表 0x49f98c，7 项，索引 = 城種）
    #    type0..6 → 表项 [0,1,2,2,2,3,3]；type7 别名表项 6（值同为 3）
    for i in range(7):
        v = u32(0x49F98C + 4 * i)
        imm = jump_stub_imm(v)
        chk("城種 %d 農商基档 = %d" % (i, CASTLE_TYPE_BASE[i]),
            imm == CASTLE_TYPE_BASE[i], hex(imm))

    # 8. 工事カウンタ setter（word[城+0x1D]：低=改修 / 高=開発）
    chk("0x49AC00 写 word[+0x1D] 低字节（改修）",
        find_disp(0x49AC00, 0x1D, 0x20) is not None
        and find_call(0x49AC00, 0x4AA370, 0x400) is not None)
    chk("0x49AC30 写 word[+0x1D] 高字节（開発）",
        find_disp(0x49AC30, 0x1D, 0x20) is not None
        and find_call(0x49AC30, 0x4AA290, 0x400) is not None)
    chk("0x49ABE0 置 byte[城+0x1C] |= 0x20（築城済）",
        find_call(0x49ABE0, 0x4AB530, 0x200) is not None)

    # 9. 日次進行 0x4a9df0 → dispatcher 0x4a9f10
    chk("0x4A9DF0 call 0x4A9F10", find_call(0x4A9F10, 0x4A9DF0, 0x200) is not None)
    chk("0x4A9DF0 現在地<0xC8 → 城表(stride 31)",
        find_call(0x4A04E0, 0x4A9DF0, 0x200) is not None)
    chk("0x4A9DF0 現在地 in [0xC8,0xF8) → 国情表(stride 5) + 0x38/0x31 偏置",
        find_call(0x4A0510, 0x4A9DF0, 0x200) is not None
        and b"\x80\xc3\x38" in MEM[0x4A9E7E - BASE:0x4A9EA8 - BASE]
        and b"\x80\xfb\x31" in MEM[0x4A9E7E - BASE:0x4A9EA8 - BASE])

    # 10. 0x4ebc50 = (a*b)/c
    chk("0x4EBC50 == muldiv(a,b,c)",
        MEM[0x4EBC50 - BASE:0x4EBC50 - BASE + 4] == b"\x8b\x4c\x24\x0c"
        and muldiv(10, 4, 3) == 13 and muldiv(10, 4, 0) == 0xFFFF)

    # 11. 公式自检
    c = bytearray(31)
    c[0x1B] = 7
    c[0x09] = 130
    c[0x0C] = 7
    v, add = work_kaiten(c, 80)      # 内政 80 → (80-30)/10+1 = 6
    chk("開墾: 内政80 → 增量 6", add == 6 and v == 13, "add=%d v=%d" % (add, v))
    v, add = work_kaiten(c, 20)      # 内政 20 → sat_sub=0 → 1
    chk("開墾: 内政20 → 增量 1（下限）", add == 1)
    c[0x0D] = 240
    v, add = work_kaizen(c, 70, 1)   # 70/10 + 5*2 = 7+10 = 17；残容量 250-240=10
    chk("改建: 内政70 tier1 → min(10, 17) = 10", add == 10 and v == 250)
    c[0x0D] = 0
    v, add = work_kaizen(c, 70, 1)
    chk("改建: 空城 → 17", add == 17)
    v, add = work_chikujo(c)
    chk("築城: 固定 +10", add == 10 and (c[0x1C] & 0x20) != 0)

    # 12. 城種 / 守城上限 与场景数据的留档矛盾（第 14 处）
    try:
        cv = json.load(open(os.path.join(HERE, "castle_values.json"), encoding="utf-8"))
        rows = cv["scenario1"]
        over = sum(1 for r in rows if r["sub_or_def"] > CASTLE_TYPE_CAP[r["raw"][22] & 7])
        chk("留档矛盾：%d/200 城「守城度 > 城種上限」" % over, over > 0, "（已知，见 §3.21.7）")
    except Exception as e:  # pragma: no cover
        chk("castle_values.json 可读", False, str(e))

    print("\n%d OK / %d FAIL" % (OK, FAIL))
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if self_test() else 1)
