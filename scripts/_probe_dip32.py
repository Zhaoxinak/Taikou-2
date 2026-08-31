# -*- coding: utf-8 -*-
"""dump 友好外交成败判定核心 0x47be00-0x47bee0, 找 RNG(0x4ebd30) 与比较."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
def rva(p): return p - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

print("### 0x47be00 友好外交成败判定核心")
for ins in md.disasm(mem[rva(0x47be00): rva(0x47bee0)], 0x47be00):
    mark = ""
    if ins.mnemonic == "call":
        mark = f"  <CALL 0x{int(ins.op_str,16):x}>"
        if ins.op_str == "0x4ebd30":
            mark += "  <<< RNG(LCG)"
    elif "0x4ebd30" in ins.op_str:
        mark = "  <RNG ref>"
    print(f"0x{ins.address:05x}: {ins.mnemonic:9} {ins.op_str}{mark}")
