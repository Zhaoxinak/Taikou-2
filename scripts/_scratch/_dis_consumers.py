# -*- coding: utf-8 -*-
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
mem=open("scripts/_unpacked_mem.bin","rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)

def show(va, n=0x90):
    print(f"\n==== {va:#x} ====")
    for ins in md.disasm(mem[va-BASE:va-BASE+n], va):
        print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str}")
        if ins.mnemonic.startswith("ret") and ins.address > va + 0x10:
            break

for va in [0x444240, 0x4aa380, 0x4a7000, 0x47de40, 0x47e050,
           0x4c87e0, 0x445380, 0x44d4e0, 0x4ab520, 0x410dc0,
           0x447970, 0x452fa0, 0x49cf20, 0x4a3e50, 0x46b300]:
    show(va)
