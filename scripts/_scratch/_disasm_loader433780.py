"""Disassemble the generic LZW->object loader 0x433780 and the init chain
that calls it with HKMAP/HJMAP/HJCHAR/HGRP, to recover the object struct
layout (esp. the palette field) for true-color rendering."""
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

BASE = 0x400000
data = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def off_of(va): return va - BASE

def disasm(va, n):
    chunk = data[off_of(va): off_of(va)+n]
    out = []
    for ins in md.disasm(chunk, va):
        out.append(ins)
    return out

# The loader 0x433780; disassemble a generous window.
print("================ LOADER 0x433780 ================")
for ins in disasm(0x433780, 0x500):
    s = f"0x{ins.address:06x}: {ins.mnemonic} {ins.op_str}"
    print(s)
