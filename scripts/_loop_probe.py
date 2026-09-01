# -*- coding: utf-8 -*-
"""Probe 0x4e8625 (main record loop ①) and 0x4e89cd (②). Print disasm to understand
stack layout passed into 0x47fc60 / 0x47ff68."""
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

for TGT, SIZE in ((0x4e8625, 0x300), (0x4e89cd, 0x300)):
    print("\n=== 0x%06x disasm (first %d bytes) ===" % (TGT, SIZE))
    for va, mn, ops in disasm(TGT, SIZE):
        print("0x%06x: %-10s %s" % (va, mn, ops))
