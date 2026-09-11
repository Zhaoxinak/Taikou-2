#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hunt eval-word consumers: thresholds + group index."""
from __future__ import annotations

import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(r"F:\Games\Taikou 2")

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

code = open("scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
out = open("scripts/_scratch/_eval_deep.txt", "w", encoding="utf-8")

# Search lea/add involving 0x50b6ba parts: stride 9 = lea reg,[reg+reg*8]
# Or push 0x50b6ba as 2 parts
# Also search for string "缺乏" GBK
lack = "缺乏".encode("gbk")
rich = "丰富".encode("gbk")
out.write(f"lack={lack.hex()} hits={code.count(lack)}\n")
# table itself
out.write(f"table at file: {(0x50b6ba-BASE):#x} raw={code[0x50b6ba-BASE:0x50b6ba-BASE+27]}\n")

# Find functions that cmp with known thresholds from SPEC
THRESH = [40, 55, 60, 80, 1800, 2000, 3000]
# Scan 0x4d0000-0x4d2000 for cmp sequences
out.write("\n=== cmps in 0x4d0c00..0x4d1400 ===\n")
for i in md.disasm(code[0x4D0C00 - BASE : 0x4D1400 - BASE], 0x4D0C00):
    if i.mnemonic in ("cmp", "ja", "jae", "jb", "jbe", "jg", "jge", "jl", "jle"):
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")

out.write("\n=== 0x47ca70 full ===\n")
for i in md.disasm(code[0x47CA70 - BASE : 0x47CC80 - BASE], 0x47CA70):
    out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")

# Who calls 0x47ca70?
hits = []
for i in range(len(code) - 5):
    if code[i] != 0xE8:
        continue
    rel = struct.unpack_from("<i", code, i + 1)[0]
    if BASE + i + 5 + rel == 0x47CA70:
        hits.append(BASE + i)
out.write(f"\ncallers 0x47ca70: {len(hits)} {[hex(h) for h in hits]}\n")
for h in hits[:8]:
    out.write(f"\n-- caller {h:#x} --\n")
    for i in md.disasm(code[h - 0x40 - BASE : h + 0x20 - BASE], h - 0x40):
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")

# Search imm 0x50b6ba as add/lea
# Also 0xb6ba as word?
for pat, name in [
    (struct.pack("<I", 0x50B6BA), "abs50b6ba"),
    (struct.pack("<I", 0x50B6B0), "near"),
    (struct.pack("<H", 0xB6BA), "b6ba"),
]:
    st = 0
    n = 0
    locs = []
    while True:
        j = code.find(pat, st)
        if j < 0:
            break
        locs.append(BASE + j)
        n += 1
        st = j + 1
        if n > 30:
            break
    out.write(f"{name}: {n} { [hex(x) for x in locs[:15]] }\n")

out.close()
print("written")
