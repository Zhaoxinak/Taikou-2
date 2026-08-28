#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Empirical probe of SNDATA1.TR2 text encoding.
Goal: determine whether TEXT records are plain GBK, a KOEI private code page,
or mixed binary+text. Dump hex of sample records, measure GBK decode
success at byte level, characterize high-byte (0x80+) distribution.
"""
import sys
from collections import Counter

S1 = open('F:/Games/Taikou2/SNDATA1.TR2','rb').read()
HDR=16; STRIDE=49; N=833

def rec(i): return S1[HDR+i*STRIDE:HDR+i*STRIDE+STRIDE]

def rtype(b):
    s=set(b)
    if s <= {0,1,0x0c,0x0a}:
        return 'FLAG'
    return 'TEXT' if any(x>=0x80 for x in b) else 'MIXED'

types=[rtype(rec(i)) for i in range(N)]
print('type counts:', Counter(types))

# ---- byte-level GBK validity over TEXT records ----
# A byte stream is valid GBK if every byte is either ASCII (<=0x80 start)
# or part of a valid GBK double-byte sequence.
def gbk_valid_bytes(b):
    """Return fraction of bytes that participate in a valid GBK decode.
    Uses python's incremental gbk decoder; tracks consumed vs errors."""
    dec = []
    ok=0; total=len(b)
    i=0
    while i < len(b):
        # try 1-byte ascii
        if b[i] < 0x80:
            ok+=1; i+=1; continue
        # try 2-byte GBK
        if i+1 < len(b):
            pair=b[i:i+2]
            try:
                pair.decode('gbk')
                ok+=2; i+=2; continue
            except:
                pass
        # invalid -> count this byte as fail, advance 1
        i+=1
    return ok, total

tot_ok=0; tot_byt=0
rec_ok=0; rec_total=0
fail_records=[]
for i in range(N):
    if types[i]!='TEXT': continue
    rec_total+=1
    ok,byt=gbk_valid_bytes(rec(i))
    tot_ok+=ok; tot_byt+=byt
    frac=ok/byt if byt else 1.0
    if frac < 0.95:
        fail_records.append((i, round(frac,3)))
print('\nTEXT records: %d' % rec_total)
print('overall GBK-valid bytes: %d/%d = %.1f%%' % (tot_ok, tot_byt, 100*tot_ok/tot_byt))
print('TEXT recs with <95%% GBK-valid bytes: %d' % len(fail_records))
print('first 25 failing recs (idx, frac):', fail_records[:25])

# ---- high-byte distribution across TEXT records ----
hic=Counter()
for i in range(N):
    if types[i]!='TEXT': continue
    for x in rec(i):
        if x>=0x80: hic[x]+=1
print('\ndistinct high-byte values in TEXT:', len(hic))
print('top 30 high bytes (value:count):')
for v,c in hic.most_common(30):
    print('  0x%02x : %5d' % (v,c))

# ---- dump hex of first 6 TEXT records for visual inspection ----
print('\n=== hex dumps of first 8 TEXT records ===')
shown=0
for i in range(N):
    if types[i]!='TEXT': continue
    b=rec(i)
    hexs=' '.join('%02x'%x for x in b)
    # also show as latin1 to see ascii portions
    asc=''.join(chr(x) if 32<=x<127 else '.' for x in b)
    try: gbk=b.decode('gbk','replace')
    except: gbk='?'
    print('rec %3d | %s' % (i, hexs))
    print('       ascii: %s' % asc)
    print('       gbk  : %s' % gbk)
    shown+=1
    if shown>=8: break
