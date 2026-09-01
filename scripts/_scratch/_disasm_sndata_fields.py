#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反汇编 SNDATA 记录字段读取函数链，提取每个函数从 49B 记录读取的字节偏移 → 字段语义。"""
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

MEM=_ROOT + '/scripts/_unpacked_mem.bin'
mem=open(MEM,'rb').read()
base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)

# 在 0x47f43a 处调用的字段读取函数链
funcs=[0x47d960,0x47dae0,0x47dce0,0x47e130,0x47e3a0,0x47e440,
       0x47e5a0,0x47e770,0x47ea80,0x47ebb0,
       0x47dba0,0x47df00,0x47e260,0x47e3f0,0x47e4e0,0x47e680,
       0x47e8a0,0x47eb10,0x47ec30,0x47ece0,0x47ed40,0x47ede0,0x47eea0,0x47efa0]

def disasm_func(va, size=120):
    off=va-base
    code=mem[off:off+size]
    out=[]
    for ins in md.disasm(code, va):
        out.append((ins.address, ins.mnemonic, ins.op_str))
    return out

def extract_offsets(asm):
    """提取对 [ecx+0xXX] / [esi+0xXX] 等字节偏移的读取。"""
    offs=[]
    for addr,mn,op in asm:
        # 匹配 mov xx, byte ptr [reg+0xXX]
        import re
        m=re.search(r'byte ptr \[(e[a-z]x|e[a-z]i|e[a-z]p) \+ 0x([0-9a-f]+)\]', op)
        if m:
            offs.append((addr, int(m.group(2),16)))
        m2=re.search(r'word ptr \[(e[a-z]x|e[a-z]i|e[a-z]p) \+ 0x([0-9a-f]+)\]', op)
        if m2:
            offs.append((addr, int(m2.group(2),16), 'word'))
    return offs

print("=== SNDATA 字段读取函数 → 字节偏移 ===")
for f in funcs:
    asm=disasm_func(f)
    offs=extract_offsets(asm)
    # 显示前几行 + 提取的偏移
    head=" | ".join(f"{mn} {op}" for _,mn,op in asm[:4])
    print(f"\n0x{f:08x}:")
    print(f"   reads offsets: {[ (f'0x{o:x}' if isinstance(o,int) else o) for _,o,*_ in offs]}")
    for addr,o,*kind in offs[:6]:
        k=kind[0] if kind else 'byte'
        print(f"     0x{addr:08x}: {k} @ record offset 0x{o:x} ({o})")
