#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Disassemble a linear window around each battle-map loader's reference
sites, without breaking on ret, so we see the real code containing the
string pushes."""
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

import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
with open(DUMP, "rb") as f:
    data = f.read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# (label, reference sites)
FUNCS = [
    ("HKMAP/HJMAP",  [0x4338db, 0x4338ec]),
    ("HJMAPDAT/HKMAPNEW", [0x43a4e9, 0x43a55e, 0x43a5ae, 0x43a6db]),
]

def window(sites, pre=0x60, post=0x500):
    lo = min(sites) - pre
    hi = max(sites) + post
    return lo, hi

def disasm_window(va_lo, va_hi):
    p0 = va_lo - BASE
    chunk = data[p0:(va_hi-BASE)]
    return list(md.disasm(chunk, va_lo))

for label, sites in FUNCS:
    lo, hi = window(sites)
    print("\n" + "="*78)
    print(f"{label}   window 0x{lo:06x}..0x{hi:06x}")
    print("="*78)
    for ins in disasm_window(lo, hi):
        mark = "  <== REF" if ins.address in sites else ""
        print(f"  0x{ins.address:06x}: {ins.mnemonic} {ins.op_str}{mark}")
