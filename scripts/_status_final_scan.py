#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续171（终）：① 十进制位移感知扫描所有直接内存写 [base+0x2c/0x2d] 0x80/0x7f/0x8000/0x7fff；
② 列出 bit15 setter 0x49a860 与 bit7 setter 0x43dd20 的全部调用方（玩法语义归类）；
③ 列出其余寄存器式写者 0x46b2f0/0x48fb00 调用方。"""
import os, re, bisect
from collections import defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE; return list(md.disasm(bytes(MEM[off:off+n]), va))
def signed_disp(op):
    m = re.search(r'\[([^\]]+)\]', op)
    if not m: return None, None
    inside = m.group(1)
    bm = re.match(r'\s*([e]?[a-z]{2})', inside)
    base = bm.group(1) if bm else None
    dm = re.search(r'([+\-])\s*(0x[0-9a-f]+|\d+)$', inside)
    disp = 0
    if dm:
        s = dm.group(1); h = dm.group(2)
        disp = (int(h,16) if h.startswith('0x') else int(h,10))
        disp = disp if s=='+' else -disp
    return base, disp

INS = dis(BASE, len(MEM))
all_funcs = set([0x4f44b0, 0x400000])
for i in INS:
    if i.mnemonic=="call" and i.op_str.startswith("0x"):
        try: all_funcs.add(int(i.op_str,16))
        except: pass
all_funcs = sorted(all_funcs)
def func_of(v): return all_funcs[max(0,bisect.bisect_right(all_funcs,v)-1)]
fi=defaultdict(list)
for i in INS: fi[func_of(i.address)].append(i)
callers=defaultdict(set)
for fn,il in fi.items():
    for j in il:
        if j.mnemonic=="call" and j.op_str.startswith("0x"):
            try: callers[int(j.op_str,16)].add(fn)
            except: pass

# ① 直接内存写（注意：capstone op_str 不含 mnemonic，只匹配操作数部分）
pat = re.compile(r'^(byte|word) ptr \[([^\]]+)\],\s*(0x[0-9a-f]+|\d+)$')
print("=== ① 直接内存写 [base+0x2c/0x2d] 0x80/0x7f/0x8000/0x7fff（十进制感知）===")
mem_w=[]
for fn,il in fi.items():
    for ins in il:
        if ins.mnemonic not in ("or","and","xor"): continue
        m=pat.match(ins.op_str)
        if not m: continue
        imm=int(m.group(3),16) if m.group(3).startswith('0x') else int(m.group(3),10)
        if imm not in (0x80,0x7f,0x8000,0x7fff): continue
        base,disp=signed_disp("["+m.group(2)+"]")
        if disp in (0x2c,0x2d):
            bit = "bit15" if (disp==0x2d or imm in (0x8000,0x7fff)) else "bit7"
            kind = "SET" if m.group(1)=="or" else ("CLR" if m.group(1)=="and" else "XOR")
            mem_w.append((fn,ins.address,m.group(1),base,disp,imm,bit,kind))
for fn,a,mn,base,disp,imm,bit,kind in sorted(mem_w):
    print("0x%06x @0x%x  %s %s ptr [%s+0x%x], 0x%x  [%s %s]"%(fn,a,mn,("byte" if disp==0x2d or imm in(0x80,0x7f) else "word"),base,disp,imm,bit,kind))
print("  (注：bit15=byte[+0x2d]&0x80 / word[+0x2c]&0x8000; bit7=byte[+0x2c]&0x80)")
print("  共 %d 处\n"%len(mem_w))

# ② 调用方
for setter, nm in ((0x49a860,"bit15 setter"), (0x43dd20,"bit7 setter"), (0x48fb00,"bit7 写者"), (0x46b2f0,"bit7 镜像写者")):
    cl=sorted(callers[setter])
    print("=== ② %s 0x%06x 调用方 (%d) ==="%(nm,setter,len(cl)))
    for c in cl:
        # 该调用方是否也设 lord_idx=0xffff(ronin)？
        marks=[]
        for j in fi[c]:
            if j.mnemonic=="call" and j.op_str=="0x49a7d0": marks.append("set_lord_idx")
            if j.mnemonic=="push" and j.op_str.lower().endswith("ffff"): marks.append("push_ffff")
        print("  0x%06x  %s"%(c, " ".join(sorted(set(marks)))))
    print()
