#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dump_else.py -- 详查 else 簇 0x491e70 / 0x4873b0 如何取得资源基址（看 mov reg,[0x52xxxx] / lea / call 链）。"""
import os, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_unpacked_mem.bin')
BASE = 0x400000
code = open(BIN,'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=False
def disasm(va, n):
    return [(i.address,i.mnemonic,i.op_str) for i in md.disasm(code[va-BASE:va-BASE+n], va)]

# 找 0x491e70/0x4873b0 体里所有对 [0x52xxxx]/[0x50xxxx] 的读、以及 call 目标
for label,va in [('else 0x491e70',0x491e70),('else 0x4873b0',0x4873b0),('sub 0x524740',0x524740)]:
    print(f"\n===== {label} =====")
    for addr,mn,ops in disasm(va,0x400):
        # 捕获读取数据段常量
        mm=re.search(r'\[(0x[0-9a-fA-F]{6})\]',ops)
        if mm:
            v=int(mm.group(1),16)
            if 0x500000<=v<=0x52ffff:
                print(f"  0x{addr:06x}: {mn} {ops}   (读数据段 0x{v:06x})")
        if mn=='call':
            print(f"  0x{addr:06x}: call {ops}")
        if mn in ('ret','retn') and addr>va+8:
            print(f"  -- ret @0x{addr:06x} --")
            break
