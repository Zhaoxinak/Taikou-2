# -*- coding: utf-8 -*-
"""dump 0x49a400..0x49a800 取值器簇, 找寿命/死亡/登场相关 getter。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

o = 0x49A400 - BASE
cur = None
for ins in md.disasm(mem[o:o + 0x420], 0x49A400):
    if ins.mnemonic == "ret":
        print(f"  {ins.address:08x}  {ins.mnemonic:<6} {ins.op_str}")
        print()
        cur = None
        continue
    print(f"  {ins.address:08x}  {ins.mnemonic:<6} {ins.op_str}")
