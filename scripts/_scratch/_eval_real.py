#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find real consumers of eval-word table 0x50b6ba (stride 9)."""
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
out = open("scripts/_scratch/_eval_real.txt", "w", encoding="utf-8")

# 1) Any absolute ref to addresses inside the 24*9 table
TBL = 0x50B6BA
END = TBL + 24 * 9
abs_hits = []
for va in range(TBL, END):
    needle = struct.pack("<I", va)
    st = 0
    while True:
        j = code.find(needle, st)
        if j < 0:
            break
        abs_hits.append((BASE + j, va))
        st = j + 1
out.write(f"abs refs into table: {len(abs_hits)}\n")
for h, v in abs_hits[:40]:
    out.write(f"  code@{h:#x} -> {v:#x} (off {v-TBL})\n")
    for i in md.disasm(code[h - BASE - 0x10 : h - BASE + 0x20], h - 0x10):
        out.write(f"    {i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")

# 2) Search for imul/lea *9 patterns near add 0x50b6ba
# lea r,[r+r*8] = 8d xx xx with SIB scale 8
# Then +r = *9

def dump(va, n, title=""):
    out.write(f"\n=== {title or hex(va)} ===\n")
    for i in md.disasm(code[va - BASE : va - BASE + n], va):
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")


# 3) Decode words at 0x50ce78 family (used by 4d0e80) to confirm NOT eval
out.write("\n=== 0x50ce78 word table dump ===\n")
for off in range(0, 0x40, 2):
    w = struct.unpack_from("<H", code, 0x50CE78 - BASE + off)[0]
    out.write(f"  [{off:#x}] = {w} ({w:#x})\n")

# 4) Find functions that contain both "缺乏" bytes nearby in data refs
# Search wrappers: known from eval_word docs - 5 access wrappers with 0 e8 callers
# Grep BREAKTHROUGHS for wrapper addresses
# Search for mov reg, 0x50b6ba as push/mov imm32 anywhere including data section as vtable

# Scan for *9: imul reg, reg, 9 = 6b xx 09
hits9 = []
st = 0
while True:
    j = code.find(b"\x6b", st)  # imul r, r/m, imm8
    if j < 0:
        break
    if j + 3 <= len(code) and code[j + 2] == 9:
        # verify via disasm
        for i in md.disasm(code[j : j + 8], BASE + j):
            if i.mnemonic == "imul" and "0x9" in i.op_str:
                hits9.append(BASE + j)
            break
    st = j + 1
out.write(f"\nimul *9 sites: {len(hits9)}\n")
for h in hits9:
    # check if nearby has 0x50b6ba or 0xb6ba
    window = code[h - BASE - 0x40 : h - BASE + 0x40]
    near = b"\xba\xb6\x50" in window or b"\xb6\xba" in window
    out.write(f"  {h:#x} near_tbl={near}\n")
    if near or True:
        dump(h - 0x30, 0x60, f"imul9 @{h:#x}")

# 5) lea reg,[reg+reg*8] then add reg,reg (=*9) then add 0x50b6ba
# Pattern harder; search add/mov with 0x50b6ba displacement variants

# Search GBK first word of each group as standalone and see code xrefs to those VAs
for gi, name in enumerate(["缺乏", "低", "缺乏", "薄弱", "缺乏", "缺少", "稚嫩", "低"]):
    # already know addresses
    pass

# Dump first bytes of eval table and find ANY code that reads byte from computed
# Look for known wrapper VAs from continuations - search "0x4" near eval in scripts
out.write("\n=== search scripts mentions ===\n")

out.close()
print("abs", len(abs_hits), "imul9", len(hits9))
