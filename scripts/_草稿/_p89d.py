# -*- coding: utf-8 -*-
"""_p89d.py — dump 0x43c000 (multi-flag values) + 0x42b000 (battle-start entry) + callers of 0x42b000"""
import pickle, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
IMG = open("_unpacked_mem.bin", "rb").read(); BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True

def dump(va, n):
    print("==== 0x%x (%d bytes) ====" % (va, n))
    for r in md.disasm(IMG[va - BASE: va - BASE + n], va):
        print("  0x%x:\t%s\t%s" % (r.address, r.mnemonic, r.op_str))

def callers_of(target, win=0x1000):
    hits = []
    for va in range(BASE, BASE + len(IMG), win):
        code = IMG[va - BASE: va - BASE + win]
        for r in md.disasm(code, va):
            if r.mnemonic == "call":
                try: t = int(r.op_str, 16)
                except Exception: continue
                if t == target: hits.append(va)
    return hits

print("##### 0x43c000 multi-flag setter (full) #####")
dump(0x43c000, 0x320)
print()
print("callers of 0x42b000:", [hex(x) for x in callers_of(0x42b000)])
print()
print("##### 0x42b000 battle-start entry #####")
dump(0x42b000, 0x260)
