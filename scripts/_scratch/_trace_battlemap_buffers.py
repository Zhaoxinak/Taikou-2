#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find xrefs to the battle-map section buffers (0x512868=B, 0x512b60=C,
0x512e58=A) and disassemble around them to recover the grid stride
(imul by width)."""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
with open(DUMP, "rb") as f:
    data = f.read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

TARGETS = {
    0x512868: "B(terrain)",
    0x512b60: "C(unit)",
    0x512e58: "A(header)",
}

print("=== xrefs (4-byte LE pointers) to section buffers ===")
refs = {k: [] for k in TARGETS}
for va, label in TARGETS.items():
    tgt = struct.pack("<I", va)
    start = 0
    while True:
        i = data.find(tgt, start)
        if i < 0:
            break
        refs[va].append(i + BASE)
        start = i + 1
    print(f"  {label} @0x{va:06x}: {len(refs[va])} refs -> {[hex(r) for r in refs[va][:12]]}")

# For each buffer, disassemble a window BEFORE the first ref to find the
# index/stride computation.
for va, label in TARGETS.items():
    rlist = refs[va]
    if not rlist:
        continue
    r0 = min(rlist)
    lo = r0 - 0x80
    hi = r0 + 0x40
    p0 = lo - BASE
    chunk = data[p0:(hi-BASE)]
    print(f"\n=== {label} @0x{va:06x}  window 0x{lo:06x}..0x{hi:06x} (ref at 0x{r0:06x}) ===")
    for ins in md.disasm(chunk, lo):
        mark = "  <== BUF" if ins.address == r0 else ""
        print(f"  0x{ins.address:06x}: {ins.mnemonic} {ins.op_str}{mark}")
