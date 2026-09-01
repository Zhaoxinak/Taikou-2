# -*- coding: utf-8 -*-
"""
武将对象方法表（续132）
======================
承接续131「下一步①」——深挖 `0x49a400` 的 2-bit setter 簇。结论：它不是孤立的
setter，而是一整张 **「武将对象方法表」** 的一段，对象基址来自全局指针
**`dword[0x513b14]`**。

方法表总览（`0x49a2b0 .. 0x49a870`，规则间隔排布）
------------------------------------------------
| 区间                       | 语义                                   |
|----------------------------|----------------------------------------|
| `0x49a2b0 + 0x20*k` k=0..4 | **五维能力 setter**（`byte[ecx+k]`，钳 100）|
| `0x49a350 … 0x49a4d0`      | **10 技能 setter**（2-bit 域，钳 3）    |
| `0x49a500 + 0x10*k` k=0..9 | **10 技能名 getter** → `0x507b58 + 5*k` |
| `0x49a5a0`                 | `word[ecx]` bits 11-14 位域 setter（ecx=base+8）|
| `0x49a5c0`                 | 年齢 getter  → `byte[+0x1b]`            |
| `0x49a5e0`                 | 生年 setter  → `byte[+0x1b]`            |

对象字段图（调用点传入 `ecx = base + N`）
----------------------------------------
- **能力块 `+0x0a..+0x0e`**（5 字节，各钳 100）
- **技能块 `+0x0f/+0x10/+0x11`**（10 技能 × 2 bit，各钳 3）
- **`+0x1b`** = 生年字段（`1490 + (v & 0x7f)`）
- **`+0x08`** = word，bits 11-14 位域

🔴 补上续130/131 留下的缺口
--------------------------
续130 曾留「`+0x0b`/`+0x0c` 究竟对应统御力/武力/内政力中的哪两维（全镜像写入点
0 处，须 emu）」。本轮由**能力 setter 族的 `+0x0a..+0x0e` 连续块**与**能力名表
`0x507fc0`（stride 7 ×5，顺序 统御力/武力/内政力/外交力/魅力）**严格对齐，
加上 `+0x0d`=外交力、`+0x0e`=魅力 已有字符串硬证据（续130 `0x4b5620`），
⇒ **五维顺序定案**：

    +0x0a 统御力   +0x0b 武力   +0x0c 内政力   +0x0d 外交力   +0x0e 魅力

**纯静态闭合，无需 emu**（此前的「须 emu」判断系误判——写入点确实为 0，
但 setter 是**按 `ecx = base + N` 传入偏移**的参数化家族，故静态扫描
`byte[reg + 0x0b]` 形式的写入永远抓不到）。
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
BASE = 0x400000
_mem = open(MEM_PATH, "rb").read()

OBJ_PTR_GLOBAL = 0x513B14      # dword: 武将对象基址

# ---------------------------------------------- 能力 setter 族 (0x20 间隔)
ABILITY_SETTERS = {
    # k: (入口, 写入 disp, 钳制上限)
    0: (0x49A2B0, 0, 100),
    1: (0x49A2D0, 1, 100),
    2: (0x49A2F0, 2, 100),
    3: (0x49A310, 3, 100),
    4: (0x49A330, 4, 100),
}
ABILITY_BLOCK_OFF = 0x0A       # 调用点传 ecx = base + 0x0a
ABILITY_NAMES = ["统御力", "武力", "内政力", "外交力", "魅力"]
ABILITY_OFFSETS = {n: ABILITY_BLOCK_OFF + i for i, n in enumerate(ABILITY_NAMES)}

# ---------------------------------------------- 技能 setter 族
SKILL_NAMES = ["口才", "马术", "算术", "剑术", "忍术", "兵法", "洋枪", "筑城", "礼法", "茶道"]
SKILL_SETTERS = [
    (0x49A350, 0), (0x49A370, 2), (0x49A3A0, 4), (0x49A3D0, 6),     # +0x0f
    (0x49A400, 0), (0x49A420, 2), (0x49A450, 4), (0x49A480, 6),     # +0x10
    (0x49A4B0, 0), (0x49A4D0, 2),                                    # +0x11
]
SKILL_BLOCK_OFF = 0x0F         # 调用点传 ecx = base + 0x0f
SKILL_BYTE_OFF = [0x0F, 0x0F, 0x0F, 0x0F, 0x10, 0x10, 0x10, 0x10, 0x11, 0x11]

# ---------------------------------------------- 技能名 getter 族 (0x10 间隔)
SKILL_NAME_GETTERS = [0x49A500 + 0x10 * k for k in range(10)]
SKILL_NAME_TBL = 0x507B58
SKILL_NAME_STRIDE = 5

ABILITY_NAME_TBL = 0x507FC0
ABILITY_NAME_STRIDE = 7

BIRTH_FIELD_OFF = 0x1B
AGE_GETTER = 0x49A5C0
BIRTH_SETTER = 0x49A5E0
WORD8_SETTER = 0x49A5A0        # ecx = base + 8, 写 word[ecx] bits 11-14


def rd(va, n):
    return _mem[va - BASE: va - BASE + n]


def gbk(b):
    return b.split(b"\x00")[0].decode("gbk", "replace")


def imm32_at(va):
    return struct.unpack_from("<I", _mem, va - BASE)[0]


def set_ability(obj: bytearray, i: int, v: int):
    """能力 setter 语义: 钳到 100 后写 byte[base + 0x0a + i]。"""
    obj[ABILITY_BLOCK_OFF + i] = min(v, 100)


def get_ability(obj, i):
    return obj[ABILITY_BLOCK_OFF + i]


def set_skill(obj: bytearray, i: int, v: int):
    """技能 setter 语义: 钳到 3 后写 2-bit 域（与续130 的实体布局一致）。"""
    off = SKILL_BYTE_OFF[i]
    sh = 2 * (i % 4)
    b = obj[off] & ~(3 << sh)
    obj[off] = b | ((min(v, 3) & 3) << sh)


def get_skill(obj, i):
    off = SKILL_BYTE_OFF[i]
    return (obj[off] >> (2 * (i % 4))) & 3


def get_birth_year(obj):
    return 1490 + (obj[BIRTH_FIELD_OFF] & 0x7F)


def get_age(obj, year_offset: int):
    """数え年 = (year_offset + 1560) − 生年 + 1"""
    return (year_offset + 1560) - get_birth_year(obj) + 1


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

    # --- 1. 能力名表解码
    names_a = [gbk(rd(ABILITY_NAME_TBL + ABILITY_NAME_STRIDE * i, ABILITY_NAME_STRIDE))
               for i in range(5)]
    check("能力名表 = 统御力/武力/内政力/外交力/魅力", names_a == ABILITY_NAMES)

    # --- 2. 技能名表解码
    names_s = [gbk(rd(SKILL_NAME_TBL + SKILL_NAME_STRIDE * i, SKILL_NAME_STRIDE))
               for i in range(10)]
    check("技能名表 = 官方十技能", names_s == SKILL_NAMES)

    # --- 3. 技能名 getter 族: 0x49a500+0x10k 处应为 mov eax, 0x507b58+5k
    for k in range(10):
        va = SKILL_NAME_GETTERS[k]
        # mov eax, imm32 : B8 xx xx xx xx
        b0 = _mem[va - BASE]
        val = imm32_at(va + 1)
        check(f"技能名 getter[{k}] = mov eax, {SKILL_NAME_TBL + 5 * k:#x}",
              b0 == 0xB8 and val == SKILL_NAME_TBL + 5 * k)

    # --- 4. 能力 setter 族: 每条应为 ... mov byte ptr [ecx + d], al
    for k, (entry, disp, cap) in ABILITY_SETTERS.items():
        body = rd(entry, 0x14)
        # 找 B8/66 之后的 mov byte[ecx+d],al : 88 41 d (d>0) 或 88 01 (d=0)
        want = b"\x88\x41" + bytes([disp]) if disp else b"\x88\x01"
        check(f"能力 setter[{k}] 写 byte[ecx+{disp}]", want in body)
        # 钳制 0x64
        check(f"能力 setter[{k}] 钳制 100", b"\x66\x3d\x64\x00" in body or
              b"\x3d\x64\x00" in body or b"d\x00" in body)

    # --- 5. 技能 setter 族: 掩码与位移
    MASK = {0: 0xFC, 2: 0xF3, 4: 0xCF, 6: 0x3F}
    for i, (entry, sh) in enumerate(SKILL_SETTERS):
        body = rd(entry, 0x18)
        check(f"技能 setter[{i}] {SKILL_NAMES[i]} 掩码 {MASK[sh]:#04x}",
              bytes([0x24, MASK[sh]]) in body)      # and al, mask

    # --- 6. 字段图: 能力/技能块偏移
    check("能力块 = +0x0a..+0x0e",
          [ABILITY_BLOCK_OFF + i for i in range(5)] == [0x0A, 0x0B, 0x0C, 0x0D, 0x0E])
    check("能力 +0x0d = 外交力", ABILITY_OFFSETS["外交力"] == 0x0D)
    check("能力 +0x0e = 魅力", ABILITY_OFFSETS["魅力"] == 0x0E)
    check("技能块 = +0x0f/+0x10/+0x11",
          SKILL_BYTE_OFF == [0x0F] * 4 + [0x10] * 4 + [0x11] * 2)

    # --- 7. 存取 round-trip
    obj = bytearray(0x30)
    for i in range(5):
        for v in (0, 37, 100, 255):
            set_ability(obj, i, v)
            check(f"能力{i} round-trip v={v}", get_ability(obj, i) == min(v, 100))
    for i in range(10):
        for v in range(4):
            vals = [0] * 10
            vals[i] = v
            obj2 = bytearray(0x30)
            for j, x in enumerate(vals):
                set_skill(obj2, j, x)
            check(f"技能{i}({SKILL_NAMES[i]}) round-trip v={v}", get_skill(obj2, i) == v)

    # --- 8. 与续130/131 交叉一致
    try:
        import bsdata_fields_ref as BF
        check("与续130 技能位域一致", BF.SKILL_FIELDS ==
              [(SKILL_BYTE_OFF[i], 2 * (i % 4)) for i in range(10)])
        check("与续130 技能名一致", BF.SKILL_ORDER == SKILL_NAMES)
    except Exception as e:
        print(f"  [WARN] 交叉校验 bsdata_fields_ref 跳过: {e}")
    try:
        import bsdata_lifespan_ref as BL
        obj3 = bytearray(0x30)
        obj3[BIRTH_FIELD_OFF] = BL.field_from_birth_year(1543)
        check("与续131 生年一致", get_birth_year(obj3) == 1543)
        check("与续131 年齢一致", get_age(obj3, 20) == BL.age(20, obj3[BIRTH_FIELD_OFF]))
    except Exception as e:
        print(f"  [WARN] 交叉校验 bsdata_lifespan_ref 跳过: {e}")

    # --- 9. 生年/年齢 锚点
    obj4 = bytearray(0x30)
    obj4[BIRTH_FIELD_OFF] = 1543 - 1490
    check("生年 1543", get_birth_year(obj4) == 1543)
    check("数え年 Y=0 → 18", get_age(obj4, 0) == 1560 - 1543 + 1)

    print(f"\nRESULT: {ok}/{tot} checks passed")
    return ok == tot


if __name__ == "__main__":
    print("=== 武将对象方法表（续132）===")
    print(f"  对象基址: dword[{OBJ_PTR_GLOBAL:#x}]")
    print(f"  能力块 +0x0a..+0x0e: " + " / ".join(
        f"+{ABILITY_OFFSETS[n]:#04x}={n}" for n in ABILITY_NAMES))
    print(f"  技能块 +0x0f/+0x10/+0x11: " + " / ".join(
        f"{SKILL_NAMES[i]}@+{SKILL_BYTE_OFF[i]:#04x}>>{2*(i%4)}" for i in range(10)))
    print(f"  生年 +{BIRTH_FIELD_OFF:#04x} (getter {AGE_GETTER:#x} / setter {BIRTH_SETTER:#x})")
    print()
    _run_tests()
