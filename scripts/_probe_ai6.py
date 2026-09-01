#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 12: find all word-stores to [reg+0xc] (this+0xc = action code) in duel module 0x466000..0x46c000.
This is where the AI (and player) action code gets written. Disassemble each writer's function head.
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
md.detail = True

STORE = {"mov","add","sub","and","or","xor"}
hits = []
for ins in md.disasm(MEM[0x66000:0x6c000], 0x466000):
    if ins.mnemonic not in STORE:
        continue
    for op in ins.operands:
        if op.type == 3:  # X86_OP_MEM
            m = op.mem
            if m.base != 0 and m.index == 0 and m.disp == 0xc and (ins.id & 0) == 0:
                # ensure it's a word-ish store (operands[0] is memory, operands[1] is reg/imm)
                if len(ins.operands) >= 2:
                    hits.append((ins.address, ins.mnemonic, ins.op_str))
                break

hits = sorted(set(hits))
out=[]
out.append(f"found {len(hits)} word-stores to [reg+0xc]\n")
for va, mn, opstr in hits:
    # disassemble a window before to find the function and the value being stored
    s = (va - BASE) - 40
    ctx = "\n".join(f"  {i.address:#08x}: {i.mnemonic} {i.op_str}"
                    for i in md.disasm(MEM[s:va-BASE+2], BASE+s))
    out.append(f"\n--- store @ {va:#08x}: {mn} {opstr} ---")
    out.append(ctx)
open(_ROOT + '/scripts/_ai6.txt',"w",encoding="utf-8").write("\n".join(out))
print("WROTE _ai6.txt ; stores:", len(hits))
