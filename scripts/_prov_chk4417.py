#!/usr/bin/env python3
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BIN = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
data = open(BIN,"rb").read()
def off(va): return va-BASE
cs = Cs(CS_ARCH_X86, CS_MODE_32); cs.detail=True
va=0x441780
code=data[off(va):off(va)+0x60]
for ins in cs.disasm(code, va):
    print(f"{ins.address:#08x}  {ins.mnemonic} {ins.op_str}")
