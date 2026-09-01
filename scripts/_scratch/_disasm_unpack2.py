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

def disasm(va, size):
    off=va-base
    return [(i.address,i.mnemonic,i.op_str) for i in md.disasm(mem[off:off+size], va)]

# 0x47dba0 是 49B 记录解析链的第一个函数，可能含 record->object 拷贝
print("=== 0x47dba0 (首字段解析/拷贝) ===")
for addr,mn,op in disasm(0x47dba0, 220):
    note=""
    if "519640" in op: note=" <== RECORD SRC"
    if re.search(r'ptr \[ecx \+ 0x', op): note+=" <== OBJ"
    print(f"0x{addr:08x}  {mn} {op}{note}")

print("\n=== 0x47df00 ===")
for addr,mn,op in disasm(0x47df00, 160):
    note=""
    if "519640" in op: note=" <== RECORD SRC"
    if re.search(r'ptr \[ecx \+ 0x', op): note+=" <== OBJ"
    print(f"0x{addr:08x}  {mn} {op}{note}")

# 通用: 在所有字段函数中找 "mov [ecx+OBJ], X" 与 "mov X, [0x519640+K]" 的配对
print("\n=== 搜索 record(K) -> object(J) 拷贝配对 (0x47dba0..0x47f2a0) ===")
funcs=range(0x47dba0,0x47f2b0,0x10)
for f in funcs:
    asm=disasm(f, 200)
    pairs=[]
    for addr,mn,op in asm:
        m=re.search(r'mov (al|ax|eax|cl|cx|ecx), (byte |word )?ptr \[(e[a-z]+|0x519640)(\+ 0x([0-9a-f]+))?\]', op)
        if m:
            pairs.append(("R",addr, int(m.group(5) or 0,16) if m.group(5) else 0))
        m2=re.search(r'mov (byte |word )?ptr \[ecx \+ 0x([0-9a-f]+)\], (al|ax|eax|cl|cx|ecx)', op)
        if m2:
            pairs.append(("O",addr, int(m2.group(2),16)))
    if pairs:
        print(f"0x{f:08x}: {pairs}")
