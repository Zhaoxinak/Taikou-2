# -*- coding: utf-8 -*-
"""_p89b.py — dump 0x42c000/0x43c000 模式标志 setter + 找 caller"""
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

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _dis_helper import disasm
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.skipdata = True

def dump(va, n):
    print("==== 0x%x (%d bytes) ====" % (va, n))
    for r in disasm(va, n):
        print("  0x%x:\t%s\t%s" % (r["va"], r["mnem"], r["ops"]))

def callers_of(target):
    hits = []
    step = 0x1000
    for va in range(BASE, BASE + len(IMG), step):
        code = IMG[va - BASE: va - BASE + step]
        for r in md.disasm(code, va):
            if r.mnemonic == "call":
                try:
                    t = int(r.op_str, 16)
                except Exception:
                    continue
                if t == target:
                    hits.append(va)
    return hits

print("##### mode_m1 setter 0x42c000 #####")
dump(0x42c000, 0x120)
print("callers of 0x42c000:", [hex(x) for x in callers_of(0x42c000)])
print()
print("##### multi-flag setter 0x43c000 #####")
dump(0x43c000, 0x200)
print("callers of 0x43c000:", [hex(x) for x in callers_of(0x43c000)])
