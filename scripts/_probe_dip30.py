# -*- coding: utf-8 -*-
"""dump 外交成败判定函数 0x47bed0(友好) 与 0x47b5f0(高压), 找 RNG(0x4ebd30) 比较."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
def rva(p): return p - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dump(a, b, label):
    print(f"\n### {label} (0x{a:x}-0x{b:x})")
    for ins in md.disasm(mem[rva(a): rva(b)], a):
        mark = ""
        if ins.mnemonic == "call":
            mark = "  <CALL>"
            if ins.op_str == "0x4ebd30":
                mark += "  <<< RNG(LCG)"
        print(f"0x{ins.address:05x}: {ins.mnemonic:9} {ins.op_str}{mark}")

dump(0x47bed0, 0x47c040, "0x47bed0 友好外交成败判定")
dump(0x47b5f0, 0x47b8a0, "0x47b5f0 高压外交成败判定")
