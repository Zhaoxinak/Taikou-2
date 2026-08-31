# -*- coding: utf-8 -*-
"""Classify writes to the 4 battle mode flags; dump setter context."""
import os, struct
from _dis_helper import disasm

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()

TARGETS = {0x511bf8:"mode_m1",0x51352c:"mode_m2",0x513540:"parity",0x513548:"battle_type",0x513534:"handle_stat_base"}

WRITE_MNEM = {"mov","add","sub","and","or","xor","inc","dec","shl","shr","sal","sar"}

def find_refs(va):
    pat = struct.pack("<I", va); offs=[]; s=0
    while True:
        i = IMG.find(pat, s)
        if i<0: break
        offs.append(i); s=i+1
    return offs

for va, name in TARGETS.items():
    print("=== %s (0x%x) ===" % (name, va))
    nwrite=0
    for off in find_refs(va):
        refva = BASE+off
        # disasm a window containing refva
        ctx = list(disasm(refva-0x18, 0x48))
        hit=None
        for r in ctx:
            if r["va"]==refva: hit=r; break
        if not hit: continue
        iswrite = (hit["mnem"] in WRITE_MNEM) and ("[" in hit["ops"]) and (hit["ops"].split()[0]=="[" or hit["ops"].strip().startswith("byte ptr [") or hit["ops"].strip().startswith("word ptr [") or hit["ops"].strip().startswith("dword ptr ["))
        # crude: write if mnem in WRITE_MNEM and the dst operand is the memory op
        dst_is_mem = False
        ops=hit["ops"]
        if hit["mnem"] in WRITE_MNEM and "[" in ops:
            # e.g. 'mov byte ptr [0x511bf8], al' -> dst is mem
            dst_is_mem = True
        if not dst_is_mem:
            continue
        nwrite+=1
        if nwrite<=12:
            for r in ctx:
                mark=" >>" if r["va"]==refva else "   "
                print("  0x%x %s %s%s" % (r["va"], r["mnem"], r["ops"], mark))
            print()
    print("  total writes: %d\n" % nwrite)
