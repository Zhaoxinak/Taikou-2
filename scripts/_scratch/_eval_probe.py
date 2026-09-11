#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe eval-word draw loop 0x47ca70 and threshold site 0x4d0e10."""
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
out = open("scripts/_scratch/_eval_probe.txt", "w", encoding="utf-8")


def dump(va, n, title=""):
    out.write(f"\n=== {title or hex(va)} ===\n")
    for i in md.disasm(code[va - BASE : va - BASE + n], va):
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")


dump(0x47CA70, 0x200, "47ca70 draw")
dump(0x4D0E10, 0x200, "4d0e10 thresholds")

# find cmp imm near 0x4d0e10 and 0x47ca70
out.write("\n=== interesting cmps in 0x4d0e10..0x4d1200 ===\n")
for i in md.disasm(code[0x4D0E10 - BASE : 0x4D1200 - BASE], 0x4D0E10):
    if i.mnemonic == "cmp" and any(
        x in i.op_str for x in ("0x28", "0x37", "0x3c", "0x50", "0x64", "0x708", "0x7d0", "0xbb8", "40", "55", "60", "80")
    ):
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")

# xref 0x50b6ba
needle = struct.pack("<I", 0x50B6BA)
st = 0
hits = []
while True:
    j = code.find(needle, st)
    if j < 0:
        break
    hits.append(BASE + j)
    st = j + 1
out.write(f"\nxrefs 0x50b6ba: {len(hits)} {[hex(h) for h in hits[:20]]}\n")
for h in hits[:12]:
    dump(h - 0x20, 0x50, f"xref@{h:#x}")

out.close()
print("ok", len(hits))
