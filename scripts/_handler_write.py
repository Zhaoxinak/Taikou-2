# -*- coding: utf-8 -*-
"""Disassemble around VA 0x47fae4 (a code reference to 0x4fb09c) to find the
per-type handler assignment. Also scan a window for any instruction that writes
to 0x4fb09c (store into that address)."""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def dis(va, n=80):
    code = IMG[va-BASE: va-BASE+3000]
    out = []
    for i in md.disasm(code, va):
        out.append(i)
        if len(out) >= n:
            break
    return out

print("===== around 0x47fae4 =====")
for i in dis(0x47fa60, 80):
    s = "%s  %s" % (hex(i.address), i.mnemonic + " " + i.op_str)
    if '4fb09c' in s:
        s += "   <<< 4fb09c"
    if i.mnemonic in ('cmp','test','je','jne','jmp','ja','jb','jg','jl','jae','jbe','call'):
        s += "   CTRL"
    print(s)
