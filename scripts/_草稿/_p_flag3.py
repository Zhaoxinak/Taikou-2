# -*- coding: utf-8 -*-
"""Dump all refs to mode_m1(0x511bf8) and battle_type(0x513548) with context,
to locate the battle-init function that sets these flags."""
import os, struct
from _dis_helper import disasm

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()

def find_refs(va):
    pat = struct.pack("<I", va); offs=[]; s=0
    while True:
        i = IMG.find(pat, s)
        if i<0: break
        offs.append(i); s=i+1
    return offs

for va, name in [(0x511bf8,"mode_m1"),(0x513548,"battle_type")]:
    refs = find_refs(va)
    print("=== %s (0x%x) : %d refs ===" % (name, va, len(refs)))
    shown=0
    for off in refs:
        refva = BASE+off
        ctx = list(disasm(refva-0x30, 0x70))
        hit=[r for r in ctx if r["va"]==refva]
        if not hit: continue
        insn=hit[0]
        # only show loads (mov reg, [addr]) or writes
        print("  -- ref @0x%x : %s %s" % (refva, insn["mnem"], insn["ops"]))
        for r in ctx:
            mark=" >>" if r["va"]==refva else "   "
            print("    0x%x %s %s%s" % (r["va"], r["mnem"], r["ops"], mark))
        print()
        shown+=1
        if shown>=3: break
    print()
