#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续171（修正3）：处理 ax/ah、ax/al 别名，配对 load/modify/store 定位真实状态字写者。"""
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

import os, re, bisect
from collections import defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
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

def base_disp(op):
    m=re.search(r'\[([^\]]+)\]', op)
    if not m: return None,None
    inside=m.group(1)
    bm=re.match(r'\s*([e]?[a-z]{2})', inside)
    base=bm.group(1) if bm else None
    dm=re.search(r'([+\-])\s*(0x[0-9a-f]+|\d+)$', inside)
    disp=0
    if dm:
        s=dm.group(1); h=dm.group(2)
        disp=int(h,16) if h.startswith('0x') else int(h,10)
        disp=disp if s=='+' else -disp
    return base,disp

loads=[]; stores=[]; ors=[]
for fn,ilist in fi.items():
    for ins in ilist:
        m=re.match(r'(e?[a-z]{2}),\s*(word|byte) ptr \[([^\]]+)\]$', ins.op_str)
        if m and ins.mnemonic=="mov":
            base,disp=base_disp("["+m.group(3)+"]")
            loads.append((fn,ins.address,m.group(1),m.group(2),base,disp))
        s=re.match(r'(word|byte) ptr \[([^\]]+)\],\s*(e?[a-z]{2})$', ins.op_str)
        if s and ins.mnemonic=="mov":
            base,disp=base_disp("["+s.group(2)+"]")
            stores.append((fn,ins.address,s.group(3),s.group(1),base,disp))
        r=re.match(r'((?:e?[a-z]{2})|ah|al),\s*(0x[0-9a-f]+|\d+)$', ins.op_str)
        if r and ins.mnemonic in ("or","and"):
            imm=int(r.group(2),16) if r.group(2).startswith('0x') else int(r.group(2),10)
            if imm in (0x80,0x7f,0x8000,0x7fff):
                dr=r.group(1)
                if imm in (0x8000,0x7fff): sz,bit="word","bit15"
                else:
                    sz,bit=("byte","bit15") if dr=="ah" else ("byte","bit7")
                ors.append((fn,ins.address,dr,sz,bit))

# ax/ah、ax/al 别名：or 在 ah -> 数据经 ax；or 在 al -> 数据经 ax
def data_regs(dr):
    if dr=="ah": return ("ax","ah")
    if dr=="al": return ("ax","al")
    return (dr,)

W=80
hits=[]
for (fn,oa,dr,sz,bit) in ors:
    drs=data_regs(dr)
    valid_ld = (("word",0x2c),("byte",0x2d)) if bit=="bit15" else (("byte",0x2c),("word",0x2c))
    lb=None
    for L in loads:
        if L[0]!=fn or L[1]>=oa or oa-L[1]>W*4: continue
        if L[2] not in drs: continue
        if (L[3],L[5]) not in valid_ld: continue
        lb=L; break
    sb=None
    for S in stores:
        if S[0]!=fn or S[1]<=oa or S[1]-oa>W*4: continue
        if S[2] not in drs: continue
        if (S[3],S[5]) not in valid_ld: continue
        sb=S; break
    if lb or sb:
        b = lb[4] if lb else sb[4]
        hits.append((fn,oa,bit, lb[1] if lb else None, sb[1] if sb else None, b, "SET" if dr in ("or",) or True else "X"))

print("真实状态字 bit15/bit7 写者：%d 处（load/modify/store 配对）\n"%len(hits))
seen=set()
for fn,oa,bit,la,sa,b,*_ in sorted(hits):
    if fn in seen: continue
    seen.add(fn)
    print("0x%06x  or@0x%x(%s)  load@%s  store@%s  ptr=%s"%(fn,oa,bit,("0x%x"%la if la else "—"),("0x%x"%sa if sa else "—"),b))
print("\n共 %d 个函数。"%len(seen))
