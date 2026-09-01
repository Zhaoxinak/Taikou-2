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
# Inline capstone disassembler for a VA range (no per-function timeout risk).
# Usage: python _dis.py 0x443f00 0x800
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BIN = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000

va = int(sys.argv[1], 16)
n  = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x200
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

data = open(BIN, "rb").read()
off = va - BASE
code = data[off:off+n]

for ins in md.disasm(code, va):
    # show bytes
    bs = ins.bytes.hex()
    print(f"0x{ins.address:06x}  {bs:<20} {ins.mnemonic} {ins.op_str}")
