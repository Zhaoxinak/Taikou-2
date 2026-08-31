#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def disasm(a,b):
    return "\n".join(f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}"
                     for ins in md.disasm(MEM[a-BASE:b-BASE], a))

out=[]
out.append("===== duel main loop around xref 0x469887/0x469892 (0x4697c0..0x4699c0) =====")
out.append(disasm(0x4697c0, 0x4699c0))
open(r"F:\Games\Taikou 2\scripts\_ai3.txt","w",encoding="utf-8").write("\n".join(out))
print("WROTE _ai3.txt")
