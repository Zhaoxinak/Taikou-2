#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Disassemble the battle-map loader functions identified in
_trace_battlemap_ptrtab.py.

Reference sites (string VA -> code sites that push it):
  HBMAP.LZW      0x5030d8 : 0x42391f, 0x423939
  HBOBJ.DAT      0x503108 : 0x42402d, 0x424047
  HKMAP.LZW      0x5034e0 : 0x4338db
  HJMAP.LZW      0x5034c0 : 0x4338ec
  HJMAPDAT.DAT   0x5036f0 : 0x43a4e9, 0x43a55e
  HKMAPNEW.LZW   0x503700 : 0x43a5ae, 0x43a6db
"""
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

# function candidates: (name, approx code start, reference sites)
FUNCS = [
    ("HBMAP.LZW",    0x423900, [0x42391f, 0x423939]),
    ("HBOBJ.DAT",    0x424000, [0x42402d, 0x424047]),
    ("HKMAP/HJMAP",  0x433800, [0x4338db, 0x4338ec]),
    ("HJMAPDAT/HKMAPNEW", 0x43a400, [0x43a4e9, 0x43a55e, 0x43a5ae, 0x43a6db]),
]

def find_prologue(start_va, max_back=0x200):
    """scan backward for 'push ebp; mov ebp,esp' (55 8B EC) or 'push ebp' alone."""
    for off in range(0, max_back, 1):
        va = start_va - off
        if va < BASE:
            break
        p = va - BASE
        if data[p] == 0x55 and data[p+1] == 0x8B and data[p+2] == 0xEC:
            return va
    # fallback: just push ebp
    for off in range(0, max_back, 1):
        va = start_va - off
        p = va - BASE
        if data[p] == 0x55:
            return va
    return start_va - 0x80  # give some context

def disasm_range(va_start, va_end):
    p0 = va_start - BASE
    chunk = data[p0:(va_end - BASE)]
    out = []
    for ins in md.disasm(chunk, va_start):
        out.append(ins)
        if ins.mnemonic == "ret" or ins.mnemonic == "retn":
            break
    return out

for fname, approx, sites in FUNCS:
    print("\n" + "="*78)
    print(f"FUNCTION near 0x{approx:06x}  ({fname})   refs={[hex(s) for s in sites]}")
    print("="*78)
    prologue = find_prologue(min(sites))
    print(f"  -> detected prologue @ 0x{prologue:06x}")
    # disassemble from prologue; stop at ret after the last site
    end = max(sites) + 0x300
    insns = disasm_range(prologue, end)
    for ins in insns:
        # highlight the reference sites
        mark = ""
        if ins.address in sites:
            mark = "   <== REF"
        # show immediate operands that look like string/rdata pointers
        line = f"  0x{ins.address:06x}: {ins.mnemonic} {ins.op_str}{mark}"
        print(line)
    print(f"  (disassembled {len(insns)} instructions)")
