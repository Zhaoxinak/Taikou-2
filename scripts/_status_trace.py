#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续171：① 反汇编共享 setter 库 0x49bd50/0x49bd70/0x49bd90/0x49a7e0 看各自置哪位；
② 追 bit15 写者 0x439190 的调用链 + bit7 写者 0x43dd20/0x48fb00 的调用链。"""
import os, bisect
from collections import defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()

def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off+n]), va))

INS = dis(BASE, len(MEM))
all_funcs = set([0x4f44b0, 0x400000])
for i in INS:
    if i.mnemonic == "call" and i.op_str.startswith("0x"):
        try: all_funcs.add(int(i.op_str, 16))
        except: pass
all_funcs = sorted(all_funcs)
def func_of(va): return all_funcs[max(0, bisect.bisect_right(all_funcs, va) - 1)]
func_insns = defaultdict(list)
for i in INS: func_insns[func_of(i.address)].append(i)

callers = defaultdict(set)
for fn, ilist in func_insns.items():
    for j in ilist:
        if j.mnemonic == "call" and j.op_str.startswith("0x"):
            try: callers[int(j.op_str,16)].add(fn)
            except: pass

def dump(fn, n=0x160, label=""):
    print("#"*78); print("# 0x%06x %s  调用方=%s" % (fn, label, " ".join("0x%06x"%c for c in sorted(callers[fn])[:12]))); print("#"*78)
    for ins in dis(fn, n):
        print("  0x%x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
    print()

print("===== 共享 setter 库（word[+0x2c] 各位段）=====")
for f in (0x49bd50, 0x49bd70, 0x49bd90, 0x49a7e0):
    dump(f, 0x80, "set_status*")

print("===== bit15 写者 0x439190 调用链 =====")
dump(0x439190, 0x420, "bit15 SET+CLR (cond byte[+0x2b]&0xc0==0x40)")
dump(0x439150, 0xa0, "caller of 0x439190")

print("===== bit7 写者 0x43dd20 调用链 =====")
dump(0x43dd20, 0x60, "bit7 布尔 setter")
dump(0x433ad0, 0xc0, "caller of 0x43dd20")

print("===== bit7 写者 0x48fb00 调用链 =====")
dump(0x48fb00, 0x100, "bit7 SET or 128")
for c in sorted(callers[0x48fb00]):
    dump(c, 0x80, "caller of 0x48fb00")
