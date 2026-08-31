# -*- coding: utf-8 -*-
"""Disassemble 0x47ff68 from 0x480120 onward to find the indirect dispatch to
the type-specific handler (the point where our emulation crashes at EIP=0)."""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dis(va, n=90):
    code = IMG[va-BASE: va-BASE+3000]
    out = []
    for i in md.disasm(code, va):
        out.append(i)
        if len(out) >= n:
            break
    return out

print("===== 0x47ff68 from 0x480120 =====")
for i in dis(0x480120, 90):
    s = "%s  %s" % (hex(i.address), i.mnemonic + " " + i.op_str)
    print(s)
    # highlight indirect calls and table reads
    if 'call' in i.mnemonic and ('[' in i.op_str or i.op_str.strip().lower() in ('eax','ecx','edx','ebx','esi','edi')):
        print("      ^^^ INDIRECT CALL")
    if '[' in i.op_str and ('+' in i.op_str or '*' in i.op_str):
        print("      ^^^ memory-indexed read")
