#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recon 4: disassemble pool setters to confirm field layout (esp. byte +4)."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
def gb(va, n): return IMG[va - BASE: va - BASE + n]
def disasm(va, n=0x80, label=''):
    print(f"\n=== {label}  0x{va:x} ===")
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
    for ins in md.disasm(gb(va, n), va):
        print(f"  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}")

for va, lbl in [
    (0x49bfc0, "setFlagsWord(ecx,word) 0x49bfc0"),
    (0x49bff0, "setOwnedBit7(ecx,nonzero) 0x49bff0"),
    (0x49bfe0, "bind_setter(ecx,?) 0x49bfe0"),
    (0x49c030, "getPoolIndex(ecx) 0x49c030"),
]:
    disasm(va, 0x80, lbl)

# also: how is +4 (qty delta) used? search for writes to [ecx+4] near setters
print("\n=== scan for 'mov ... [ecx+4]' / '[ecx+5]' writes near 0x49bf00..0x49c000 ===")
md = Cs(CS_ARCH_X86, CS_MODE_32)
for ins in md.disasm(gb(0x49bf00, 0x300), 0x49bf00):
    s = f"{ins.mnemonic} {ins.op_str}"
    if 'ecx + 4' in s or 'ecx + 5' in s or 'ecx + 6' in s or 'ecx + 8' in s:
        print(f"  0x{ins.address:x}: {s}")
