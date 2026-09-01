#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 16: disassemble candidate action-executor functions called by the orchestrator
loop, looking for where this+0xc (action code) gets written for the AI/host side.
Targets: 0x469070, 0x469310, 0x4ee470, 0x4696a0 (end), 0x468640 (apply)."""
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

targets = {
    0x469070: "0x469070 (loop opener, edi!=0 branch)",
    0x469310: "0x469310 (after 0x466470+0x49f7a0)",
    0x4ee470: "0x4ee470 (ecx=0x514348)",
    0x4696a0: "0x4696a0 (end-of-duel handler)",
    0x468640: "0x468640 (apply action)",
}

out = []
for va, label in targets.items():
    out.append(f"\n===== {label} @ {va:#08x} =====")
    for ins in md.disasm(MEM[va-BASE:va-BASE+0x300], va):
        out.append(f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}")

open(_ROOT + '/scripts/_ai11.txt',"w",encoding="utf-8").write("\n".join(out))
print("WROTE _ai11.txt")
