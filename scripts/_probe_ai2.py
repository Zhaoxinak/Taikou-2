#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def va_off(va): return va - BASE

def xref_e8(target_va):
    tg = va_off(target_va)
    out=[]; pos=0
    while True:
        i = MEM.find(bytes([0xe8]), pos)
        if i<0: break
        pos=i+1
        if i+5>len(MEM): continue
        rel=int.from_bytes(MEM[i+1:i+5],"little",signed=True)
        if (i+5)+rel==tg: out.append(BASE+i)
    return out

def disasm(a,b):
    return "\n".join(f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}"
                     for ins in md.disasm(MEM[a-BASE:b-BASE], a))

out=[]
out.append("=== xref to 0x468340 (player turn handler) ===")
for x in xref_e8(0x468340):
    out.append(f"  caller @ 0x{x:08x}")

# other menu_fn callers in duel range
for x in (0x46907e, 0x4691fc, 0x46a93d):
    out.append(f"\n===== disasm around menu_fn caller 0x{x:08x} (0x{x-0x40:08x}..0x{x+0x80:08x}) =====")
    out.append(disasm(x-0x40, x+0x80))

open(r"F:\Games\Taikou 2\scripts\_ai2.txt","w",encoding="utf-8").write("\n".join(out))
print("WROTE _ai2.txt")
