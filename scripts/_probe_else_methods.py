#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_else_methods.py -- 抽 else 簇调用的 9 个资源子系统 method 各自的资源基址。
每个 method 反汇编，找它传给我们已知资源加载原语(0x4802e0 / 0x4ec8c0 / 0x4ecf30 族)
的 0x50xxxx 基址立即数，或自身 mov reg,0x50xxxx。解码成资源名。"""
import os, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_unpacked_mem.bin')
BASE = 0x400000
code = open(BIN,'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=False
def disasm(va, n):
    return [(i.address,i.mnemonic,i.op_str) for i in md.disasm(code[va-BASE:va-BASE+n], va)]
def decode_res_array(b, maxn=8):
    out=[]
    for i in range(maxn):
        a=b+i*16
        if a-BASE+14>len(code): break
        raw=code[a-BASE:a-BASE+14]; nn=raw.find(0)
        if nn<0: nn=14
        if nn==0: break
        try: s=bytes(raw[:nn]).decode('gbk')
        except Exception: s=bytes(raw[:nn]).decode('latin-1','replace')
        if ':' not in s: break
        out.append(s)
    return out

METHODS = [0x4ecf30,0x4ecf90,0x4ee720,0x4ee060,0x4ed710,0x4edfa0,0x4edf70,0x4ed930,0x4ed880]
for m in METHODS:
    print(f"\n### method 0x{m:06x}")
    seen=set()
    for addr,mn,ops in disasm(m,0x200):
        for mm in re.finditer(r'0x([0-9a-fA-F]{5,6})',ops):
            v=int(mm.group(1),16)
            if 0x503000<=v<=0x50ca08 and v not in seen:
                seen.add(v)
                print(f"  0x{addr:06x}: {mn} {ops}  -> {decode_res_array(v)}")
    if not seen:
        print("  (无 0x50xxxx 资源基址立即数)")
