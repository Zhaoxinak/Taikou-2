#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dis.py <start_va_hex> <end_va_hex>  -- linear disasm dump of _unpacked_mem.bin"""
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

import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BIN = _ROOT + '/scripts/_unpacked_mem.bin'
data = open(BIN, 'rb').read()
BASE = 0x400000
st = int(sys.argv[1], 16)
en = int(sys.argv[2], 16)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False
o = st - BASE
for insn in md.disasm(data[o:o+(en-st)], st):
    if insn.address >= en:
        break
    print('%08x: %-10s %s' % (insn.address, insn.mnemonic, insn.op_str))
