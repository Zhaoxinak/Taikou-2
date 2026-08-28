#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Classify the 833 x 49-byte SNDATA records.
Strategy:
 1. byte-statistics per record  -> cluster by content shape
 2. inter-scenario diff (SNDATA1 vs SNDATA2) -> identical=static/master,
    differing=scenario state.
 3. dump a few representative records in full hex + interpreted form.
"""
import struct, sys

S1 = open('F:/Games/Taikou2/SNDATA1.TR2','rb').read()
S2 = open('F:/Games/Taikou2/SNDATA2.TR2','rb').read()
assert len(S1)==len(S2)==40856, (len(S1),len(S2))

SIG=b'TAIKOU2_SCENARIO'
assert S1[:16]==SIG and S2[:16]==SIG, 'signature mismatch'

HDR=16
STRIDE=49
N=(40856-16-23)//STRIDE   # 833
print('records N =', N, ' residual =', (40856-16)%STRIDE, 'tail=', S1[40833:40856].hex())

def rec(data, i):
    return data[HDR+i*STRIDE : HDR+i*STRIDE+STRIDE]

def stats(b):
    n=len(b)
    z=b.count(0)
    # bytes 1..127 nonzero (low ascii / small ints)
    lo=[x for x in b if 0<x<0x80]
    hi=[x for x in b if x>=0x80]      # candidate GBK lead/trail
    # GBK-ish: high bytes in pairs
    gbk_pairs=0
    i=0
    while i+1<n:
        if b[i]>=0x81 and b[i]<=0xfe and b[i+1]>=0x40 and b[i+1]<=0xfe and b[i+1]!=0x7f:
            gbk_pairs+=1; i+=2
        else:
            i+=1
    return dict(n=n, zero=z, lo=len(lo), hi=len(hi), gbk_pairs=gbk_pairs,
                maxb=max(b), minnz=min((x for x in b if x), default=0))

# ---- per-record classification ----
rows=[]
for i in range(N):
    a=rec(S1,i); b=rec(S2,i)
    sa=stats(a); sb=stats(b)
    diff=sum(1 for x,y in zip(a,b) if x!=y)
    # dominant type guess
    if sa['hi']>=6 and sa['gbk_pairs']>=2:
        typ='TEXT'
    elif sa['lo']>=30 and sa['hi']==0:
        typ='INTS'
    elif sa['zero']>=40:
        typ='SPARSE'
    else:
        typ='MIXED'
    rows.append((i, typ, diff, sa, sb))

# histogram
from collections import Counter
hist=Counter(r[1] for r in rows)
print('\n=== type histogram (SNDATA1) ===')
for k,v in hist.most_common():
    print('  %-7s %d' % (k,v))

# inter-scenario diff buckets
ident=sum(1 for r in rows if r[2]==0)
small=sum(1 for r in rows if 0<r[2]<=4)
med=sum(1 for r in rows if 4<r[2]<=20)
big=sum(1 for r in rows if r[2]>20)
print('\n=== inter-scenario diff (SNDATA1 vs SNDATA2) ===')
print('  identical (static/master): %d' % ident)
print('  tiny (<=4 bytes):          %d' % small)
print('  medium (5-20):             %d' % med)
print('  large (>20):               %d' % big)

# show record index ranges per type
print('\n=== record index ranges per type ===')
cur=None; start=None
def flush(t,s,e):
    print('  %-7s [%d:%d]  (%d recs)' % (t,s,e+1,e-s+1))
for i,(t,_,_,_,_) in enumerate(rows):
    if t!=cur:
        if cur is not None: flush(cur,start,i-1)
        cur=t; start=i
flush(cur,start,len(rows)-1)

def dump(i, label):
    a=rec(S1,i); b=rec(S2,i)
    print('\n--- record %d (%s) ---' % (i,label))
    print('  S1:', a.hex())
    print('  S2:', b.hex())
    # try interpret as GBK where high bytes
    print('  S1 txt-ish:', ' '.join('%02x'%x for x in a))

print('\n\n===== SAMPLE DUMPS =====')
for i in [0,1,2,3,10,50,100,150,300,500,700,832]:
    dump(i, rows[i][1])
