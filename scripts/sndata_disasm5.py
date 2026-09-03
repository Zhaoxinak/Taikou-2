#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Disassemble the enqueue comparison internals to find the static category table."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"
with open(IMG, "rb") as f:
    MEM = f.read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def disasm_at(va, n=60, maxb=0x200):
    off = va - BASE
    code = MEM[off:off+maxb]
    print(f"\n===== 0x{va:x} =====")
    cnt = 0
    for ins in md.disasm(code, va):
        print(f"  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}")
        cnt += 1
        if cnt >= n:
            break

for va in (0x4eefe0, 0x4ef030, 0x4ef120, 0x4ef1c0, 0x4ee7b0, 0x4ee830):
    disasm_at(va)
