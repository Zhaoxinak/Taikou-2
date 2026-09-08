#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
castle_1c_flags_ref.py — 城种 word[+0x1b] 高位 / +0x1c OR-flags（续250）
================================================================================
纠偏：`0x49ab80/a0/c0/e0` 的 this 是**城**（`0x51eb88` 族），不是武将实体。
它们操作的是城种 word 的高字节（= `byte[+0x1c]`），与 BSDATA `@28`/entity+0x1c **无关**。

| bit (byte+0x1c) | word bit | 定名 | 证据 |
|---|---|---|---|
| bit2 (0x04) | 10 (0x400) | **重视军备**（0=内政 / 1=军备） | `0x4e3d21` → 名表 `0x50d628`；MSGX 0x11ab/0x11ac |
| bit3 (0x08) | 11 | **筑城中** | SET 紧邻筑城 MSG；门控 `0x4b45c3` · 续251 |
| bit4 (0x10) | 12 | **开垦中** | 开垦入口门控 `0x4c92d3`；分派 idx==4 · 续251 |
| bit5 (0x20) | 13 | **築城済** | setter `0x49abe0` ← 筑城 handler `0x4ab530` |

运行：`python scripts/castle_1c_flags_ref.py` → RESULT n/n
"""
from __future__ import annotations

import os
import struct

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
BASE = 0x400000
MEM = open(os.path.join(_HERE, "_unpacked_mem.bin"), "rb").read()
CASTLE = 0x51EB88
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
results = []


def chk(name, cond, detail=""):
    results.append((name, bool(cond)))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           (" — " + detail) if detail else ""))


def rd(va, n):
    return MEM[va - BASE:va - BASE + n]


def dis(va, n=0x40):
    return " | ".join("%s %s" % (i.mnemonic, i.op_str)
                      for i in md.disasm(rd(va, n), va))


def callers(target):
    out = []
    for i in range(len(MEM) - 5):
        if MEM[i] != 0xE8:
            continue
        rel = int.from_bytes(MEM[i + 1:i + 5], "little", signed=True)
        if BASE + i + 5 + rel == target:
            out.append(BASE + i)
    return out


print("=== A. Setter 字节 + 清位用 word[+0x1b] ===")
for va, bit, wmask in (
    (0x49AB80, 0x04, 0xFBFF),
    (0x49ABA0, 0x08, 0xF7FF),
    (0x49ABC0, 0x10, 0xEFFF),
    (0x49ABE0, 0x20, 0xDFFF),
):
    body = rd(va, 0x18)
    chk("A1 %s or [ecx+0x1c],%#x" % (hex(va), bit),
        bytes([0x80, 0x49, 0x1C, bit]) in body)
    chk("A2 %s clear word[+0x1b] &%#x" % (hex(va), wmask),
        struct.pack("<H", wmask) in body[8:18] or ("0x%x" % wmask).lower() in dis(va, 0x20).lower())

print("\n=== B. this = 城（非实体）===")
# fixed castle indices in clear-all event paths
for va, idx in ((0x51F45F, 73), (0x51F8F9, 111), (0x51F7E2, 102)):
    chk("B1 %#x = castle[%d]" % (va, idx), (va - CASTLE) % 31 == 0 and (va - CASTLE) // 31 == idx)
# 0x4e3dd4: esi castle + call bit2 setter
chk("B2 0x4e3dd4 call 0x49ab80 前有 CASTLE 解算",
    "0x51eb88" in dis(0x4E3DA0, 0x40) and "0x49ab80" in dis(0x4E3DC0, 0x20))
# 築城済
chk("B3 0x4ab59a call 0x49abe0（筑城→築城済）",
    0x4AB59A in callers(0x49ABE0))

print("\n=== C. bit2 = 内政/军备 ===")
names = rd(0x50D628, 10)
n0 = names[0:5].split(b"\x00")[0].decode("gbk", "replace")
n1 = names[5:10].split(b"\x00")[0].decode("gbk", "replace")
chk("C1 名表 0x50d628 = 内政/军备", n0 == "内政" and n1 == "军备", "%s/%s" % (n0, n1))
# 0x4e3d21: word[+0x1b] >> 10 & 1 → index into table
chk("C2 0x4e3d21 shr 0xa + lea ..+0x50d628",
    "shr" in dis(0x4E3D21, 0x20) and "0x50d628" in dis(0x4E3D21, 0x20))
chk("C3 MSGX 0x11ab / 0x11ac push 存在",
    b"\x68\xab\x11\x00\x00" in rd(0x4E3CC0, 0x80) or b"\x68\xac\x11\x00\x00" in rd(0x4E3D20, 0x30))

print("\n=== D. 调用点计数（非零）===")
for va, name, lo, hi in (
    (0x49AB80, "bit2", 5, 8),
    (0x49ABA0, "bit3", 8, 15),
    (0x49ABC0, "bit4", 5, 10),
    (0x49ABE0, "bit5", 1, 3),
):
    n = len(callers(va))
    chk("D %s callers in [%d,%d]" % (name, lo, hi), lo <= n <= hi, "n=%d" % n)

passed = sum(1 for _, c in results if c)
total = len(results)
print("\nRESULT: %d/%d checks passed" % (passed, total))
raise SystemExit(0 if passed == total else 1)
