# -*- coding: utf-8 -*-
"""Trace callers of the AI turn entry + power-table builder/fn."""
import os
IMG = r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
wanted = {
    0x4a6ba0: "ai_turn_entry_4a6ba0",
    0x49faf0: "prov_power_49faf0",
    0x4a8840: "build_power_tbl_4a8840",
    0x4a0d10: "ai_active_guard_4a0d10",
}
with open(IMG,'rb') as f:
    data=f.read()
N=len(data)
func_entries=set(); hits={t:[] for t in wanted}
i=0
while i<N-5:
    if data[i]==0xE8:
        imm=int.from_bytes(data[i+1:i+5],'little',signed=True)
        tgt=(BASE+i+5+imm)&0xffffffff
        func_entries.add(tgt)
        if tgt in wanted: hits[tgt].append(BASE+i)
    i+=1
sf=sorted(func_entries)
def cf(c):
    lo,hi=0,len(sf)
    while lo<hi:
        m=(lo+hi)//2
        if sf[m]<=c: lo=m+1
        else: hi=m
    return sf[lo-1] if lo>0 else None
out=[]
for t,n in wanted.items():
    cs=sorted(hits[t])
    out.append(f"=== callers of {n} ({hex(t)}) : {len(cs)} ===")
    for c in cs: out.append(f"  0x{c:x}  (in fn 0x{cf(c):x})")
txt="\n".join(out)
od=r"F:/Games/Taikou 2/scripts/_ai_callers3.txt"
open(od,'w').write(txt); print(txt); print("\n[written]",od)
