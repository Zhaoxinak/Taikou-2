#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
relation_slots_ref.py — 续249：六槽「関係記録」表 0x5197b0
============================================================
与武将实体池（0x519868×47）**相邻但独立**：

  BASE   = 0x5197b0
  STRIDE = 0x1e (30)
  COUNT  = 6

关键字段（本脚本坐死）：
  +0x14 word  绑定武将索引（0..0x171；≥0x172=空）
  +0x1c byte  **関係噂档** 低 3 bit（0..7）→ MSGX `0x1162+(v&7)`
              （消费：`0x4ce2c3` / `0x4d0576` / `0x4db6a2` / `0x447992`）

解析器：
  `0x4a0050(entity*)` → 在 6 槽中找 `word[+0x14]==entity_index`，返回槽指针或 NULL
  `0x4ce0a0` 扫描 6 槽收集候选

⚠️ **不是** BSDATA stream 0x28 / entity+0x1c（续248/错误归并已纠偏）。
"""
import json
import os
import struct

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(_ROOT, "scripts", "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

TBL = 0x5197B0
STRIDE = 0x1E
COUNT = 6
ENT = 0x519868
FIND = 0x4A0050
MSGX_BANK = 0x1162

results = []


def chk(name, cond, detail=""):
    results.append((name, bool(cond)))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           ("  — " + detail) if detail else ""))


def rd(va, n):
    return MEM[va - BASE:va - BASE + n]


def dis(va, n=0x40):
    return list(md.disasm(rd(va, n), va))


def txt(ins):
    return " | ".join("%s %s" % (i.mnemonic, i.op_str) for i in ins)


print("=== A. 表几何 ===")
chk("A1 表基 0x5197b0 紧挨实体池前", TBL + STRIDE * COUNT + 4 == ENT,
    "tbl_end=%s ent=%s" % (hex(TBL + STRIDE * COUNT), hex(ENT)))
# 0x5197b0 + 6*30 = 0x519864; +4 = 0x519868 ✓
chk("A2 6×30 = 180B", STRIDE * COUNT == 180)
body = txt(dis(FIND, 0x50))
chk("A3 0x4a0050 含 sub eax,0x519868（entity→index）", "0x519868" in body)
chk("A4 0x4a0050 扫 0x5197b0 + add eax,0x1e + cmp cx,6",
    "0x5197b0" in body and "0x1e" in body and "6" in body)

print("\n=== B. +0x14 = 武将索引 ===")
# 0x4a0050: cmp word [eax+0x14], dx
raw = rd(FIND, 0x50)
chk("B1 find 函数 cmp word[eax+0x14]",
    b"\x66\x39\x50\x14" in raw or b"\x66\x3b\x50\x14" in raw
    or "word ptr [eax + 0x14]" in body)
# 0x4ce0a0 scanner
scan = txt(dis(0x4CE0A0, 0x50))
chk("B2 0x4ce0a0 亦 cmp word[eax+0x14], bp(=0x172)",
    "0x14" in scan and "0x172" in scan)

print("\n=== C. +0x1c 低3bit = 関係噂档 → MSGX ===")
# consumer bytes at 0x4ce2c3
raw_c = rd(0x4CE2C3, 16)
chk("C1 0x4ce2c3: mov al,[esi+0x1c]; and eax,7; add eax,0x1162",
    raw_c[0:3] == bytes([0x8A, 0x46, 0x1C])
    and bytes([0x83, 0xE0, 0x07]) in raw_c
    and bytes([0x05, 0x62, 0x11, 0x00, 0x00]) in raw_c)
# 0x4ce2c3 的 esi 来自 0x4ce0a0（槽指针），前有 word[esi+0x14]→entity
prev = txt(dis(0x4CE288, 0x40))
chk("C2 同函数先用 [esi+0x14] 解实体（槽非实体）",
    "0x14" in prev and "0x519868" in prev)
texts = json.load(open(os.path.join(_ROOT, "scripts", "msgx_all_texts.json"),
                       encoding="utf-8"))["texts"]
for i in range(8):
    t = texts[str(MSGX_BANK + i)]
    chk("C3 MSGX %s 非空" % hex(MSGX_BANK + i),
        isinstance(t, str) and len(t) > 10, t[:24])

# 0x447992: arg slot +0x1c &7（ebx=arg，esi=entity）
raw_t = rd(0x447927, 0x80)
chk("C4 0x447927: 从 arg+0x14 解实体到 esi，再读 arg+0x1c &7",
    b"\x66\x8b\x43\x14" in raw_t  # mov ax,[ebx+0x14]
    and b"\x81\xc6\x68\x98\x51\x00" in raw_t  # add esi,0x519868
    and b"\x8a\x5b\x1c" in raw_t  # mov bl,[ebx+0x1c]
    and b"\x83\xe3\x07" in raw_t)  # and ebx,7

print("\n=== D. 与 entity+0x1c / BSDATA@28 切割 ===")
chk("D1 表基 ≠ 实体基", TBL != ENT)
chk("D2 stride 30 ≠ 实体 47", STRIDE != 47)
# entity+0x1c OR setters 存在，但那是另一套
chk("D3 entity OR-flag setter 0x49ab80 仍存在（别对象可能混用）",
    b"\x80\x49\x1c\x04" in rd(0x49AB80, 16))

passed = sum(1 for _, c in results if c)
total = len(results)
print("\nRESULT: %d/%d checks passed" % (passed, total))
raise SystemExit(0 if passed == total else 1)
