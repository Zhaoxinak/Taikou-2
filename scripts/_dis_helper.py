# -*- coding: utf-8 -*-
"""Shared capstone disassembly helper for the unpacked TAIK2W95 image."""
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

import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
IMG = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
MD = Cs(CS_ARCH_X86, CS_MODE_32)
MD.detail = True


def disasm(va, nbytes=0x200):
    """Disassemble nbytes of image starting at VA. Returns list of dicts."""
    off = va - BASE
    out = []
    for ins in MD.disasm(IMG[off:off + nbytes], va):
        tgt = ""
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            tgt = ins.op_str
        elif ins.mnemonic.startswith("j") and ins.op_str.startswith("0x"):
            tgt = ins.op_str
        out.append(dict(va=ins.address, mnem=ins.mnemonic, ops=ins.op_str, tgt=tgt,
                        bytes=ins.bytes.hex()))
    return out


def find_end(va, max_nbytes=0x800):
    """Disassemble until first ret/retf/iret to bound a function."""
    off = va - BASE
    for ins in MD.disasm(IMG[off:off + max_nbytes], va):
        if ins.mnemonic in ("ret", "retf", "iret", "iretq"):
            return ins.address + ins.size
    return va + max_nbytes


def lines(va, nbytes=0x200):
    rows = disasm(va, nbytes)
    return "\n".join(
        f"0x{r['va']:06x}  {r['bytes']:<20s} {r['mnem']:<8s} {r['ops']}" for r in rows)


if __name__ == "__main__":
    import sys
    v = int(sys.argv[1], 16)
    n = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x200
    print(lines(v, n))
