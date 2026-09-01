# -*- coding: utf-8 -*-

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
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *
BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va-BASE
def dis(va0, va1):
    for ins in md.disasm(MEM[off(va0):off(va1)], va0):
        print(f"{ins.address:08x}  {ins.bytes.hex():18s} {ins.mnemonic} {ins.op_str}")
if __name__ == '__main__':
    import sys as _s
    a = _s.argv
    if len(a) >= 3:
        dis(int(a[1],16), int(a[2],16))
    else:
        which = a[1]
        if which == 'p08':
            dis(0x441780, 0x4418c0)
        elif which == 'fire':
            dis(0x4e84b0, 0x4e8580)
        elif which == 'evtcluster':
            dis(0x4e7e00, 0x4e8400)
