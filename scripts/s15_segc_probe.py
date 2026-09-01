#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S15 段C 6B setter/getter 反汇编 + call-site 扫描（续193 候选，静态部分）。
   setter 0x49c500(idx=[esp+4], val=[esp+8]) 写入 段C(byte[基+0x13+idx]?)。
   getter 0x49c410 读 段C 字节。
   扫描全部 E8 call-site，提取每个调用点的 idx/val 实参，按游戏上下文分类。
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

import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
BIN=_ROOT + '/scripts/_unpacked_mem.bin'
SET_C=0x49c500
GET_C=0x49c410

def load():
    with open(BIN,"rb") as f: return f.read()

def disasm_at(b,va,nbytes=32):
    md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=False
    off=va-BASE
    return [(i.address,i.mnemonic,i.op_str) for i in md.disasm(b[off:off+nbytes],va)]

def find_e8_calls(b,target):
    res=[];p=0;n=len(b)
    while p<n-5:
        if b[p]==0xE8:
            rel=struct.unpack_from("<i",b,p+1)[0]
            if (p+BASE)+5+rel==target: res.append(p+BASE)
        p+=1
    return res

def get_push_arg(b,call_va):
    cp=call_va-BASE
    scan_start=max(0,cp-16)
    i=cp-1
    while i>=scan_start:
        c=b[i]
        if c==0x6A: return ("imm8",b[i+1])
        if c==0x68: return ("imm32",struct.unpack_from("<I",b,i+1)[0])
        if 0x50<=c<=0x57:
            regs=["eax","ecx","edx","ebx","esp","ebp","esi","edi"]
            return ("reg",regs[c-0x50])
        i-=1
    return ("unknown",None)

def main():
    b=load()
    print("="*70); print("S15 段C setter/getter 反汇编 + call-site 扫描"); print("="*70)
    print("\n[setter 0x%X]:"%SET_C)
    for (a,m,o) in disasm_at(b,SET_C,28): print(f"  0x{a:x}: {m} {o}")
    print("\n[getter 0x%X]:"%GET_C)
    for (a,m,o) in disasm_at(b,GET_C,24): print(f"  0x{a:x}: {m} {o}")

    cs=find_e8_calls(b,SET_C)
    print(f"\n[setter 0x{SET_C:x}] E8 call-site = {len(cs)}")
    parsed=[]
    for c in cs:
        # setter 签名: push val; push idx; call 0x49c500  => 取最近两个 push
        cp=c-BASE; scan_start=max(0,cp-20); args=[]
        i=cp-1
        while i>=scan_start and len(args)<2:
            cc=b[i]
            if cc==0x6A: args.insert(0,("imm8",b[i+1])); i-=2; continue
            if cc==0x68: args.insert(0,("imm32",struct.unpack_from("<I",b,i+1)[0])); i-=5; continue
            if 0x50<=cc<=0x57:
                regs=["eax","ecx","edx","ebx","esp","ebp","esi","edi"]
                args.insert(0,("reg",regs[cc-0x50])); i-=1; continue
            i-=1
        parsed.append((c,args))
    for c,args in parsed:
        print(f"  0x{c:x}: args={args}")

    cg=find_e8_calls(b,GET_C)
    print(f"\n[getter 0x{GET_C:x}] E8 call-site = {len(cg)} {[hex(x) for x in cg]}")

if __name__=="__main__":
    main()
