# -*- coding: utf-8 -*-
"""Find setter functions (writes) for the 4 battle mode flags + handle_stat.
Scan unpacked image for the global-address immediates, then disassemble
the instruction that references each, to learn the setter context.
mode_m1=0x511bf8  mode_m2=0x51352c  parity=0x513540  battle_type=0x513548  handle_stat base=0x513534(+0xd=0x513541?)
"""
import os, struct
from _dis_helper import disasm

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
LEN = len(IMG)

TARGETS = {
    0x511bf8: "mode_m1",
    0x51352c: "mode_m2",
    0x513540: "parity",
    0x513548: "battle_type",
    0x513534: "handle_stat_base",
}

def find_refs(va):
    pat = struct.pack("<I", va)
    offs = []
    start = 0
    while True:
        i = IMG.find(pat, start)
        if i < 0:
            break
        offs.append(i)
        start = i + 1
    return offs

for va, name in TARGETS.items():
    refs = find_refs(va)
    print("=== %s (0x%x) : %d raw refs ===" % (name, va, len(refs)))
    seen_funcs = set()
    for off in refs[:40]:
        refva = BASE + off
        # disassemble a small window ending at refva to see the referencing insn + function head
        # search backward for a 'ret' or function boundary is hard; just show +/- a few insns
        for r in disasm(refva - 0x20, 0x40):
            if r["va"] == refva:
                # print this insn and a couple around
                pass
        # simpler: disasm 8 insns around
        ctx = list(disasm(refva - 0x10, 0x30))
        # find the one whose va==refva
        for r in ctx:
            mark = " >>" if r["va"] == refva else "   "
            print("  0x%x %s %s%s" % (r["va"], r["mnem"], r["ops"], mark))
        # function head ~ look back for 'push ebp'/'sub esp' within 0x80
        break  # only first ref detail to avoid flood; we'll aggregate callers below
    print()
