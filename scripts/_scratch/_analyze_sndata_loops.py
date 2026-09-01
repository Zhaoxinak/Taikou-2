#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
循环感知的 SNDATA sub-loader 字节消费估算:
  每个 sub-loader 通过 0x47d910(读1B)/0x47d930(读2B) 顺序读取文件.
  找到循环(回边)及其计数器(常量 ecx), 将循环体内 read 调用 x 计数.
  累加得到该段消费字节, 期望总和 ~ 692*59 = 40828.
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

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
data=open(_ROOT + '/scripts/_unpacked_mem.bin',"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
SUBS=[0x47dae0,0x47dce0,0x47e130,0x47e3a0,0x47e440,0x47e5a0,0x47e770,
      0x47ea80,0x47ebb0,0x47ecb0,0x47ed10,0x47ed70,0x47ee50,0x47ef00,
      0x47f050,0x47f0a0,0x47f1b0,0x47f210]
READ1={0x47d910,0x47da10}
READ2={0x47d930,0x47da50}

def analyze(addr):
    chunk=data[addr-BASE:addr-BASE+0x900]
    insns=list(md.disasm(chunk,addr))
    reads=[]  # (ea, size)
    for ins in insns:
        if ins.mnemonic=="call":
            t=int(ins.op_str.replace("0x",""),16) if ins.op_str.startswith("0x") else -1
            if t in READ1: reads.append((ins.address,1))
            elif t in READ2: reads.append((ins.address,2))
    # 找回边
    loops=[]  # (target, back_addr, counter_or_None)
    for ins in insns:
        if ins.mnemonic in ("jne","je","jmp","loop","jnz") and ins.op_str.startswith("0x"):
            tgt=int(ins.op_str,16)
            if tgt < ins.address:
                # 找计数器: 在 [tgt, back] 内最近 mov ecx, imm
                cnt=None
                for j in insns:
                    if tgt <= j.address <= ins.address and j.mnemonic=="mov":
                        m=__import__("re").search(r"ecx, 0x([0-9a-f]+)", j.op_str)
                        if m: cnt=int(m.group(1),16)
                loops.append((tgt, ins.address, cnt))
    # 计算每个 read 的最内层 enclosing loop
    covered=set()
    consumed=0
    for (ea,sz) in reads:
        # 找包含 ea 的最小循环
        enclosing=None
        for (t,b,c) in loops:
            if t < ea < b:
                if enclosing is None or (b-t) < (enclosing[1]-enclosing[0]):
                    enclosing=(t,b,c)
        if enclosing is not None:
            c=enclosing[2]
            if c: consumed += sz*c
            else: consumed += sz  # 未知计数, 估 1
            covered.add(ea)
        else:
            consumed += sz
    return consumed, len(reads), loops

total=0
print("# sub-loader 循环感知字节消费估算")
for a in SUBS:
    cons, nreads, loops = analyze(a)
    total += cons
    lc = ";".join(f"{t:#x}-{b:#x}:{c}" for (t,b,c) in loops) if loops else "-"
    print(f"@0x{a:08x}  est_bytes={cons:6d}  reads={nreads:3d}  loops=[{lc}]")
print(f"\n估算总消费 = {total}  (目标 692*59={692*59})")
print("DONE")
