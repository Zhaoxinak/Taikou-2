# -*- coding: utf-8 -*-
"""Disassemble 0x47fc60 (the real per-record fan-out + per-type decoder) and
surface the interesting structure: references to the payload bases
(0x522c88 / 0x522c60 / 0x522c70), indirect calls (type-handler dispatch),
and `cmp` against small immediates (type switch)."""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def dis(va, n=3000):
    code = IMG[va-BASE: va-BASE+60000]
    out = []
    for i in md.disasm(code, va):
        out.append(i)
        if len(out) >= n:
            break
    return out

insns = dis(0x47fc60, 3000)
print("0x47fc60 total insns in window: %d, last addr %s" % (len(insns), hex(insns[-1].address)))

INTEREST = []
for i in insns:
    s = i.mnemonic + " " + i.op_str
    if ('522c88' in s or '522c60' in s or '522c70' in s or
        '509' in s or '520' in s or '51e' in s):
        INTEREST.append((i.address, s, 'PAYLOAD/BUF'))
    elif i.mnemonic in ('call',) and ('[' in i.op_str or i.op_str.strip().lower() in
            ('eax','ecx','edx','ebx','esi','edi','ebp')):
        INTEREST.append((i.address, s, 'INDIRECT'))
    elif i.mnemonic == 'cmp' and i.op_str.split(',')[-1].strip().startswith('0x'):
        val = int(i.op_str.split(',')[-1].strip(), 16)
        if val < 0x200:
            INTEREST.append((i.address, s, 'CMP'))

print("\n===== INTERESTING (payload/base/indirect/cmp) =====")
for (a, s, tag) in INTEREST:
    print("  [%s] %s  %s" % (tag, hex(a), s))
