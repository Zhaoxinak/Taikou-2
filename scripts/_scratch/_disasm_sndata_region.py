#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反汇编 SNDATA 加载/解析整段 (0x47d720..0x47ff00)，输出到 _sndata_region.asm 供分析。"""
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
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = _ROOT + '/scripts/_unpacked_mem.bin'
mem = open(MEM, "rb").read()
base = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

START, END = 0x47d720, 0x47ff00
code = mem[START-base:END-base]

out = []
for ins in md.disasm(code, START):
    if ins.address > END:
        break
    line = f"{ins.address:08x}  {ins.mnemonic} {ins.op_str}"
    out.append(line)

with open(_ROOT + '/scripts/_sndata_region.asm', "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print(f"disassembled {len(out)} instructions -> _sndata_region.asm")
