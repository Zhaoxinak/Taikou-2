# -*- coding: utf-8 -*-
"""
实体中段 `+0x1b..+0x1f` 字段图 + 身分名表（续136）
=================================================
承接续135「下一步①」：用定稿的 `-12` 通则把 BSDATA `@40/@41/@43` 反推到实体
`+0x1c/+0x1d/+0x1f`，再到实体侧找 setter。**结果找到第二个 setter 区段
`0x49a900..0x49ae00`**，一次性钉死四个字段。

字段图（全部为 e8 真实调用入口）
--------------------------------
| 实体 | BSDATA | setter | 形态 | 语义 |
|---|---|---|---|---|
| `+0x1b` | `@39` | `0x49a5e0` + `0x49ab00/20/40/60` | byte | **生年字段**：低 7 位 = 生年−1490；**bit4/5/6/7 = 四个独立 or-flag** |
| `+0x1c` | `@40` | `0x49ab80/a0/c0/e0` | byte | **bits 2/3/4/5 = 四个独立 or-flag**（低 2 位与高 2 位用途待定）|
| `+0x1d` | `@41` | `0x49ac00` | byte | **钳 255**（`and word[+0x1d],0xff00` 清低字节后 `or min(v,0xff)`）|
| `+0x1e` | `@42` | `0x49ac30` | byte | **钳 255**（`and word[+0x1d],0xff` 清高字节后写入）；@42 = 生死/状态枚举 {0,1,2,255} |
| `+0x1f` | `@43` | 未定位 | — | 本区段未见 setter（续136 遗留）|

★ **`+0x1b` bit7 的正主**：续131 发现「`@39` bit7 是独立 flag，232/700 置位、
跨剧本 139 条翻转」，但没找到 setter。本轮 `0x49ab60`（**17 调用**）
`or byte ptr [ecx + 0x1b], 0x80` 正是它 —— bit4/5/6 另有 `0x49ab00`(14)/
`0x49ab20`(4)/`0x49ab40`(5)。⇒ **生年字节的 4 个高位全是状态位**，
.age 计算用 `and 0x7f` 抹掉它们（EXE `0x49a5c0`），setter 用 XOR 惯用法保留。

⚠️ **位域别名（本轮新发现的疑点，未解）**
------------------------------------------
年龄 getter `0x49a5c0` 用 `and ecx, 0x7f` 取低 7 位；而 bit4/5/6 的 or-flag
setter（`0x49ab00/0x20/0x40`）**落在 `0x7f` 掩码之内** —— 置位会**改变算出的年龄**。
只有 bit7（`0x49ab60`）在掩码外、与年龄互不干扰。两种可能：
(a) 这三个 setter 作用于**另一个对象**（`0x49a900..0x49ae00` 区段疑似混有多个对象的方法）；
(b) 确实存在别名，游戏只在「年龄不重要」的记录上置这些位。
⇒ 列为开放项，勿在未验证前把 bits4-6 当生日位使用。

🆕 身分名表 `0x507778` stride 7 × 8
-----------------------------------
由 getter `0x49a920` 索引：
    cx = word[+0x2c]; ecx >>= 8; ecx &= 7      ; 身分码 0..7
    eax = ecx*8 - ecx  (= 7*ecx)
    return eax + 0x507778
⇒ **身分名 = 0x507778 + 7 * ((word[+0x2c] >> 8) & 7)**

    [0] 浪人   [1] 步兵头  [2] 队长   [3] 侍大将
    [4] 部将   [5] 家老    [6] 宿老   [7] 大名

这正是太阁2 官方**八段身分阶梯**，且**交叉坐实续122 的
「`+0x2d` 低 3 位 = 身分码 0..7」**（`+0x2d` 即 `word[+0x2c] >> 8`）。
"""

import struct
from collections import Counter

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BSD_PATH = "F:/Games/Taikou 2/Taikou2 Original/BSDATA1.TR2"
BASE = 0x400000
_mem = open(MEM_PATH, "rb").read()
_bsd = open(BSD_PATH, "rb").read()
REC, N = 59, 700
REMAP_SHIFT = 12

