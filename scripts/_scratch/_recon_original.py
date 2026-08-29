#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recon the original Taikou2 data files + anchor loaders via EXE filename strings."""
import os, struct, sys

BASE = r"F:\Games\Taikou 2\Taikou2 Original"
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"
BASE_VA = 0x400000

def hexdump(b, off=0, n=64):
    out=[]
    for i in range(0, min(n, len(b)), 16):
        chunk=b[i:i+16]
        h=' '.join(f'{x:02x}' for x in chunk)
        a=''.join(chr(x) if 32<=x<127 else '.' for x in chunk)
        out.append(f'{off+i:06x}  {h:<48}  {a}')
    return '\n'.join(out)

def try_deco(b, label):
    for enc in ('cp932','big5','gbk','euc-jp','shift_jis'):
        try:
            s=b.decode(enc)
            if any(0x4e00<=ord(c)<=0x9fff or 0x3040<=ord(c)<=0x30ff for c in s):
                print(f'    [{label}] {enc}: {s!r}')
        except Exception:
            pass

print("="*70)
print("FILE SIZES")
print("="*70)
for fn in sorted(os.listdir(BASE)):
    p=os.path.join(BASE,fn)
    if os.path.isfile(p):
        print(f"  {fn:16s} {os.path.getsize(p):8d}")

print("\n"+"="*70)
print("BSDATA1.TR2  (41300)")
print("="*70)
bs=open(os.path.join(BASE,"BSDATA1.TR2"),"rb").read()
print(f"  size={len(bs)}  41300/59={41300/59:.3f}  41300/58={41300/58:.3f}  41300/60={41300/60:.3f}")
print("  --- record 0 (59B) ---")
print(hexdump(bs[:59]))
print("  --- record 0 byte/word/dword ---")
r0=bs[:59]
for i in range(0,59,1):
    pass
print("  bytes:", ' '.join(f'{x:02x}' for x in r0))
print("  words (LE):", [struct.unpack_from('<H',r0,i)[0] for i in range(0,58,2)])
print("  dwords(LE):", [struct.unpack_from('<I',r0,i)[0] for i in range(0,56,4)])
# try decode name region at various offsets
for off in (0,4,6,8,10,12):
    try_deco(r0[off:off+16], f"r0+{off}")

print("\n"+"="*70)
print("SNDATA1.TR2  (40856)")
print("="*70)
sd=open(os.path.join(BASE,"SNDATA1.TR2"),"rb").read()
print(f"  size={len(sd)}")
print("  --- header 96B ---")
print(hexdump(sd[:96]))
# find magic
m=sd.find(b'TAIKOU2_SCENARIO')
print(f"  magic @ {m}: {sd[m:m+20]!r}")
# after magic, what?
after=sd[m+17:m+17+64]
print("  after-magic 64B:")
print(hexdump(after, m+17))
# search for ascii-ish runs
import re
runs=re.findall(rb'[ -~]{4,}', sd[:2000])
print("  ascii runs in first 2000B:", [r.decode('ascii') for r in runs])

print("\n"+"="*70)
print("TOWNTBL.DAT  (2560)")
print("="*70)
tt=open(os.path.join(BASE,"TOWNTBL.DAT"),"rb").read()
print(f"  size={len(tt)}  2560/20={2560/20}  2560/16={2560/16}  2560/32={2560/32}")
print(hexdump(tt[:80]))
print("  words:", [struct.unpack_from('<H',tt,i)[0] for i in range(0,40,2)])

print("\n"+"="*70)
print("TOWNPOS.DAT  (2450)")
print("="*70)
tp=open(os.path.join(BASE,"TOWNPOS.DAT"),"rb").read()
print(f"  size={len(tp)}  2450/10={2450/10}  2450/12={2450/12:.2f}  2450/14={2450/14:.2f}")
print(hexdump(tp[:80]))
print("  words:", [struct.unpack_from('<H',tp,i)[0] for i in range(0,40,2)])

print("\n"+"="*70)
print("SCAN UNPACKED IMAGE FOR FILENAME TOKENS (loader anchors)")
print("="*70)
img=open(IMG,"rb").read()
tokens=[b'TOWNTBL',b'TOWNPOS',b'SNDATA',b'BSDATA',b'SAVEDATA',b'HJMAPDAT',b'GAIJI',b'HBOBJ',b'.TR2',b'.DAT',b'.GRP',b'.KOS']
for tok in tokens:
    idx=0
    hits=[]
    while True:
        j=img.find(tok, idx)
        if j<0: break
        va=BASE_VA+j
        hits.append(va)
        idx=j+1
        if len(hits)>8: break
    if hits:
        print(f"  {tok.decode('ascii'):10s} -> {len(hits)} hits, e.g. VA {[hex(x) for x in hits[:6]]}")
print("\nDONE")
