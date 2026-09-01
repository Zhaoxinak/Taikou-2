#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 19: disassemble the 5 action executors (0x80 bytes each) to confirm:
- do they set this+0xc (action code)?
- do they call 0x468860 / 0x468640 (the performer)?
This reveals how the AI routes to the same executors."""
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
    0x468af0: "ACT0 (普通攻击? from menu idx0)",
    0x46a680: "ACT1 (瞄准? from menu idx1)",
    0x468cd0: "ACT2 (快刀? from menu idx2)",
    0x468f00: "ACT3 (击中要害? from menu idx3)",
    0x4663f0: "ACT4 (一击必杀 from menu idx4)",
}
out = []
for va, label in targets.items():
    out.append(f"\n===== {label} @ {va:#08x} =====")
    for ins in md.disasm(MEM[va-BASE:va-BASE+0x90], va):
        out.append(f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}")

open(_ROOT + '/scripts/_ai16.txt',"w",encoding="utf-8").write("\n".join(out))
print("WROTE _ai16.txt")
