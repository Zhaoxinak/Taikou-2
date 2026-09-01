# -*- coding: utf-8 -*-
"""dump 0x4b6095-0x4b6160 (set_diplo 2 + set_lord 3 紧邻, 疑高压外交成功=屈服)."""
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

import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
def rva(p): return p - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

S, E = 0x4b6080, 0x4b6130
for ins in md.disasm(mem[rva(S): rva(E)], S):
    a = ins.address
    tag = ""
    if ins.mnemonic == "call": tag = "  <CALL>"
    elif ins.mnemonic == "push" and re.match(r"^0x92[0-9a-f]$", ins.op_str): tag = "  <MSGX?"
    print(f"0x{a:05x}: {ins.mnemonic:9} {ins.op_str}{tag}")
