# -*- coding: utf-8 -*-
"""Disassemble 0x4e8625 fully and find calls to 0x47ff68 / 0x47fc60 / indirect calls."""
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

import os, sys, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def disasm(va, size):
    code = IMG[va - BASE: va - BASE + size]
    return [ (va + i, ins.mnemonic, ins.op_str) for i, ins in
             enumerate(md.disasm(code, va)) ]

lines = disasm(0x4e8625, 0x900)
print("Total insns:", len(lines))
# show all call targets and any reference to 47ff68 / 47fc60
for va, mn, ops in lines:
    up = ops.upper()
    if mn == 'call' and ('47FF68' in up or '47FC60' in up):
        print(">>> DISPATCH/FANOUT CALL at 0x%06x: %s %s" % (va, mn, ops))
    if mn == 'call' and not ops.startswith('0x'):
        print("    indirect call at 0x%06x: %s %s" % (va, mn, ops))
    if '47FF68' in up or '47FC60' in up:
        print("    ref at 0x%06x: %s %s" % (va, mn, ops))
