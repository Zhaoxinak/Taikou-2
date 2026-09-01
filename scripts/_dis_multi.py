# -*- coding: utf-8 -*-
"""_dis_multi.py — 反汇编多个 (地址+长度) 片段到文件。
用法: python scripts/_dis_multi.py 0xADDR1,0xN1 0xADDR2,0xN2 ... """
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
    s, n = a.split(',')
    va = int(s, 16); n = int(n, 16)
    print(f'=== 0x{va:x} (+{n:#x}) ===')
    for ins in md.disasm(MEM[va-BASE: va-BASE+n], va):
        print(f'  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}')
    print()
