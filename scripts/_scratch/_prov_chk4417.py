#!/usr/bin/env python3

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
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BIN = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
data = open(BIN,"rb").read()
def off(va): return va-BASE
cs = Cs(CS_ARCH_X86, CS_MODE_32); cs.detail=True
va=0x441780
code=data[off(va):off(va)+0x60]
for ins in cs.disasm(code, va):
    print(f"{ins.address:#08x}  {ins.mnemonic} {ins.op_str}")