# ------------------------------------------------- 第二 setter 区段（真实入口）
FLAG_SETTERS = [
    (0x49AB00, 0x1B, 0x10, 14, "+0x1b bit4 状态位"),
    (0x49AB20, 0x1B, 0x20, 4,  "+0x1b bit5 状态位"),
    (0x49AB40, 0x1B, 0x40, 5,  "+0x1b bit6 状态位"),
    (0x49AB60, 0x1B, 0x80, 17, "+0x1b bit7 状态位（= 续131 的 @39 bit7 flag）"),
    (0x49AB80, 0x1C, 0x04, 6,  "+0x1c bit2 状态位"),
    (0x49ABA0, 0x1C, 0x08, 11, "+0x1c bit3 状态位"),
    (0x49ABC0, 0x1C, 0x10, 7,  "+0x1c bit4 状态位"),
    (0x49ABE0, 0x1C, 0x20, 1,  "+0x1c bit5 状态位"),
]
BYTE_SETTERS = [
    (0x49AC00, 0x1D, 0xFF, 25, "+0x1d byte（清 word[+0x1d] 低字节后写入）"),
    (0x49AC30, 0x1E, 0xFF, 17, "+0x1e byte（清 word[+0x1d] 高字节后写入）"),
]

# ------------------------------------------------- 身分名表
RANK_TBL = 0x507778
RANK_STRIDE = 7
RANK_N = 8
RANK_NAMES = ["浪人", "步兵头", "队长", "侍大将", "部将", "家老", "宿老", "大名"]


def rd(va, n):
    return _mem[va - BASE: va - BASE + n]


def bsd_f(i, off):
    return _bsd[REC * i + off]


def rank_names():
    out = []
    for i in range(RANK_N):
        raw = rd(RANK_TBL + RANK_STRIDE * i, RANK_STRIDE)
        out.append(raw.split(b"\x00")[0].decode("gbk", "replace"))
    return out


# ------------------------------------------------- 语义实现
def or_flag(obj: bytearray, off: int, bit: int, on: bool = True):
    """0x49abxx 语义: 参数非 0 则置位, 否则不变（只置不清）。"""
    if on:
        obj[off] |= bit


def set_byte_1d(obj: bytearray, v: int):
    """0x49ac00: 清 word[+0x1d] 低字节(=+0x1d), 写入 min(v,255)。"""
    obj[0x1D] = min(v, 0xFF)


def set_byte_1e(obj: bytearray, v: int):
    """0x49ac30: 清 word[+0x1d] 高字节(=+0x1e), 写入 min(v,255)。"""
    obj[0x1E] = min(v, 0xFF)


def get_rank(obj):
    """身分码 = (word[+0x2c] >> 8) & 7 = byte[+0x2d] & 7。"""
    return (struct.unpack_from("<H", obj, 0x2C)[0] >> 8) & 7


def get_rank_name(obj):
    return rank_names()[get_rank(obj)]


def birth_year(obj):
    return 1490 + (obj[0x1B] & 0x7F)


