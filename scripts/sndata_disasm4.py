#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Disassemble 0x4eefa0 (enqueue -> writes category key) to assess emulability."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"
with open(IMG, "rb") as f:
    MEM = f.read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def disasm_at(va, n=70, maxb=0x300):
    off = va - BASE
    code = MEM[off:off+maxb]
    print(f"\n===== 0x{va:x} =====")
    cnt = 0
    for ins in md.disasm(code, va):
        print(f"  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}")
        cnt += 1
        if cnt >= n:
            break

disasm_at(0x4eefa0)
