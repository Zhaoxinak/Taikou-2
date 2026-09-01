# -*- coding: utf-8 -*-
"""Disassemble 0x4882b1 (a caller of 0x47ff68) to learn the stack frame layout
passed into the per-type decoder. Find the call to 0x47ff68 and the record setup."""
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
    return list(md.disasm(code, va))

# 0x4882b1: disassemble a window and look for 47ff68 / 47fc60 / record setup
for TGT, SIZE in ((0x4882b1, 0x600),):
    print("=== 0x%06x ===" % TGT)
    for ins in disasm(TGT, SIZE):
        s = ins.op_str
        mark = ""
        if '47FF68' in s.upper() or '47FC60' in s.upper():
            mark = "   <<< DISPATCH/FANOUT"
        if ins.mnemonic == 'call' and not s.startswith('0x'):
            mark = "   <<< indirect call"
        print("0x%06x: %-10s %s%s" % (ins.address, ins.mnemonic, s, mark))
