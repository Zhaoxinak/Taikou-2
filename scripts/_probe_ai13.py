#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 18: 
1. Precise scan: genuine `mov word ptr [reg+0xc], imm` (reg = non-stack GP, disp=0xc) in
   the action region 0x469000..0x469600 and 0x466000..0x469000 — these are this+0xc setters.
2. Disasm menu callback 0x469180 and player-turn 0x468340.
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

def is_genreg(r):
    return r in (1,2,3,6,7)  # eax,ecx,edx,esi,edi (X86_REG_*)  -- capstone enum: EAX=1,ECX=2,EDX=3,EBX=4,ESP=5,EBP=6,ESI=7,EDI=8
# careful: capstone X86_REG_EAX=1, ECX=2, EDX=3, EBX=4, ESP=5, EBP=6, ESI=7, EDI=8
GEN = {1,2,3,4,7,8}

out = []
out.append("=== genuine this+0xc immediate stores (mov word [reg+0xc], imm) in action region ===")
found = []
for ins in md.disasm(MEM[0x69000:0x99600], 0x469000):
    if ins.mnemonic != "mov":
        continue
    ops = ins.operands
    if len(ops) != 2:
        continue
    dst, src = ops
    if dst.type == 3 and dst.mem.base in GEN and dst.mem.index == 0 and dst.mem.disp == 0xc:
        # src should be immediate
        if src.type == 2:  # X86_OP_IMM
            found.append((ins.address, ins.mnemonic, ins.op_str, src.imm))
# also scan 0x466000..0x469000
for ins in md.disasm(MEM[0x66000:0x90000], 0x466000):
    if ins.mnemonic != "mov":
        continue
    ops = ins.operands
    if len(ops) != 2: continue
    dst, src = ops
    if dst.type == 3 and dst.mem.base in GEN and dst.mem.index == 0 and dst.mem.disp == 0xc:
        if src.type == 2:
            found.append((ins.address, ins.mnemonic, ins.op_str, src.imm))

for va, mn, opstr, imm in sorted(found):
    # context: 0x60 bytes before
    ctx = "\n".join(f"    {i.address:#08x}: {i.mnemonic} {i.op_str}" for i in md.disasm(MEM[va-BASE-0x60:va-BASE+2], va-0x60))
    out.append(f"\n@ {va:#08x}: {mn} {opstr}  (imm={imm})")
    out.append(ctx)

open(_ROOT + '/scripts/_ai13.txt',"w",encoding="utf-8").write("\n".join(out))
print("WROTE _ai13.txt ; genuine this+0xc imm stores:", len(found))
for va, mn, opstr, imm in sorted(found):
    print(f"  {va:#08x}: {opstr}  (imm={imm})")
