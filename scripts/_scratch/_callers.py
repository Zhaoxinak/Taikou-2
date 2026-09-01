# -*- coding: utf-8 -*-
"""太阁2 — 在映像中查找对给定目标 VA 的 call（e8 rel32）调用点。
用法：python _callers.py 0x46336c 0x463200 0x4607f0
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

import sys, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

def callers_of(target):
    out = []
    off = 0
    # 扫描所有 e8 rel32
    while off < SZ - 5:
        if MEM[off] == 0xe8:
            rel = int.from_bytes(MEM[off+1:off+5], "little", signed=True)
            dest = BASE + off + 5 + rel
            if dest == target:
                out.append(BASE + off)
        off += 1
    return out

for arg in sys.argv[1:]:
    t = int(arg, 16) if arg.lower().startswith("0x") else int(arg)
    cs = callers_of(t)
    print("===== callers of %#x (%d) =====" % (t, len(cs)))
    for c in cs[:40]:
        print("   call @%08x" % c)
    if not cs:
        print("   (none via e8 rel32)")
