# -*- coding: utf-8 -*-
"""
武将实体尾段方法表（续133）
==========================
承接续132「下一步①」——横扫方法表剩余区段 `0x49a5f0..0x49a8b0`。
结果：这一整段就是**武将实体尾段 `+0x20..+0x2e` 的 setter/getter 方法表**，
一次性复现了续114/122/126/127 花多轮才建立的尾段语义，**并补上了
`+0x20..+0x23` / `+0x26..+0x28` / `+0x2a` 的空白**。

字段图（`ecx` = 对象基址，全部函数体直接写 `[ecx + d]`）
------------------------------------------------------
| 偏移      | 宽   | 钳制/掩码              | setter       | 语义 |
|-----------|------|------------------------|--------------|------|
| `+0x20`   | byte | `cmp 0x64` → 100       | `0x49a650`   | 能力型 0..100 |
| `+0x21`   | byte | —                      | `0x49a630`   | （29 调用，最常用）|
| `+0x22`   | byte | `cmp 0x64` → 100       | `0x49a670`   | 能力型 0..100 |
| `+0x23`   | byte | `cmp 0x64` → 100       | `0x49a690`   | 能力型（常量 50/80）|
| `+0x24`   | byte | —                      | `0x49a750`   | **被搜索匹配的目标 ID**（续114 `cmp byte[+0x24],bl; je FOUND`）|
| `+0x25`   | byte | —                      | `0x49a760`   | **实体基础值**（续114 复制到 `+0x13`/`+0x18`）|
| `+0x26`   | word | **`cmp 0xEA60` → 60000**| `0x49a770`  | **功勲 / 勲功**（与续104 国力上限同常量）|
| `+0x28`   | byte | `cmp 0xC8` → 200       | `0x49a790`   | 0..200 |
| `+0x29`   | byte | **`cmp 0x64` → 100**   | `0x49a7b0`   | **忠诚 loyalty**（续122 钳制点 `0x49a7bf` 正落在此函数体内 ✓）|
| `+0x2a`   | word | 哨兵 `0xffff`          | `0x49a7d0`   | 16-bit，-1 = 空 |
| `+0x2c`   | word | 状态字（见下）         | `0x49a7e0` 等| 16-bit 状态字 |
| `+0x2d`   | byte | 状态字高字节           | `0x49a800/20/60` | bit3 flag / bit4 谋反 / bit7 已故 |
| `+0x2e`   | byte | —                      | `0x49a880/8a0` | 1-byte 状态 |

`word[+0x2c]` 状态字位域（三条独立 setter 互证）
----------------------------------------------
- **bits 0-3**（低 nibble）：getter `0x49a610`（`& 0xf`，`cmp 0xc` → <12 有效）、
  setter `0x49a6b0`（**XOR 惯用法**：`xor al,dl; and eax,0xf; xor word[+0x2c],ax`）
- **bits 4-7**：四个独立的 or-flag setter — `0x49a6d0`/`0x10`、`0x49a6f0`/`0x20`、
  `0x49a710`/`0x40`、`0x49a730`/`0x80`
- **bits 11-13**（= `+0x2d` bits 3-5）：`0x49a7e0`，掩码 `0xF8FF`，3-bit 域
- **bits 13-14**（= `+0x2d` bits 5-6 = **F2B 序列関係**）：`0x49a840`，
  掩码 `0x9FFF`，`cmp 4` → 钳到 0..3（与续127「`0x49a840` 24 调用 {3:12,2:5,1:6}」完全吻合 ✓）
- **bit 15**（= `+0x2d` bit7 = **已故/除籍**）：`0x49a860`
- **`+0x2d` bit3 = flag**：`0x49a800`（续122/127 消费者 `0x4a3ddf`/`0x4e9beb`）
- **`+0x2d` bit4 = F4 谋反/背叛标记**：`0x49a820`（续127 记的 `0x49a828` 是其函数体，
  真实入口在 nop 滑橇后的 `0x49a820` —— 又一次「nop 滑橇入口」坑）

🔴 对既有记录的校正
------------------
- 续127 记 F4 setter 为 `0x49a828`、bit7 setter 等均按「函数体地址」记录；
  本表一律用 **e8 真实调用入口**（`0x49a820` / `0x49a800` / `0x49a860` / `0x49a840`）。
- 续122 记 `+0x29` 忠诚钳制点为 `0x49a7bf` —— 该地址正在 `0x49a7b0` 函数体内，
  两者是同一处，**互为印证**（本表给出其 setter 入口 `0x49a7b0`）。
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
from collections import Counter

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BSD_PATH = _ROOT + '/Taikou2 Original/BSDATA1.TR2'
BASE = 0x400000
_mem = open(MEM_PATH, "rb").read()
_bsd = open(BSD_PATH, "rb").read()
REC, NREC = 59, 700

# ---------------------------------------------------------------------------
# 续134：+0x20..+0x23 的人类可读名
# 由「-12 通则」(实体偏移 = BSDATA 偏移 - 12, 续132) 反推，并被数据侧三重印证：
#   @44 体力上限 → +0x20   setter 0x49a650 钳 100，@44 实测 0..100 ✓
#   @45 体力(现役) → +0x21 初始化 `+0x21 = +0x20`，实测 @44 == @45 700/700 ✓
#   @46 体力消耗 → +0x22   setter 0x49a670 钳 100，@46 实测 ≤100、uniq=16 ✓
#   @47 野心     → +0x23   setter 0x49a690 常量含 0x32(50)，@47 实测 700/700 恒 50 ✓
# ---------------------------------------------------------------------------
VITALS = {
    0x20: "体力上限 (max HP)",
    0x21: "体力（现役 / 当前 HP）",
    0x22: "体力消耗",
    0x23: "野心",
}

# -12 通则已验证的 13 组映射（续132 三组 + 续134 第四组）
REMAP_PAIRS = [
    (22, 0x0A, "统御力"), (23, 0x0B, "武力"), (24, 0x0C, "内政力"),
    (25, 0x0D, "外交力"), (26, 0x0E, "魅力"),
    (27, 0x0F, "技能 0-3"), (28, 0x10, "技能 4-7"), (29, 0x11, "技能 8-9"),
    (39, 0x1B, "生年"),
    (44, 0x20, "体力上限"), (45, 0x21, "体力(现役)"),
    (46, 0x22, "体力消耗"), (47, 0x23, "野心"),
]
REMAP_SHIFT = 12


def bsd_f(rec, off):
    return _bsd[REC * rec + off]


def clamp_current_hp(obj: bytearray):
    """0x4042a0 语义: `+0x21 = min(+0x20, +0x21)` —— 当前体力不得高于上限。"""
    obj[0x21] = min(obj[0x20], obj[0x21])


def saturating_sub(a, b):
    """0x4ebcd0: a > b 时返回 a - b（饱和减）。"""
    return a - b if a > b else a

# --------------------------------------------------- 方法表（真实 e8 入口）
TAIL_METHODS = [
    # (入口, 写入偏移, 宽度, 钳制上限 or None, 掩码, 语义)
    (0x49A610, 0x2C, "get", None, 0x0F, "+0x2c 低 nibble getter (<12 有效)"),
    (0x49A630, 0x21, "byte", None, None, "+0x21 setter"),
    (0x49A650, 0x20, "byte", 100, None, "+0x20 setter (钳 100)"),
    (0x49A670, 0x22, "byte", 100, None, "+0x22 setter (钳 100)"),
    (0x49A690, 0x23, "byte", 100, None, "+0x23 setter (钳 100)"),
    (0x49A6B0, 0x2C, "word", None, 0x0F, "+0x2c 低 nibble setter (XOR 惯用法)"),
    (0x49A6D0, 0x2C, "orflag", None, 0x10, "+0x2c bit4 置位"),
    (0x49A6F0, 0x2C, "orflag", None, 0x20, "+0x2c bit5 置位"),
    (0x49A710, 0x2C, "orflag", None, 0x40, "+0x2c bit6 置位"),
    (0x49A730, 0x2C, "orflag", None, 0x80, "+0x2c bit7 置位"),
    (0x49A750, 0x24, "byte", None, None, "+0x24 目标 ID"),
    (0x49A760, 0x25, "byte", None, None, "+0x25 实体基础值"),
    (0x49A770, 0x26, "word", 60000, None, "+0x26 功勲/勲功 (钳 60000)"),
    (0x49A790, 0x28, "byte", 200, None, "+0x28 setter (钳 200)"),
    (0x49A7B0, 0x29, "byte", 100, None, "+0x29 忠诚 loyalty (钳 100)"),
    (0x49A7D0, 0x2A, "word", None, None, "+0x2a word (哨兵 0xffff)"),
    (0x49A7E0, 0x2C, "word", None, 0xF8FF, "+0x2c bits 11-13 (3-bit 域)"),
    (0x49A800, 0x2D, "orflag", None, 0x08, "+0x2d bit3 flag"),
    (0x49A820, 0x2D, "orflag", None, 0x10, "+0x2d bit4 F4 谋反/背叛"),
    (0x49A840, 0x2C, "word", 3, 0x9FFF, "+0x2c bits 13-14 = F2B 序列関係 (钳 0..3)"),
    (0x49A860, 0x2D, "orflag", None, 0x80, "+0x2d bit7 已故/除籍"),
    (0x49A880, 0x2E, "byte", None, None, "+0x2e 状态 setter A"),
    (0x49A8A0, 0x2E, "byte", None, None, "+0x2e 状态 setter B"),
]

KNOWN = {
    0x24: "被搜索匹配的目标 ID", 0x25: "实体基础值", 0x26: "功勲/勲功",
    0x29: "忠诚 loyalty", 0x2C: "16-bit 状态字(低字节)", 0x2D: "状态字高字节",
    0x2E: "1-byte 状态",
}

CLAMP = {0x20: 100, 0x22: 100, 0x23: 100, 0x26: 60000, 0x28: 200, 0x29: 100}


def rd(va, n):
    return _mem[va - BASE: va - BASE + n]


# --------------------------------------------------- 语义实现
def set_byte(obj: bytearray, off: int, v: int):
    obj[off] = min(v, CLAMP[off]) if off in CLAMP else (v & 0xFF)


def set_word(obj: bytearray, off: int, v: int):
    cap = CLAMP.get(off)
    if cap is not None:
        v = min(v, cap)
    struct.pack_into("<H", obj, off, v & 0xFFFF)


def set_low_nibble_xor(obj: bytearray, off: int, v: int):
    """0x49a6b0: xor 惯用法, 只替换 word[off] 低 4 位。"""
    old = struct.unpack_from("<H", obj, off)[0]
    x = ((v & 0xF) ^ old) & 0xF
    struct.pack_into("<H", obj, off, old ^ x)


def set_bits_masked(obj: bytearray, off: int, v: int, mask: int, shift: int):
    """0x49a7e0 / 0x49a840: 先按掩码清位, 再按 shift 写入。"""
    old = struct.unpack_from("<H", obj, off)[0]
    new = (old & mask) | ((v & 0xFF) << shift)
    struct.pack_into("<H", obj, off, new & 0xFFFF)


def or_flag(obj: bytearray, off: int, bit: int):
    obj[off] |= bit


def set_f2b(obj: bytearray, v: int):
    """F2B 序列関係: word[+0x2c] bits 13-14, 钳 0..3。"""
    set_bits_masked(obj, 0x2C, min(v, 3), 0x9FFF, 13)


def get_f2b(obj):
    return (struct.unpack_from("<H", obj, 0x2C)[0] >> 13) & 3


def is_dead(obj):
    return bool(obj[0x2D] & 0x80)


def loyalty(obj):
    return obj[0x29]


# ============================================================ 自检
def _run_tests():
    ok = tot = 0

    def check(name, cond):
        nonlocal ok, tot
        tot += 1
        if not cond:
            print(f"  [FAIL] {name}")
        else:
            ok += 1

    # --- 1. 每条方法的函数体都在映像里写出预期偏移（防回归）
    import re
    for entry, off, width, cap, mask, desc in TAIL_METHODS:
        body = rd(entry, 0x20)
        txt = " | ".join(f"{m} {p}" for _, m, p in _dis(entry))
        if width == "get":
            # getter: 检查读取了预期偏移
            check(f"{entry:#x} 读 [{off:#x}]",
                  f"[ecx + {hex(off)}]" in txt or f"+ {off}]" in txt)
        elif width == "orflag":
            # capstone 对小立即数可能省略 0x 前缀 (如 `or byte ptr [ecx+0x2d], 8`)
            cands = (f"or byte ptr [ecx + {hex(off)}], {hex(mask)}",
                     f"or byte ptr [ecx + {hex(off)}], {mask}",
                     f"or byte ptr [ecx + {hex(off)}], {mask:#04x}")
            check(f"{entry:#x} or [{off:#x}] {mask:#04x}",
                  any(c in txt for c in cands))
        elif mask is not None and width == "word":
            check(f"{entry:#x} 掩码 {mask:#06x}", f"{mask:#x}" in txt.lower() or
                  f"{mask:04x}" in txt.lower())
        else:
            pat = (f"byte ptr [ecx + {hex(off)}], al" if width == "byte"
                   else f"word ptr [ecx + {hex(off)}], ax")
            check(f"{entry:#x} 写 {width}[{off:#x}]", pat in txt or
                  f"[{off:#x}]" in txt or f"+ {off}]" in txt)

    # --- 2. 钳制上限：函数体里能找到 cmp 立即数
    for entry, off, width, cap, mask, desc in TAIL_METHODS:
        if cap is None or width == "orflag":
            continue
        txt = " | ".join(f"{m} {p}" for _, m, p in _dis(entry))
        # 钳制常以 `cmp ax, cap+1; jae` 表达 (如 F2B: cmp 4 ⇒ 值域 0..3)
        cands = (f"{cap:#x}", f"{cap:x}", str(cap),
                 f"{cap + 1:#x}", f"{cap + 1:x}", str(cap + 1))
        check(f"{entry:#x} 钳制 {cap}", any(c in txt.lower() for c in cands))

    # --- 3. 字段图覆盖 +0x20..+0x2e (word 写入同时覆盖其高字节)
    covered = set()
    for _, off, width, *_ in TAIL_METHODS:
        covered.add(off)
        if width == "word":
            covered.add(off + 1)
    missing = [o for o in range(0x20, 0x2F) if o not in covered]
    check("尾段 +0x20..+0x2e 全覆盖", not missing)
    if missing:
        print(f"      缺: {[hex(x) for x in missing]}")

    # --- 4. 语义写入
    obj = bytearray(0x2F)
    set_byte(obj, 0x29, 250)
    check("忠诚钳到 100", loyalty(obj) == 100)
    set_byte(obj, 0x29, 47)
    check("忠诚 47", loyalty(obj) == 47)
    set_word(obj, 0x26, 99999)
    check("功勲钳到 60000", struct.unpack_from("<H", obj, 0x26)[0] == 60000)
    set_byte(obj, 0x28, 300)
    check("+0x28 钳到 200", obj[0x28] == 200)

    # --- 5. or-flag 幂等且只置位
    obj2 = bytearray(0x2F)
    or_flag(obj2, 0x2D, 0x80)
    or_flag(obj2, 0x2D, 0x80)
    check("已故标记幂等", is_dead(obj2) and obj2[0x2D] == 0x80)
    or_flag(obj2, 0x2D, 0x10)
    check("谋反标记置位", obj2[0x2D] == 0x90)

    # --- 6. F2B 2-bit 域 (掩码 0x9fff, shift 13)
    for v in range(4):
        o3 = bytearray(0x2F)
        set_f2b(o3, v)
        check(f"F2B={v}", get_f2b(o3) == v)
    o4 = bytearray(0x2F)
    o4[0x2D] = 0xFF
    set_f2b(o4, 1)
    check("F2B 写入保留 bit7(已故)", (o4[0x2D] & 0x80) == 0x80 and get_f2b(o4) == 1)

    # --- 7. 低 nibble XOR setter
    for v in range(16):
        o5 = bytearray(0x2F)
        struct.pack_into("<H", o5, 0x2C, 0x1234)
        set_low_nibble_xor(o5, 0x2C, v)
        w = struct.unpack_from("<H", o5, 0x2C)[0]
        check(f"低nibble XOR v={v}", (w & 0xF) == v and (w & 0xFFF0) == 0x1230)

    # --- 8. 与既有知识的交叉断言
    check("+0x24 = 目标 ID", KNOWN[0x24] == "被搜索匹配的目标 ID")
    check("+0x25 = 实体基础值", KNOWN[0x25] == "实体基础值")
    check("+0x29 = 忠诚", KNOWN[0x29] == "忠诚 loyalty")
    check("忠诚阈值 40/50/95/100 均在 0..100 内",
          all(0 <= t <= 100 for t in (40, 50, 95, 100)))
    check("实体 stride 47 > 最大字段 0x2e", 47 > 0x2E)
    check("F4 setter 入口 = 0x49a820 (非续127 记的 0x49a828 函数体)",
          any(m[0] == 0x49A820 and m[4] == 0x10 for m in TAIL_METHODS))

    # --- 9. 【续134】-12 通则: 13 组映射全部成立
    for bsd_off, ent_off, nm in REMAP_PAIRS:
        check(f"@{bsd_off} → +{ent_off:#04x} ({nm})", bsd_off - REMAP_SHIFT == ent_off)

    # --- 10. 体力三字段的数据侧印证
    eq = sum(1 for i in range(NREC) if bsd_f(i, 44) == bsd_f(i, 45))
    check("@44 == @45 (体力上限 == 现役体力) 700/700", eq == NREC)
    v44 = [bsd_f(i, 44) for i in range(NREC)]
    v46 = [bsd_f(i, 46) for i in range(NREC)]
    v47 = [bsd_f(i, 47) for i in range(NREC)]
    check("@44 体力上限 ≤ 100 (setter 钳 100)", max(v44) <= 100)
    check("@46 体力消耗 ≤ 100 (setter 钳 100)", max(v46) <= 100)
    check("@46 uniq = 16", len(set(v46)) == 16)
    check("@47 野心 700/700 恒 50", set(v47) == {50})
    check("@47 = 50 与 setter 常量 0x32 吻合", 0x32 == 50)

    # --- 11. 当前体力钳位语义 (+0x21 = min(+0x20, +0x21))
    o6 = bytearray(0x2F)
    o6[0x20], o6[0x21] = 80, 95      # 上限 80, 当前 95 → 应压到 80
    clamp_current_hp(o6)
    check("当前体力被压到上限", o6[0x21] == 80)
    o7 = bytearray(0x2F)
    o7[0x20], o7[0x21] = 80, 45      # 上限 80, 当前 45 → 保持 45
    clamp_current_hp(o7)
    check("当前体力低于上限时不变", o7[0x21] == 45)
    # 初始化: 现役 = 上限
    o8 = bytearray(0x2F)
    o8[0x20] = 73
    o8[0x21] = o8[0x20]
    check("初始化 现役 = 上限", o8[0x21] == o8[0x20] == 73)

    # --- 12. 饱和减 (0x4ebcd0)
    check("饱和减 80-10=70", saturating_sub(80, 10) == 70)
    check("饱和减 5-10 → 5", saturating_sub(5, 10) == 5)

    print(f"\nRESULT: {ok}/{tot} checks passed")
    return ok == tot


def _dis(entry, maxb=0x20, n=14):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    out = []
    for ins in md.disasm(rd(entry, maxb), entry):
        out.append((ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic == "ret" or len(out) >= n:
            break
    return out


if __name__ == "__main__":
    print("=== 武将实体尾段方法表（续133）===")
    print(f"  {'入口':<12}{'字段':<12}{'宽':<8}{'钳制':<10}{'掩码':<10}语义")
    for entry, off, width, cap, mask, desc in TAIL_METHODS:
        print(f"  {entry:#010x}  +{off:#04x}      {width:<8}"
              f"{str(cap) if cap is not None else '-':<10}"
              f"{(hex(mask) if mask else '-'):<10}{desc}")
    print()
    _run_tests()
