#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续171：确认 is_alive 位映射 + 关键 setter 调用方语义。"""
import os, bisect
from collections import defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
MEM=open('scripts/_unpacked_mem.bin','rb').read()
def dis(va,n):
    md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
    off=va-BASE; return list(md.disasm(bytes(MEM[off:off+n]),va))
INS=dis(BASE,len(MEM))
af=set([0x4f44b0,0x400000])
for i in INS:
    if i.mnemonic=="call" and i.op_str.startswith("0x"):
        try: af.add(int(i.op_str,16))
        except: pass
af=sorted(af)
def fo(v): return af[max(0,bisect.bisect_right(af,v)-1)]
fi=defaultdict(list)
for i in INS: fi[fo(i.address)].append(i)
callers=defaultdict(set)
for fn,il in fi.items():
    for j in il:
        if j.mnemonic=="call" and j.op_str.startswith("0x"):
            try: callers[int(j.op_str,16)].add(fn)
            except: pass
def dump(fn,n=0xc0,label=""):
    print("#"*74); print("# 0x%06x %s  调用方=%s"%(fn,label," ".join("0x%06x"%c for c in sorted(callers[fn])[:10]))); print("#"*74)
    for ins in dis(fn,n): print("  0x%x  %-8s %s"%(ins.address,ins.mnemonic,ins.op_str))
    print()
dump(0x470690,0x40,"is_alive")
dump(0x49a730,0x40,"bit7 XOR toggle")
dump(0x433ad0,0xa0,"caller of bit7 setter 0x43dd20")
# bit15 setter 调用方语义：上溯一层
for c in (0x40c010,0x40feb0,0x40ffc0,0x440d20):
    dump(c,0x60,"bit15+ronin 调用方")
