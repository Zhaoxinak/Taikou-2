"""Disassemble the generic LZW->object loader 0x433780 and the init chain
that calls it with HKMAP/HJMAP/HJCHAR/HGRP, to recover the object struct
layout (esp. the palette field) for true-color rendering."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
data = open("_unpacked_mem.bin", "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def off_of(va): return va - BASE

def disasm(va, n):
    chunk = data[off_of(va): off_of(va)+n]
    out = []
    for ins in md.disasm(chunk, va):
        out.append(ins)
    return out

# The loader 0x433780; disassemble a generous window.
print("================ LOADER 0x433780 ================")
for ins in disasm(0x433780, 0x500):
    s = f"0x{ins.address:06x}: {ins.mnemonic} {ins.op_str}"
    print(s)
