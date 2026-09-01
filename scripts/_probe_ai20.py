#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 20: 0x466470 (check-action-code) full, and 0x469180 (player menu callback)
to confirm action-code <-> value mapping. Also 0x49f7a0 (the 'check' before 0x469310)."""
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

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

out = []
for va, label in [(0x466470,"0x466470 check-action-code"), (0x469180,"0x469180 player menu callback"),
                  (0x49f7a0,"0x49f7a0 pre-ikkill check"), (0x468290,"0x468290 player main-menu sel")]:
    out.append(f"\n===== {label} @ {va:#08x} =====")
    for ins in md.disasm(MEM[va-BASE:va-BASE+0x200], va):
        out.append(f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}")

open(_ROOT + '/scripts/_ai20.txt',"w",encoding="utf-8").write("\n".join(out))
print("WROTE _ai20.txt")
