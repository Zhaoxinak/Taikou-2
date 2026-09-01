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
import os, re, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
MEM=_ROOT + '/scripts/_unpacked_mem.bin'
mem=open(MEM,'rb').read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)

# 搜所有对 0x519640 的引用 (4字节LE)
target=struct.pack("<I",0x519640)
hits=[]
p=0
while True:
    q=mem.find(target,p)
    if q<0: break
    hits.append(q); p=q+1
print(f"0x519640 引用数: {len(hits)}")
for h in hits:
    va=base+h
    # 反汇编周围
    code=mem[h-30:h+90]
    print(f"\n--- ref @ 0x{va:08x} (file 0x{h:x}) ---")
    for ins in md.disasm(code, va-30):
        mark=" >>>" if ins.address==va else "    "
        print(f"  0x{ins.address:08x}{mark} {ins.mnemonic} {ins.op_str}")
