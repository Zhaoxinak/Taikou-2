# -*- coding: utf-8 -*-
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
mem = open("scripts/_unpacked_mem.bin", "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

def show(va, n=0xA0):
    print(f"\n==== {va:#x} ====")
    for ins in md.disasm(mem[va - BASE:va - BASE + n], va):
        print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str}")
        if ins.mnemonic.startswith("ret") and ins.address > va + 0x30:
            break

# +0x1c entity consumers
for va in [0x447920, 0x449620, 0x4ce290, 0x4d3b20, 0x4db640,
           0x4be3c0, 0x4d61e0, 0x4ddf10, 0x4e5540, 0x4b45a0,
           0x4cb680, 0x4bd300, 0x4492a0, 0x4d3d20]:
    show(va)

# +0x1f
show(0x4a52c0, 0xC0)

# +0x20 entity
show(0x447940, 0x80)

# check 0x49b9d0 (XOR toggle +0x1c from BREAKTHROUGHS for other struct?)
show(0x49b9d0, 0x40)
