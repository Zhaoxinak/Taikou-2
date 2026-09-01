# -*- coding: utf-8 -*-
"""Disassemble the event-condition evaluator at 0x4e82c0 and dump it.
Linear disassembly with symbol annotations; prints to stdout (utf-8)."""
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

import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

SYM = {
    0x4e82c0: 'EVT_COND_EVAL (event condition evaluator)',
    0x47d910: 'rd1B', 0x47d930: 'rd2B', 0x47da10: 'rd1B_impl', 0x47da50: 'rd2B_impl',
    0x4ebd30: 'rand', 0x4ebd60: 'rand%n',
    0x4ede20: 'showStr', 0x47b900: 'msgDispatch', 0x46fd20: 'msgDispatch2',
    0x493500: 'MSGX_lookup', 0x47b8d0: 'showMsg',
    0x4f1d37: 'uiListRender', 0x47ad90: 'listSetData',
}

def va2off(va):
    return va - BASE

def disasm(va_start, va_end):
    off = va2off(va_start)
    code = MEM[off: va2off(va_end)]
    cur = va_start
    out = []
    for ins in md.disasm(code, va_start):
        sym = SYM.get(ins.address)
        s = f"{ins.address:08x}  {ins.bytes.hex():20s} {ins.mnemonic} {ins.op_str}"
        if sym:
            s += f"   ; << {sym}"
        out.append(s)
    return out

if __name__ == '__main__':
    import sys
    va = 0x4e82c0
    end = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x4e8a00
    for line in disasm(va, end):
        print(line)
