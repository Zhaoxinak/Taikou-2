#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续192 候选：S7 +0x08 状态机深度追查。
   ① 读跳表 0x49c1cc（8 项 dword 绝对地址 = 低3位 0..7 的派发目标）。
   ② 找派发器 0x49c064 与 +0x08 写 setter 0x49bfba 的 E8 call-site。
   ③ 回溯 call-site 的 ecx 来源，确认是否 = S7 条目 (0x516a28+16*idx)。
   ④ 反汇编每个跳表目标前几指令，判状态机形态。
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
DISP=0x49c064        # +0x08 状态机派发器 (low3 bits -> jmp [edx*4+0x49c1cc])
JTAB=0x49c1cc        # 跳表基址
SET08=0x49bfba       # +0x08 word setter (之前 0 E8 call-site)

def load():
    with open(BIN,"rb") as f: return f.read()

def find_e8_calls(b,target):
    res=[];p=0;n=len(b)
    while p<n-5:
        if b[p]==0xE8:
            rel=struct.unpack_from("<i",b,p+1)[0]
            if (p+BASE)+5+rel==target: res.append(p+BASE)
        p+=1
    return res

def disasm_at(b,va,nbytes=32):
    md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=False
    off=va-BASE
    return [(i.address,i.mnemonic,i.op_str) for i in md.disasm(b[off:off+nbytes],va)]

def trace_ecx(b,va,nbytes=130):
    """回溯 call-site 找 S7 基址锚点 (0x516a28) 或城表基址 (0x51eb88)。"""
    off=va-BASE;start=max(0,off-nbytes)
    hits=[]
    for ins in Cs(CS_ARCH_X86,CS_MODE_32).disasm(b[start:off+6],start+BASE):
        if "0x516a28" in ins.op_str: hits.append((ins.address,"S7"))
        elif "0x51eb88" in ins.op_str: hits.append((ins.address,"CASTLE"))
    return hits

def main():
    b=load()
    # ① 跳表
    jt_off=JTAB-BASE
    jt=[struct.unpack_from("<I",b,jt_off+i*4)[0] for i in range(8)]
    print(f"[跳表 0x{JTAB:x}] 8 项 (低3位 0..7 派发目标):")
    for i,addr in enumerate(jt):
        d=disasm_at(b,addr,16)
        txt=" | ".join(f"{m} {o}" for (_,m,o) in d)
        print(f"  [{i}] 0x{addr:x}: {txt}")
    # ② call-site
    calls_disp=find_e8_calls(b,DISP)
    calls_s08=find_e8_calls(b,SET08)
    print(f"\n[派发器 0x{DISP:x}] E8 call-site = {len(calls_disp)} {[hex(c) for c in calls_disp]}")
    print(f"[+0x08 setter 0x{SET08:x}] E8 call-site = {len(calls_s08)} {[hex(c) for c in calls_s08]}")
    # ③ ecx 溯源
    print("\n[派发器 call-site ecx 溯源]")
    for c in calls_disp:
        h=trace_ecx(b,c)
        tag=",".join(f"{k}@{a:x}" for (a,k) in h) or "无 S7/城表锚点"
        print(f"  0x{c:x} -> {tag}")
    if not calls_disp:
        print("  (派发器 0 E8 call-site —— 可能经寄存器间接调用或属共享库)")

if __name__=="__main__":
    main()
