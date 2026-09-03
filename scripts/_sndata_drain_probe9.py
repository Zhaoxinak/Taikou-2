#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import struct, pickle, sys
sys.path.insert(0, "scripts")
from _disasm_all import load_image
BASE=0x400000; code=load_image()
pkl=pickle.load(open("scripts/_insn_addrs.pkl","rb")); FS=sorted(pkl[1])
def fn(va):
    fo=va-BASE; lo,hi=0,len(FS)-1; best=None
    while lo<=hi:
        m=(lo+hi)//2
        if FS[m]<=fo: best=FS[m]; lo=m+1
        else: hi=m-1
    return (BASE+best) if best is not None else None
def calls_of(t):
    out=set(); off=0
    while True:
        i=code.find(b'\xe8',off)
        if i<0: break
        rel=struct.unpack('<i',code[i+1:i+5])[0]; va=BASE+i+5+rel
        if va==t: out.add(BASE+i)
        off=i+1
    return out
for t in (0x48b5f0, 0x4624f0):
    cs=calls_of(t)
    print(f"callers of 0x{t:06x} ({len(cs)}):", [hex(fn(c)) for c in sorted(cs)])
