# -*- coding: utf-8 -*-
"""Disassemble 0x47fc60 entry to find how the record type is read and the
type-switch is structured (the gateway to per-type payload decode)."""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def dis(va, n=160):
    code = IMG[va-BASE: va-BASE+8000]
    out = []
    for i in md.disasm(code, va):
        out.append(i)
        if len(out) >= n:
            break
    return out

print("===== 0x47fc60 entry (first 160 insns) =====")
for i in dis(0x47fc60, 160):
    s = "%s  %s" % (hex(i.address), i.mnemonic + " " + i.op_str)
    # highlight control flow + type-ish compares
    if i.mnemonic in ('cmp','test','je','jne','jmp','ja','jb','jg','jl','jae','jbe'):
        s += "   <-- CTRL"
    if '522c' in i.op_str or '509' in i.op_str:
        s += "   <-- PAYLOAD/BUF"
    print(s)
