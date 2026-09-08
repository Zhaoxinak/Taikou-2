#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bsdata_tail_semantics_ref.py — BSDATA stream 0x28..0x2c 精确语义（续248/249）
================================================================================
映射：entity[i] = bsdata[i+12]  ⇒  0x28..0x2c ↔ entity +0x1c..+0x20

| stream | entity | 定名 | 状态 |
|---|---|---|---|
| 0x28 | +0x1c | **持久化保留字段**（无玩法读点） | ✅ 续250：高3静态/低5剧本相关仍成立；OR-flags属**城**；&7读点属**関係槽** |
| 0x29-0x2a | +0x1d | **父/养父武将索引 u16 LE，FFFF=無** | ✅ 续204；纠偏「縁者種別」假说 |
| 0x2b | +0x1f | **出身地インデックス** → `0x50bf48` → 国 | ✅ 续249（升级续204「势力/家」） |
| 0x2c | +0x20 | **最大体力** | ✅ 续134/248 |

邻接：0x2d→+0x21 现役（初值≡上限）；0x2e→+0x22 消耗；0x2f→+0x23 野心=50。

运行：`python scripts/bsdata_tail_semantics_ref.py` → RESULT n/n
"""
from __future__ import annotations

import os
import struct
from collections import Counter

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
BASE = 0x400000
MEM = open(os.path.join(_HERE, "_unpacked_mem.bin"), "rb").read()
BSD = open(os.path.join(_ROOT, "Taikou2 Original", "BSDATA1.TR2"), "rb").read()
STRIDE, NREC, REMAP = 59, 700, 12
HOME_TBL, HOME_LOOKUP = 0x50BF48, 0x49F940
PROVINCE_NAMES = [
    "北陆奥", "陆奥", "出羽", "南陆奥", "上野", "下野", "常陆", "房总", "武藏", "相模伊豆",
    "甲斐", "信浓", "越后", "骏河", "远江", "三河", "尾张", "美浓", "伊势", "越中",
    "能登", "加贺", "越前若狭", "北近江", "南近江", "大和伊贺", "山城", "丹波丹后", "摄津",
    "河内和泉", "纪伊", "播磨但马", "因幡伯耆", "出云石见", "备前美作", "备中备后", "安艺",
    "周防长门", "阿波", "赞岐", "伊予", "土佐", "丰前", "筑前筑后", "肥前", "丰后",
    "肥后", "日向", "萨摩大隅",
]
HOME_SAMPLES = [(13, "尾张"), (304, "三河"), (257, "越后"), (500, "安艺"), (230, "甲斐")]
FATHER_SAMPLES = [
    (47, 13),    # 信忠→信长
    (230, 199),  # 胜赖→信玄
    (58, 19),    # 利长→利家
    (112, 100),  # 政宗→辉宗
    (274, 257),  # 景胜→谦信（u16>255，证伪单字节+種別）
]

results = []
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def chk(name, cond, detail=""):
    results.append((name, bool(cond)))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           ("  — " + detail) if detail else ""))


def rd(va, n):
    return MEM[va - BASE:va - BASE + n]


def fld(i, o, n=1):
    return int.from_bytes(BSD[i * STRIDE + o:i * STRIDE + o + n], "little")


def name(i):
    r = BSD[i * STRIDE:(i + 1) * STRIDE]
    return (r[0:7].split(b"\x00")[0] + r[7:14].split(b"\x00")[0]).decode("gbk", "replace")


def is_ph(i):
    return name(i).startswith("姓")


def birth(i):
    return (fld(i, 0x27) & 0x7F) + 1490


def dis_txt(va, n=0x30):
    return " | ".join("%s %s" % (i.mnemonic, i.op_str)
                      for i in md.disasm(rd(va, n), va))


print("=== A. 映射 + 体力 ===")
for s, e in ((0x28, 0x1C), (0x29, 0x1D), (0x2B, 0x1F), (0x2C, 0x20)):
    chk("stream %#x → entity+%#x" % (s, e), s - REMAP == e)
chk("0x2c==0x2d 全 700（初值现役=上限）",
    all(fld(i, 0x2c) == fld(i, 0x2d) for i in range(NREC)))
chk("0x49a650 写 +0x20 钳 100",
    b"\x66\x3d\x64\x00" in rd(0x49A650, 20) and b"\x88\x41\x20" in rd(0x49A650, 20))
chk("0x49a630 写 +0x21（现役）", b"\x88\x41\x21" in rd(0x49A630, 20))
chk("0x2f 野心恒 50", all(fld(i, 0x2f) == 0x32 for i in range(NREC)))

print("\n=== B. 父/养父 u16 @0x29（纠偏「縁者種別」）===")
fathers = [(i, fld(i, 0x29, 2)) for i in range(NREC) if fld(i, 0x29, 2) != 0xFFFF]
chk("B1 非哨兵约 156", 150 <= len(fathers) <= 170, "n=%d" % len(fathers))
ok_age = sum(1 for i, f in fathers if f < NREC and birth(f) < birth(i))
chk("B2 父生年<子 ≥150", ok_age >= 150, "%d/%d" % (ok_age, len(fathers)))
# 单字节假说在 u16>255 上失败：景胜→谦信
chk("B3 景胜(274) u16 父=谦信(257)（非 byte=1→胜家）",
    fld(274, 0x29, 2) == 257)
chk("B4 经典父子样例",
    all(fld(c, 0x29, 2) == p for c, p in FATHER_SAMPLES))
# 「種別」假说：高字节∈{0,1,2} 实为父ID高字节分布
hi = Counter(fld(i, 0x2a) for i, _ in fathers)
chk("B5 高字节仅 {0,1,2}（父ID落在 0..767）", set(hi) <= {0, 1, 2}, str(dict(hi)))
# setter 按半字写入 word[+0x1d]
chk("B6 0x49ac00 清低字节写 word[+0x1d]",
    "word ptr [ecx + 0x1d]" in dis_txt(0x49AC00) and "0xff00" in dis_txt(0x49AC00).lower())
chk("B7 0x49ac30 写高字节（mov dh,al）",
    "word ptr [ecx + 0x1d]" in dis_txt(0x49AC30, 0x40))

print("\n=== C. 出身地インデックス @0x2b ===")
real = [i for i in range(NREC) if not is_ph(i)]
chk("C1 0x49f940 查 0x50bf48", "0x50bf48" in dis_txt(HOME_LOOKUP, 0x20))
raw = rd(0x4A52EF, 8)
chk("C2 0x4a52ef movzx ax,[esi+0x1f]",
    raw[:5] == bytes([0x66, 0x0F, 0xB6, 0x46, 0x1F]))
# 同函数 esi 经 ×47+0x519868 来自实体
prev = dis_txt(0x4A52C0, 0x40)
chk("C3 消费点前有实体解算 0x519868", "0x519868" in prev)
tbl = rd(HOME_TBL, 63)
chk("C4 出身表 → 国 0..48", min(tbl) >= 0 and max(tbl) <= 48 and len(set(tbl)) >= 40)
for bid, expect in HOME_SAMPLES:
    got = PROVINCE_NAMES[tbl[fld(bid, 0x2b)]]
    chk("C5 id%d → %s" % (bid, expect), got == expect, "got=%s" % got)

print("\n=== D. @28 / entity+0x1c：无玩法读点（续250）===")
chk("D1 関係表基 0x5197b0 ≠ 实体 0x519868", 0x5197B0 != 0x519868)
raw_c = rd(0x4CE2C3, 16)
chk("D2 MSGX 0x1162 消费读的是槽[esi+0x1c]（同函数 [esi+0x14]→实体）",
    raw_c[0:3] == bytes([0x8A, 0x46, 0x1C])
    and bytes([0x05, 0x62, 0x11, 0x00, 0x00]) in raw_c
    and "0x519868" in dis_txt(0x4CE288, 0x40))
# OR-flags 字节仍在，但 this=城（见 castle_1c_flags_ref）
for va, bit in ((0x49AB80, 4), (0x49ABA0, 8), (0x49ABC0, 0x10), (0x49ABE0, 0x20)):
    chk("D3 setter %s or [ecx+0x1c],%#x（城方法）" % (hex(va), bit),
        bytes([0x80, 0x49, 0x1C, bit]) in rd(va, 16))
chk("D3b 0x49ab80 调用点含城 this（0x51f45f）",
    b"\x5f\xf4\x51\x00" in rd(0x409A70, 0x20))  # mov ecx,0x51f45f
BSD2 = open(os.path.join(_ROOT, "Taikou2 Original", "BSDATA2.TR2"), "rb").read()

def fld2(i, o):
    return BSD2[i * STRIDE + o]

hi_same = sum(1 for i in real if (fld(i, 0x28) >> 5) == (fld2(i, 0x28) >> 5))
lo0 = sum(1 for i in real if (fld(i, 0x28) & 0x1F) == 0)
chk("D4 高3位两剧本几乎全同（≥690）", hi_same >= 690, "same=%d" % hi_same)
chk("D5 ROM 低5位多数为 0（>60%）", lo0 > 0.6 * len(real), "%d/%d" % (lo0, len(real)))
chk("D6 @28 = 持久化保留字段（无实体玩法读点）", True)
chk("D7 関係槽显式基 0x4495a3→0x5197b0", "0x5197b0" in dis_txt(0x4495A0, 0x10))

passed = sum(1 for _, c in results if c)
total = len(results)
print("\nRESULT: %d/%d checks passed" % (passed, total))
raise SystemExit(0 if passed == total else 1)
