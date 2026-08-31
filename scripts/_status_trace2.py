#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续171：① 0x439150 调用链（bit15 写者 0x439190 的 caller）② 0x48fb00 全文 ③ 上溯调用方找玩法事件。"""
import os, bisect
from collections import defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE; return list(md.disasm(bytes(MEM[off:off+n]), va))
INS = dis(BASE, len(MEM))
all_funcs = set([0x4f44b0, 0x400000])
for i in INS:
    if i.mnemonic=="call" and i.op_str.startswith("0x"):
        try: all_funcs.add(int(i.op_str,16))
        except: pass
all_funcs=sorted(all_funcs)
def func_of(v): return all_funcs[max(0,bisect.bisect_right(all_funcs,v)-1)]
fi=defaultdict(list)
for i in INS: fi[func_of(i.address)].append(i)
callers=defaultdict(set)
for fn,il in fi.items():
    for j in il:
        if j.mnemonic=="call" and j.op_str.startswith("0x"):
            try: callers[int(j.op_str,16)].add(fn)
            except: pass

def dump(fn, n=0x160, label=""):
    print("#"*78); print("# 0x%06x %s  调用方=%s"%(fn,label," ".join("0x%06x"%c for c in sorted(callers[fn])[:14]))); print("#"*78)
    for ins in dis(fn,n):
        print("  0x%x  %-8s %s"%(ins.address,ins.mnemonic,ins.op_str))
    print()

# 0x439190 调用链
dump(0x439150, 0x160, "caller of 0x439190 (bit15写)")
for c in sorted(callers[0x439150]):
    dump(c, 0x80, "caller of 0x439150")

# 0x48fb00 全文 + 上溯
dump(0x48fb00, 0x120, "bit7 SET or 128")
for c in sorted(callers[0x48fb00]):
    dump(c, 0x100, "caller of 0x48fb00")

# 0x43dd20 上溯
dump(0x433ad0, 0xc0, "caller of 0x43dd20 (bit7 setter)")
for c in sorted(callers[0x433ad0]):
    dump(c, 0x100, "caller of 0x433ad0")
