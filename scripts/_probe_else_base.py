#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_else_base.py -- 反汇编 else 簇(0x491e70/0x4873b0/0x524740) 抽取资源数组基址
（形如 mov reg,0x50xxxx / lea reg,[0x50xxxx]，资源数组基址落在 0x503000..0x50ca08）。
同时把已知 layer0/layer1 基址(0x506b20/0x506b30/0x506ba0/0x506bb0)解码成资源名数组做校验。"""
import os, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_unpacked_mem.bin')
BASE = 0x400000
code = open(BIN,'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=False

def disasm(va, n):
    return [(i.address,i.mnemonic,i.op_str) for i in md.disasm(code[va-BASE:va-BASE+n], va)]

def decode_res_array(base, maxn=16):
    out=[]
    for i in range(maxn):
        a=base+i*16
        if a-BASE+14>len(code): break
        raw=code[a-BASE:a-BASE+14]; nn=raw.find(0)
        if nn<0: nn=14
        if nn==0: break
        try: s=bytes(raw[:nn]).decode('gbk')
        except Exception: s=bytes(raw[:nn]).decode('latin-1','replace')
        if ':' not in s: break
        out.append(s)
    return out

# 抽 else 簇里的 0x50xxxx 立即数
for label,va in [('else 0x491e70',0x491e70),('else 0x4873b0',0x4873b0),('else 0x524740',0x524740)]:
    print(f"\n### {label}  (0x50xxxx 立即数 + lea)")
    for addr,mn,ops in disasm(va,0x300):
        m=re.search(r'0x([0-9a-fA-F]{5,6})',ops)
        if m:
            v=int(m.group(1),16)
            if 0x503000<=v<=0x50ca08:
                print(f"  0x{addr:06x}: {mn} {ops}   -> 数组解码: {decode_res_array(v)}")

print("\n=== 已知 layer 基址校验 ===")
for base in (0x506b20,0x506b30,0x506ba0,0x506bb0):
    print(f"  0x{base:06x}: {decode_res_array(base)}")
