# -*- coding: utf-8 -*-
"""Disassemble the main record loop 0x4e8625 to find how it selects the
per-type decoder after calling the loader 0x47fc60. Look for 0x4fb09c writes,
type tables, and indirect dispatch."""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def dis(va, n=260):
    code = IMG[va-BASE: va-BASE+12000]
    out = []
    for i in md.disasm(code, va):
        out.append(i)
        if len(out) >= n:
            break
    return out

print("===== 0x4e8625 (first 260 insns) =====")
for i in dis(0x4e8625, 260):
    s = "%s  %s" % (hex(i.address), i.mnemonic + " " + i.op_str)
    tag = ''
    if '4fb09c' in s: tag += '  <<<4fb09c'
    if '522c' in s: tag += '  <<<PAYLOAD'
    if '509' in s or '520' in s: tag += '  <<<BUF'
    if i.mnemonic in ('cmp','test','je','jne','jmp','ja','jb','jg','jl','jae','jbe','call'):
        tag += '  CTRL'
    if tag:
        print("  "+s+tag)
