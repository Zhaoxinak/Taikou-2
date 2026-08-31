# -*- coding: utf-8 -*-
"""Probe 0x47ff68 (record-type dispatcher). Print disasm + locate jump/dispatch table."""
import os, sys, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
DISP = 0x47ff68
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def disasm(va, size):
    code = IMG[va - BASE: va - BASE + size]
    return [ (va + i, ins.mnemonic, ins.op_str) for i, ins in
             enumerate(md.disasm(code, va)) ]

# Disassemble a generous window
SIZE = 0x900
print("=== 0x47ff68 disasm (first %d bytes) ===" % SIZE)
for va, mn, ops in disasm(DISP, SIZE):
    print("0x%06x: %-10s %s" % (va, mn, ops))
