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
out.append("===== 0x468860 (AI decision candidate) 0x468860..0x4689c0 =====")
out.append(disasm(0x468860, 0x4689c0))
out.append("\n===== 0x469710 (turn init candidate) 0x469710..0x469820 =====")
out.append(disasm(0x469710, 0x469820))
open(r"F:\Games\Taikou 2\scripts\_ai4.txt","w",encoding="utf-8").write("\n".join(out))
print("WROTE _ai4.txt")
