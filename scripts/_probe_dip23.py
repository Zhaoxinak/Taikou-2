# -*- coding: utf-8 -*-
"""完整反汇编 0x416900-0x416c00 (关系变好候选 dec/sub 对)."""
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

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
def rva(p): return p - BASE

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

S, E = 0x416900, 0x416c00
for ins in md.disasm(mem[rva(S): rva(E)], S):
    a = ins.address
    # 高亮关键调用 / dec / sub
    mark = ""
    if ins.mnemonic == "call":
        mark = "   <== CALL"
    elif ins.mnemonic in ("dec", "sub") and ("ax" in ins.op_str or ins.op_str == "eax"):
        mark = "   <== DEC/SUB(变好?)"
    elif ins.mnemonic in ("inc", "add") and ("ax" in ins.op_str):
        mark = "   <== INC/ADD(恶化?)"
    print(f"0x{a:05x}: {ins.mnemonic:8} {ins.op_str}{mark}")
