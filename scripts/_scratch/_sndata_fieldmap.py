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
import os, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
MEM=_ROOT + '/scripts/_unpacked_mem.bin'
mem=open(MEM,'rb').read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)

# 解析函数链 (从 0x47f43a 与 0x47f6a8 两处调用)
funcs=[0x47d960,0x47dae0,0x47dce0,0x47e130,0x47e3a0,0x47e440,0x47e5a0,0x47e770,
       0x47ea80,0x47ebb0,0x47dba0,0x47df00,0x47e260,0x47e3f0,0x47e4e0,0x47e680,
       0x47e8a0,0x47eb10,0x47ec30,0x47ece0,0x47ed40,0x47ede0,0x47eea0,0x47efa0,
       0x47f070,0x47f110,0x47f1e0,0x47f2a0,0x47d9b0]

# 记录存于 object+0x8e (0x8e=142 .. 0x8e+48=0xbe=190)
# 找所有 "mov X, [reg+0xOFF]" 其中 0x8e<=OFF<=0xbe  → record[OFF-0x8e]
pat=re.compile(r'(?:byte|word|dword)?\s*ptr\s*\[(e[a-z]+)\s*\+\s*0x([0-9a-f]+)\]')

print("=== record-byte 读取映射 (object+0x8e .. 0xbe  → record[0..48]) ===")
for f in funcs:
    off=base-f and f-base
    code=mem[f-base:f-base+260]
    rec_offs=[]
    for ins in md.disasm(code, f):
        for m in pat.finditer(ins.op_str):
            reg=m.group(1); o=int(m.group(2),16)
            if 0x8e<=o<=0xbe:
                sz = 'w' if 'word' in ins.op_str else ('b' if 'byte' in ins.op_str else '?')
                rec_offs.append((o-0x8e, sz, ins.mnemonic, ins.op_str))
    if rec_offs:
        uniq=sorted(set((ro,sz) for ro,sz,_,_ in rec_offs))
        print(f"0x{f:08x}: record bytes {uniq}")
