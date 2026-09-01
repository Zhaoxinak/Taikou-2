# -*- coding: utf-8 -*-
"""Dump heads of the helper functions called inside 0x47ff68 to learn their
calling convention (cleanup bytes, arg order) for stubbing under Unicorn."""
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

import os, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def head(va, n=24):
    code = IMG[va - BASE: va - BASE + 0x80]
    print("=== 0x%06x ===" % va)
    for i, ins in enumerate(md.disasm(code, va)):
        if i >= n:
            break
        print("  0x%06x: %-10s %s" % (ins.address, ins.mnemonic, ins.op_str))

for f in (0x4ebfe0, 0x4ec010, 0x4ebe60, 0x49f120, 0x49f0b0, 0x4ebfc0, 0x47fc60):
    head(f)
