# -*- coding: utf-8 -*-
"""List all call targets inside 0x47ff68 to enumerate stub requirements."""
import os, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
DISP = 0x47ff68
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

code = IMG[DISP - BASE: DISP - BASE + 0x6000]
targets = {}
for ins in md.disasm(code, DISP):
    if ins.mnemonic == 'call':
        t = ins.op_str.strip().lower()
        if t.startswith('0x'):
            targets[int(t, 16)] = targets.get(int(t, 16), 0) + 1

print("Call targets inside 0x47ff68 (%d unique):" % len(targets))
for t, c in sorted(targets.items()):
    print("  0x%06x  x%d" % (t, c))
