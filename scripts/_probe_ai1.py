#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 7: disassemble the duel action/dispatch core 0x468000..0x468c00 to locate
how the PLAYER action code is obtained (menu_fn + table) vs how the AI action code is
chosen (the AI selection logic we want to crack). Print with our msgx id map for context.
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

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

# load msgx id map if present
mid = {}
try:
    import json
    mid = json.load(open(_ROOT + '/scripts/msgx_id_map.json', encoding="utf-8"))
except Exception:
    pass

def disasm(va_start, va_end):
    s = va_start - BASE
    e = va_end - BASE
    out=[]
    for ins in md.disasm(MEM[s:e], va_start):
        line = f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}"
        # annotate push of msg id
        if ins.mnemonic == "push" and ins.op_str.startswith("0x"):
            v = int(ins.op_str,16)
            if 0x1700 <= v <= 0x1c00:
                line += f"   ; MSGX {v:#06x}"
        out.append(line)
    return "\n".join(out)

txt = disasm(0x468000, 0x468c00)
open(_ROOT + '/scripts/_ai1.txt',"w",encoding="utf-8").write(txt)
print("WROTE _ai1.txt ; lines:", txt.count(chr(10)))
