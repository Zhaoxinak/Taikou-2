#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dump_else_full.py -- 全量反汇编 0x491e70 / 0x4873b0，读每個 call 前的 push 实参（资源索引/基址）。"""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_unpacked_mem.bin')
BASE = 0x400000
code = open(BIN,'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=False
def disasm(va, n):
    return [(i.address,i.mnemonic,i.op_str) for i in md.disasm(code[va-BASE:va-BASE+n], va)]

for label,va,end in [('else 0x491e70',0x491e70,0x491f8c),('else 0x4873b0',0x4873b0,0x487466)]:
    print(f"\n===== {label} =====")
    # 维护一个"最近 push 的立即数栈"以便关联 call 实参
    pushes=[]
    for addr,mn,ops in disasm(va, end-va+1):
        if mn=='push':
            pushes.append(ops)
            print(f"  0x{addr:06x}: push {ops}")
        elif mn=='call':
            argstr=" <- args["+",".join(pushes[-4:])+"]" if pushes else ""
            print(f"  0x{addr:06x}: call {ops}{argstr}")
            pushes=[]
        elif mn in ('ret','retn'):
            print(f"  0x{addr:06x}: ret")
            break
        else:
            pushes=[]
            print(f"  0x{addr:06x}: {mn} {ops}")
