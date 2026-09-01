# -*- coding: utf-8 -*-
"""Dump raw disassembly at given addresses:  python scripts/_dis_at.py 0x47a390+0x60 ..."""
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

import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

for a in sys.argv[1:]:
    if '+' in a:
        s, n = a.split('+')
    else:
        s, n = a, '0x60'
    va = int(s, 16); n = int(n, 16)
    print(f'--- {va:#x} (+{n:#x}) ---')
    for ins in md.disasm(MEM[va - BASE: va - BASE + n], va):
        print(f'   0x{ins.address:x}: {ins.mnemonic} {ins.op_str}')
    print()
