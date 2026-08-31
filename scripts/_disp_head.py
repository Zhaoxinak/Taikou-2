# -*- coding: utf-8 -*-
"""Disassemble the entry of 0x47ff68 to learn how the record type is obtained
(because all non-zero probe types produced identical traces, the type is
likely read from state the stubbed fan-out 0x47fc60 should have set up)."""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dis(va, n=80):
    code = IMG[va-BASE: va-BASE+2000]
    out = []
    for i in md.disasm(code, va):
        out.append(i)
        if len(out) >= n:
            break
    return out

print("===== 0x47ff68 entry =====")
for i in dis(0x47ff68, 70):
    # annotate esp-relative reads
    s = "%s  %s" % (hex(i.address), i.mnemonic + " " + i.op_str)
    print(s)