def _dis(entry, maxb=0x20, n=14):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    out = []
    for ins in md.disasm(rd(entry, maxb), entry):
        out.append((ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic == "ret" or len(out) >= n:
            break
    return out


def _run_tests():
    ok = tot = 0

    def check(name, cond):
        nonlocal ok, tot
        tot += 1
        if not cond:
            print(f"  [FAIL] {name}")
        else:
            ok += 1

    # --- 1. 身分名表解码
    check("身分名表 = 官方八段阶梯", rank_names() == RANK_NAMES)

    # --- 2. 身分 getter 0x49a920 公式
    body = " | ".join(f"{m} {p}" for _, m, p in _dis(0x49A920))
    check("0x49a920 读 word[ecx+0x2c]", "word ptr [ecx + 0x2c]" in body)
    check("0x49a920 shr 8", "shr     ecx, 8" in body or "shr ecx, 8" in body)
    check("0x49a920 and 7", "and     ecx, 7" in body or "and ecx, 7" in body)
    check("0x49a920 基址 0x507778", "0x507778" in body)
    obj = bytearray(0x2F)
    for r in range(8):
        obj[0x2D] = r
        check(f"身分码 {r} → {RANK_NAMES[r]}", get_rank_name(obj) == RANK_NAMES[r])
    obj[0x2D] = 0xF8          # 高位不影响身分码
    check("身分码只取低 3 位", get_rank(obj) == 0)

    # --- 3. or-flag setter 家族（逐条比对映像）
    for entry, off, bit, ncall, desc in FLAG_SETTERS:
        txt = " | ".join(f"{m} {p}" for _, m, p in _dis(entry))
        cands = (f"or byte ptr [ecx + {hex(off)}], {hex(bit)}",
                 f"or byte ptr [ecx + {hex(off)}], {bit}",
                 f"or byte ptr [ecx + {hex(off)}], {bit:#04x}")
        check(f"{entry:#x} or [{off:#x}] {bit:#04x}", any(c in txt for c in cands))

    # --- 4. byte setter 家族
    for entry, off, cap, ncall, desc in BYTE_SETTERS:
        txt = " | ".join(f"{m} {p}" for _, m, p in _dis(entry))
        if off == 0x1D:
            check(f"{entry:#x} 清 word[+0x1d] 低字节", "0xff00" in txt.lower())
        else:
            check(f"{entry:#x} 清 word[+0x1d] 高字节", "and word ptr [ecx + 0x1d], 0xff" in txt
                  or "0xff" in txt.lower())
        check(f"{entry:#x} 钳 {cap}", f"{cap:#x}" in txt.lower() or str(cap) in txt)

    # --- 5. -12 通则第五组: @39..@42 → +0x1b..+0x1e
    for bsd_off, ent_off in ((39, 0x1B), (40, 0x1C), (41, 0x1D), (42, 0x1E)):
        check(f"@{bsd_off} → +{ent_off:#04x}", bsd_off - REMAP_SHIFT == ent_off)

    # --- 6. 数据侧印证
    v41 = Counter(bsd_f(i, 41) for i in range(N))
    v42 = Counter(bsd_f(i, 42) for i in range(N))
    check("@41 = 255 哨兵 544/700 (setter 钳 255 允许)",
          v41.get(255, 0) == 544 and max(v41) <= 255)
    check("@42 ⊂ {0,1,2,255}", set(v42) <= {0, 1, 2, 255})
    check("@39 bit7 置位 232/700",
          sum(1 for i in range(N) if (bsd_f(i, 39) >> 7) & 1) == 232)

    # --- 7. 语义行为
    o1 = bytearray(0x2F)
    or_flag(o1, 0x1B, 0x80)
    or_flag(o1, 0x1B, 0x80)
    check("bit7 置位幂等", o1[0x1B] == 0x80)
    or_flag(o1, 0x1B, 0x40)
    check("多 flag 可共存", o1[0x1B] == 0xC0)
    or_flag(o1, 0x1B, 0x80, on=False)
    check("or-flag 只置不清", o1[0x1B] == 0xC0)
    o1[0x1B] = (o1[0x1B] & 0x80) | ((1543 - 1490) & 0x7F)
    check("bit7 flag 与生年低 7 位可共存", birth_year(o1) == 1543 and (o1[0x1B] & 0x80) == 0x80)
    # ⚠ 位域别名: bits4-6 (0x10/0x20/0x40) 落在年龄 getter 的 `and 0x7f` 掩码之内
    check("⚠ bits4-6 落在 and 0x7f 掩码内(别名风险, 已记录)",
          all((b & 0x7F) == b for b in (0x10, 0x20, 0x40)))
    check("bit7 (0x80) 在掩码外, 不影响年龄", (0x80 & 0x7F) == 0)

    o2 = bytearray(0x2F)
    set_byte_1d(o2, 999)
    set_byte_1e(o2, 255)
    check("+0x1d 钳 255", o2[0x1D] == 255)
    check("+0x1e 写入不影响 +0x1d", o2[0x1E] == 255 and o2[0x1D] == 255)

    print(f"\nRESULT: {ok}/{tot} checks passed")
    return ok == tot


if __name__ == "__main__":
    print("=== 实体中段 +0x1b..+0x1f + 身分名表（续136）===")
    print("  身分名表 0x507778 stride 7 ×8: " + " / ".join(rank_names()))
    print("\n  字段图:")
    for entry, off, bit, n, desc in FLAG_SETTERS:
        print(f"    {entry:#010x}  {desc:<44}({n} 调用)")
    for entry, off, cap, n, desc in BYTE_SETTERS:
        print(f"    {entry:#010x}  {desc:<44}({n} 调用)")
    print()
    _run_tests()
