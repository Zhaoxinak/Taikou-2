#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续171：精确定位状态字 word[+0x2c] 的真实写者（基址寄存器须指向 entity+0x2c）。
扫描全镜像所有 or/and byte[reg+0x2c]/[reg+0x2d]/word[reg+0x2c]，记录函数 + 形式。"""
import os, re, bisect
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

# 找「基址指针」：函数内是否出现 `mov reg, [..]` 或 `lea reg,[base+0x2c]` 之类，把 reg 标为 status base
# 简化：检查每条写指令的基址寄存器是否在该函数内被赋值为某实体的 +0x2c。
# 但我们关心的是「写点本身是否在实体状态字」，先暴力列出所有候选写点及其函数，再人工看基址。
pat = re.compile(r'^(?:or|and|add|sub|xor) (?:byte|word) ptr \[([^\]]+)\],\s*(0x[0-9a-f]+|\d+)$')
results = []
for fn, ilist in func_insns.items():
    for ins in ilist:
        m = pat.match(ins.op_str)
        if not m: continue
        inside, imm_s = m.group(1), m.group(2)
        imm = int(imm_s,16) if imm_s.startswith('0x') else int(imm_s,10)
        # 只关心与 0x80/0x7f/0x8000/0x7fff 相关的状态位写
        if imm not in (0x80,0x7f,0x8000,0x7fff,0xff7f,0x80ff): continue
        # 解析基址寄存器与位移
        m2 = re.match(r'(e?[a-z]{2})\s*\+\s*(0x[0-9a-f]+|\d+)$', inside)
        reg, disp = (None,None)
        if m2:
            reg = m2.group(1); disp = int(m2.group(2),16) if m2.group(2).startswith('0x') else int(m2.group(2),10)
        else:
            m3 = re.match(r'(e?[a-z]{2})$', inside)
            if m3: reg = m3.group(1); disp = 0
        if reg is None: continue
        if disp not in (0x2c, 0x2d, 0): continue
        results.append((fn, ins.address, ins.mnemonic, reg, disp, imm))

print("状态字位写点（or/and … 0x80/0x7f/0x8000/0x7fff）候选：%d 处\n" % len(results))
for fn, a, mn, reg, disp, imm in sorted(results):
    bit = {0x8000:"bit15",0x7fff:"~bit15",0x80:"bit7",0x7f:"~bit7",0xff7f:"~bit7(16)",0x80ff:"bit7(16)"}.get(imm,str(imm))
    print("0x%06x  @0x%x  %s %s%+x  %s" % (fn, a, mn, reg, disp, bit))
