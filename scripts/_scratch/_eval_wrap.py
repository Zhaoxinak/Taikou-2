#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Map 8 eval-word wrappers + tier source 0x4b1270 + thresholds."""
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
out = open("scripts/_scratch/_eval_wrap.txt", "w", encoding="utf-8")


def dump(va, n, title=""):
    out.write(f"\n=== {title or hex(va)} ===\n")
    for i in md.disasm(code[va - BASE : va - BASE + n], va):
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")
        if i.mnemonic == "ret" and i.address > va + 8:
            break


# Find all lea ..., [reg+reg*8+0x50b6xx]
wrappers = []
for off in range(len(code) - 7):
    # 8D xx SIB disp32 where SIB = reg + reg*8
    if code[off] != 0x8D:
        continue
    modrm = code[off + 1]
    if (modrm & 0xC7) != 0x84:  # mod=10, r/m=100 (SIB+disp32) roughly — check SIB
        # actually lea r32, [r+r*8+disp32]: modrm = 0x84|reg<<3, sib = 0xC0|scale_idx...
        pass
    sib = code[off + 2] if off + 2 < len(code) else 0
    # scale=8 => sib bits 6-7 = 11b = 0xC0
    if (sib & 0xC0) != 0xC0:
        continue
    if off + 7 > len(code):
        continue
    disp = struct.unpack_from("<I", code, off + 3)[0]
    if 0x50B6BA <= disp <= 0x50B6BA + 24 * 9 + 9:
        wrappers.append(BASE + off)

out.write(f"lea*9 hits: {len(wrappers)} {[hex(w) for w in wrappers]}\n")

# Walk back to function start for each
for lea_va in wrappers:
    # walk back up to 0x80 for push/ prologue after ret/nop
    start = lea_va
    for back in range(4, 0x100):
        b = code[lea_va - BASE - back]
        if b == 0xCC or (b == 0xC3 and back > 10):
            start = lea_va - back + 1
            break
        if b == 0x90 and code[lea_va - BASE - back + 1 : lea_va - BASE - back + 4] == b"\x90\x90\x90":
            start = lea_va - back + 1
            # continue to find first non-nop
    # better: find previous ret
    start = lea_va - 0x60
    for back in range(0x10, 0xA0):
        if code[lea_va - BASE - back] == 0xC3:
            # next non-nop
            s = lea_va - back + 1
            while code[s - BASE] == 0x90:
                s += 1
            start = s
            break
    dump(start, lea_va - start + 0x30, f"wrapper lea@{lea_va:#x} start@{start:#x}")

# Dump 0x4b1270 - tier calculator?
dump(0x4B1270, 0x120, "4b1270 tier?")

# Callers of each wrapper function
out.write("\n=== caller scan for wrapper funcs ===\n")
# From disasm, wrappers seem to be at ~0x497xxx / 0x498xxx
# Find e8 to those starts - collect starts from dumps by re-parsing

# Decode what each displacement points to
out.write("\n=== displacement → string ===\n")
for lea_va in wrappers:
    # find disp in instruction
    off = lea_va - BASE
    disp = struct.unpack_from("<I", code, off + 3)[0]
    # for esi=0,1,2 show strings
    for tier in range(3):
        va = disp + tier * 9
        raw = code[va - BASE : va - BASE + 9]
        s = raw.split(b"\x00")[0].decode("gbk", "ignore").replace(" ", "").replace("\u3000", "")
        out.write(f"  lea@{lea_va:#x} disp={disp:#x} tier{tier} @{va:#x}: {s!r} raw={raw.hex()}\n")

# Also check 0x4b16d0
dump(0x4B16D0, 0x40, "4b16d0 set text")

out.close()
print("wrappers", len(wrappers))
