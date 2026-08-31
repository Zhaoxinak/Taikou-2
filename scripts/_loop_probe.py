# -*- coding: utf-8 -*-
"""Probe 0x4e8625 (main record loop ①) and 0x4e89cd (②). Print disasm to understand
stack layout passed into 0x47fc60 / 0x47ff68."""
import os, sys, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def disasm(va, size):
    code = IMG[va - BASE: va - BASE + size]
    return [ (va + i, ins.mnemonic, ins.op_str) for i, ins in
             enumerate(md.disasm(code, va)) ]

for TGT, SIZE in ((0x4e8625, 0x300), (0x4e89cd, 0x300)):
    print("\n=== 0x%06x disasm (first %d bytes) ===" % (TGT, SIZE))
    for va, mn, ops in disasm(TGT, SIZE):
        print("0x%06x: %-10s %s" % (va, mn, ops))
