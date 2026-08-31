# -*- coding: utf-8 -*-
"""完整反汇编 0x4169a0-0x416b30 关系变好核心段."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
def rva(p): return p - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

S, E = 0x4169a0, 0x416b30
for ins in md.disasm(mem[rva(S): rva(E)], S):
    a = ins.address
    tag = ""
    if ins.mnemonic == "call": tag = "  <CALL>"
    elif ins.mnemonic == "dec" and "ax" in ins.op_str: tag = "  <DEC变好>"
    elif ins.mnemonic == "inc" and "ax" in ins.op_str: tag = "  <INC恶化>"
    print(f"0x{a:05x}: {ins.mnemonic:9} {ins.op_str}{tag}")
