# -*- coding: utf-8 -*-
"""Dump wide windows around the 2 refs of mode_m1/battle_type to find setters."""
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

import os, struct
from _dis_helper import disasm

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
IMG = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

def find_refs(va):
    pat = struct.pack("<I", va); offs=[]; s=0
    while True:
        i = IMG.find(pat, s)
        if i<0: break
        offs.append(i); s=i+1
    return offs

for va, name in [(0x511bf8,"mode_m1"),(0x513548,"battle_type"),(0x51352c,"mode_m2"),(0x513540,"parity")]:
    refs = find_refs(va)
    print("=== %s (0x%x) : %d refs ===" % (name, va, len(refs)))
    for off in refs:
        refva = BASE+off
        print("  -- ref @0x%x --" % refva)
        for r in disasm(refva-0x50, 0xc0):
            print("    0x%x %s %s" % (r["va"], r["mnem"], r["ops"]))
        print()
