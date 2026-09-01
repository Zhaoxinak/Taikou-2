#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 6:
(A) definitive exact-byte search for ANY store to HP_A(0x514995)/HP_B(0x514835):
   66 89 05/0d..3d + addr ; 89 05..3d + addr ; c7 05..3d + addr + imm32 ; a3 + addr
(B) scan all absolute stores into 0x514800..0x5149ff block; cluster by function to find the setup fn.
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

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

HP = {0x514995: "HP_A", 0x514835: "HP_B"}

print("===== (A) definitive store-to-HP search =====")
for va in HP:
    ab = va.to_bytes(4, "little")
    found = []
    for pat in [bytes([0x66,0x89,0x05])+ab, bytes([0x89,0x05])+ab, bytes([0xc7,0x05])+ab,
                bytes([0x66,0x89,0x0d])+ab, bytes([0x89,0x0d])+ab,
                bytes([0x66,0x89,0x15])+ab, bytes([0x89,0x15])+ab,
                bytes([0xa3])+ab]:
        pos=0
        while True:
            i=MEM.find(pat,pos)
            if i<0: break
            found.append((i, pat.hex()))
            pos=i+1
    print(f"  {HP[va]} 0x{va:08x}: {len(found)} exact store patterns -> {found[:10]}")

print("\n===== (B) all absolute stores into 0x514800..0x5149ff =====")
# patterns: c7 05/0d../3d + addr(4) ; 89 05..3d + addr ; 66 89 05..3d + addr ; a3 + addr
stores = []  # (off, va, kind)
import struct
# iterate addresses in block
for lo in range(0x00, 0x100):
    for hi in (0x48,0x49):
        va = (0x51<<24)|(0x00 if False else 0)|(hi<<8)|lo  # wrong; build properly
# build properly:
for hi in (0x48,0x49):
    for lo in range(0,0x100):
        va = 0x510000 | (hi<<8) | lo
        if not (0x514800 <= va <= 0x5149ff):
            continue
        ab = va.to_bytes(4,"little")
        # c7 05..3d imm32
        for modrm in (0x05,0x0d,0x15,0x1d,0x25,0x2d,0x35,0x3d):
            pat=bytes([0xc7,modrm])+ab
            pos=0
            while True:
                i=MEM.find(pat,pos)
                if i<0: break
                stores.append((i,va,"c7_imm32")); pos=i+1
            pat=bytes([0x89,modrm])+ab
            pos=0
            while True:
                i=MEM.find(pat,pos)
                if i<0: break
                stores.append((i,va,"89_reg")); pos=i+1
            pat=bytes([0x66,0x89,modrm])+ab
            pos=0
            while True:
                i=MEM.find(pat,pos)
                if i<0: break
                stores.append((i,va,"66_89_reg")); pos=i+1
        pat=bytes([0xa3])+ab
        pos=0
        while True:
            i=MEM.find(pat,pos)
            if i<0: break
            stores.append((i,va,"a3_eax")); pos=i+1

# cluster by function: assume function = nearest preceding known CALL or align. Simpler: sort by off and print windows.
stores.sort()
print(f"  total absolute stores in block: {len(stores)}")
# group consecutive stores within 0x200 bytes
groups=[]
cur=[]
for off,va,kind in stores:
    if cur and off - cur[-1][0] > 0x300:
        groups.append(cur); cur=[]
    cur.append((off,va,kind))
if cur: groups.append(cur)
print(f"  clusters (gap<=0x300): {len(groups)}")
out=[]
for g in groups:
    start=g[0][0]; end=g[-1][0]
    out.append(f"\n--- cluster off {start:#08x}..{end:#08x} (va {BASE+start:#08x}..{BASE+end:#08x}) : {len(g)} stores ---")
    for off,va,kind in g:
        out.append(f"  {BASE+off:#08x}: {kind} -> 0x{va:08x}")
open(_ROOT + '/scripts/_hp6.txt',"w",encoding="utf-8").write("\n".join(out))
print("WROTE _hp6.txt ; clusters:", len(groups))
