# -*- coding: utf-8 -*-
"""Bounded disassembler: _disasm.py <va_hex> <len_hex> [out_path].
Prints capstone disasm of [va, va+len). Internal 64B chunking for stability."""
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

import sys
from capstone import *
from capstone.x86 import *

IMG = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

with open(IMG, 'rb') as f:
    data = f.read()

def disasm(va, length):
    off = va - BASE
    code = data[off:off+length]
    lines = []
    # chunked to avoid capstone whole-buffer hang; resume at last good VA
    cur = va
    end = va + length
    while cur < end:
        chunk = data[(cur-BASE):(cur-BASE)+0x200]
        if not chunk:
            break
        n = 0
        for ins in md.disasm(chunk, cur):
            if ins.address >= end:
                break
            lines.append(f"  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}")
            n += 1
        if n == 0:
            lines.append(f"  (undecodable @0x{cur:x})")
            cur += 1
        else:
            cur = ins.address + ins.size
    return lines

if __name__ == "__main__":
    va = int(sys.argv[1], 16)
    length = int(sys.argv[2], 16)
    out = None
    if len(sys.argv) > 3:
        out = sys.argv[3]
    txt = "\n".join(disasm(va, length))
    print(txt)
    if out:
        with open(out, 'w') as f:
            f.write(txt)
        print("\n[written]", out)
