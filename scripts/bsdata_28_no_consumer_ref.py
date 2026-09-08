#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bsdata_28_no_consumer_ref.py — BSDATA @28 / entity+0x1c 无玩法读点（续250）
================================================================================
结论：
  1. 所有「读 [reg+0x1c] & 7 → MSGX」链的 this 是 **六槽関係表**（经 `0x4a0050`
     或显式 `0x5197b0+idx*30`），不是实体。
  2. OR-flag setters `0x49ab80..e0` 的 this 是 **城**（见 castle_1c_flags_ref）。
  3. 实体侧：序列化器读写 `word[+0x1b]`（低=生年，高=@28），但静态穷举下
     **无**把 entity+0x1c 当数值/位域做玩法判定的消费者。
  ⇒ `@28` = **持久化保留字段**（高3静态/低5剧本相关位域仍成立），玩法名
     **结论性不可再静态命名**（非开放结构孔）。

运行：`python scripts/bsdata_28_no_consumer_ref.py` → RESULT n/n
"""
from __future__ import annotations

import os
import struct

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

_HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(_HERE, "_unpacked_mem.bin"), "rb").read()
ENT, REL, CASTLE = 0x519868, 0x5197B0, 0x51EB88
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
results = []


def chk(name, cond, detail=""):
    results.append((name, bool(cond)))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           (" — " + detail) if detail else ""))


def rd(va, n):
    return MEM[va - BASE:va - BASE + n]


def dis(va, n=0x50):
    return " | ".join("%s %s" % (i.mnemonic, i.op_str)
                      for i in md.disasm(rd(va, n), va))


print("=== A. 典型 &7 读点 = 関係槽 ===")
# 0x4495a3 lea edi, [eax*2 + 0x5197b0]; later [edi+0x1c]&7
chk("A1 0x4495a3 显式基 = 0x5197b0", "0x5197b0" in dis(0x4495A0, 0x10))
chk("A2 0x449656 and eax,7 读 [edi+0x1c]",
    rd(0x449656, 6)[:3] == bytes([0x8A, 0x47, 0x1C])
    and b"\x83\xe0\x07" in rd(0x449656, 12))
# 0x4a0050 finder → slot
chk("A3 0x4d3b59 call 0x4a0050 后读 [edi+0x1c]",
    "0x4a0050" in dis(0x4D3B50, 0x20)
    and rd(0x4D3B76, 3) == bytes([0x8A, 0x5F, 0x1C]))
# 0x4ce2c3 MSGX 1162
chk("A4 0x4ce2c3 → MSGX 0x1162+n（関係噂）",
    b"\x05\x62\x11\x00\x00" in rd(0x4CE2C3, 16))

print("\n=== B. OR-setters this ≠ 实体池基址 ===")
# none of the fixed-ecx clear sites equal ENT+k*47
fixed = (0x51F45F, 0x51F8F9, 0x51F7E2)
for va in fixed:
    chk("B1 %#x 对齐城 stride31" % va, (va - CASTLE) % 31 == 0)
    chk("B2 %#x 不是实体" % va, (va - ENT) % 47 != 0 or va < ENT)

print("\n=== C. 实体序列化仍读写 word[+0x1b]（含 @28 高字节）===")
chk("C1 serializer 0x47e068 mov cx,[edi+0x1b]",
    "word ptr [edi + 0x1b]" in dis(0x47E068, 0x10))
chk("C2 无 mov [reg+0x1c],al 实体装载直写（高字节随 word 走）",
    b"\x88\x47\x1c" not in MEM and b"\x88\x46\x1c" not in MEM)

print("\n=== D. 假阳性：ENT 邻域 +0x1c 实为槽 ===")
# 0x447927 word[ebx+0x14] — slot field, then [ebx+0x1c]
chk("D1 0x447927 cmp [ebx+0x14],0x172（槽武将索引）",
    "0x172" in dis(0x447927, 0x10))
chk("D2 同函数后 [ebx+0x1c]&7",
    rd(0x447992, 3) == bytes([0x8A, 0x5B, 0x1C])
    and b"\x83\xe3\x07" in rd(0x447992, 16))

passed = sum(1 for _, c in results if c)
total = len(results)
print("\nRESULT: %d/%d checks passed" % (passed, total))
raise SystemExit(0 if passed == total else 1)
