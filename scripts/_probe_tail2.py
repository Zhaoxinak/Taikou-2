#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Map entity+0x1c flag setters and correlate BSDATA 0x2c with HP."""
import os, struct
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

code = open("scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def callers(target):
    sites=[]
    for i in range(len(code)-5):
        if code[i]==0xE8:
            rel=int.from_bytes(code[i+1:i+5],"little",signed=True)
            if BASE+i+5+rel==target:
                sites.append(BASE+i)
    return sites

def dis(va, n=0x30):
    out=[]
    for i in md.disasm(code[va-BASE:va-BASE+n], va):
        out.append(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}")
        if i.mnemonic.startswith("ret") and i.address>va:
            break
    return out

# Flag setters on +0x1c
for va, bit in [(0x49ab80,4),(0x49aba0,8),(0x49abc0,0x10),(0x49abe0,0x20)]:
    cs=callers(va)
    print(f"\n=== {hex(va)} or +0x1c,{hex(bit)}  callers={len(cs)} ===")
    for s in cs[:6]:
        # show push before call
        window=code[s-BASE-20:s-BASE]
        pushes=[]
        for j in range(len(window)):
            for ins in md.disasm(window[j:], s-20+j):
                if ins.address>=s: break
                if ins.mnemonic=="push":
                    pushes.append(ins.op_str)
                break
        print(f"  {hex(s)} pushes={pushes[-3:]}")
        # enclosing: look for mov ecx
        for line in dis(s-0x40, 0x50):
            if "ecx" in line and ("0x519868" in line or "lea" in line or "517" in line or "51eb" in line):
                print("   ", line)

# BSDATA: correlate 0x2c with known - and check 0x2d/0x2e as HP
bs=open("Taikou2 Original/BSDATA1.TR2","rb").read()
vals_2c=[]; vals_2d=[]; vals_2e=[]; vals_28=[]
for i in range(700):
    r=bs[i*59:(i+1)*59]
    vals_28.append(r[0x28])
    vals_2c.append(r[0x2c])
    vals_2d.append(r[0x2d])
    vals_2e.append(r[0x2e])

def stats(name,v):
    print(f"{name}: min={min(v)} max={max(v)} mean={sum(v)/len(v):.1f} "
          f"eq_2c_2d={sum(1 for a,b in zip(vals_2c,vals_2d) if a==b)} "
          f"2d>=2e={sum(1 for a,b in zip(vals_2d,vals_2e) if a>=b)}")

print("\n=== BSDATA HP-ish ===")
print("0x2c", min(vals_2c), max(vals_2c), "sample", vals_2c[13], vals_2c[16])  # nobunaga, hideyoshi
print("0x2d", min(vals_2d), max(vals_2d), "sample", vals_2d[13], vals_2d[16])
print("0x2e", min(vals_2e), max(vals_2e), "sample", vals_2e[13], vals_2e[16])
# How often 0x2c == 0x2d?
print("0x2c==0x2d", sum(1 for a,b in zip(vals_2c,vals_2d) if a==b))
print("0x2d==0x2e", sum(1 for a,b in zip(vals_2d,vals_2e) if a==b))
print("0x2e<=0x2d", sum(1 for a,b in zip(vals_2e,vals_2d) if a<=b))

# Famous: GAME_DATA says hideyoshi 体力80/100 - check which bytes
print("hideyoshi #16 bytes 0x28..0x2e", list(bs[16*59+0x28:16*59+0x2f]))
print("nobunaga #13", list(bs[13*59+0x28:13*59+0x2f]))

# Read 0x49a630 fully - max HP at +0x20
print("\n=== 0x49a630 (set current HP capped by +0x20) ===")
print("\n".join(dis(0x49a630, 0x30)))
