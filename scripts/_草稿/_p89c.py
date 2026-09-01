# -*- coding: utf-8 -*-
"""_p89c.py — 用 FSTART 找 mode_m1 setter 函数入口 + 两 setter caller xref（P1 #89）"""
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

import pickle, struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
D = pickle.load(open("_insn_addrs.pkl", "rb"))
FSTART_OFF = D[1]
FSTART_VA = sorted(o + BASE for o in FSTART_OFF)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.skipdata = True

def enclosing_func(va):
    best = None
    for f in FSTART_VA:
        if f <= va:
            best = f
        else:
            break
    return best

def callers_of(target, win=0x1000):
    hits = []
    for va in range(BASE, BASE + len(IMG), win):
        code = IMG[va - BASE: va - BASE + win]
        for r in md.disasm(code, va):
            if r.mnemonic == "call":
                try:
                    t = int(r.op_str, 16)
                except Exception:
                    continue
                if t == target:
                    hits.append(va)
    return hits

def dump(va, n):
    print("==== 0x%x (%d bytes) ====" % (va, n))
    for r in md.disasm(IMG[va - BASE: va - BASE + n], va):
        print("  0x%x:\t%s\t%s" % (r.address, r.mnemonic, r.op_str))

# mode_m1 写点 0x42c000 所属函数
m1_func = enclosing_func(0x42c000)
print("mode_m1 setter func entry (enclosing 0x42c000) = 0x%x" % m1_func)
print("callers of mode_m1 setter 0x%x:" % m1_func, [hex(x) for x in callers_of(m1_func)])
print()
print("callers of multi-flag setter 0x43c000:", [hex(x) for x in callers_of(0x43c000)])
print()
print("##### dump mode_m1 setter 0x%x #####" % m1_func)
dump(m1_func, 0x200)
print()
print("##### dump multi-flag setter 0x43c000 #####")
dump(0x43c000, 0x300)
