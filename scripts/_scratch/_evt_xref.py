# -*- coding: utf-8 -*-
"""Find all call sites to a given VA (call rel32 target), and print surrounding context."""
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
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def va2off(va): return va - BASE

TARGETS = [int(a, 16) for a in sys.argv[1:]] if len(sys.argv) > 1 else [0x4e82c0]

def find_callers():
    # linear scan whole image for `call rel32` whose target is in TARGETS
    results = []
    off = 0
    n = len(MEM)
    # only scan code region
    code_start = va2off(0x401000)
    code_end = va2off(0x4d0000)
    code = MEM[code_start:code_end]
    base_va = 0x401000
    for ins in md.disasm(code, base_va):
        if ins.mnemonic == 'call':
            # parse rel32
            op = ins.operands[0]
            if op.type == X86_OP_IMM:
                tgt = op.imm
                if tgt in TARGETS:
                    results.append(ins.address)
    return results

if __name__ == '__main__':
    for t in TARGETS:
        print(f"=== callers of {t:#010x} ===")
        for a in find_callers():
            print(f"  call at {a:#010x}")
