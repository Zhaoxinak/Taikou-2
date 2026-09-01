#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
md.detail = False

def disasm(a,b):
    return "\n".join(f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}"
                     for ins in md.disasm(MEM[a-BASE:b-BASE], a))

out=[]
out.append("===== 0x468860 (AI decision candidate) 0x468860..0x4689c0 =====")
out.append(disasm(0x468860, 0x4689c0))
out.append("\n===== 0x469710 (turn init candidate) 0x469710..0x469820 =====")
out.append(disasm(0x469710, 0x469820))
open(_ROOT + '/scripts/_ai4.txt',"w",encoding="utf-8").write("\n".join(out))
print("WROTE _ai4.txt")
