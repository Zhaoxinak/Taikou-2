#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Precise SNDATA record type-map + text extraction.
- type per record: FLAG (only 00/01/0c/0a), TEXT (has >=0x80 runs), MIXED
- extract GBK string slots (split on 0x0c / 0xf3 separators)
- compare S1 vs S2 for flag records
"""
import re

S1 = open('F:/Games/Taikou2/SNDATA1.TR2','rb').read()
S2 = open('F:/Games/Taikou2/SNDATA2.TR2','rb').read()
HDR=16; STRIDE=49; N=833

def rec(d,i): return d[HDR+i*STRIDE:HDR+i*STRIDE+STRIDE]

def rtype(b):
    s=set(b)
    if s <= {0,1,0x0c,0x0a}:
        return 'FLAG'
    hi=any(x>=0x80 for x in b)
    return 'TEXT' if hi else 'MIXED'

# 1) type map + boundaries
types=[rtype(rec(S1,i)) for i in range(N)]
from collections import Counter
print('type counts:', Counter(types))

# find contiguous runs
print('\nrecord-type runs:')
prev=None;st=0
for i,t in enumerate(types):
    if t!=prev:
        if prev is not None:
            print('  %-5s [%d:%d] (%d)' % (prev,st,i, i-st))
        prev=t;st=i
print('  %-5s [%d:%d] (%d)' % (prev,st,N,N-st))

# 2) extract text slots from a record (best-effort GBK)
def slots(b):
    out=[]; cur=bytearray(); 
    i=0
    while i<len(b):
        x=b[i]
        if x in (0x0c,0xf3):  # separator/terminator
            if cur: out.append(bytes(cur)); cur=bytearray()
            i+=1; continue
        if x>=0x80:
            # take pair if next is valid trail
            if i+1<len(b) and (0x40<=b[i+1]<=0xfe) and b[i+1]!=0x7f:
                cur+=b[i:i+2]; i+=2; continue
            else:
                cur.append(x); i+=1; continue
        else:
            cur.append(x); i+=1
    if cur: out.append(bytes(cur))
    return out

def dec(s):
    try: return s.decode('gbk','replace')
    except: return s.decode('latin1','replace')

print('\n=== sample TEXT-record decoding (every 20th text rec) ===')
shown=0
for i in range(N):
    if types[i]!='TEXT': continue
    if (i%20)!=0: continue
    sl=slots(rec(S1,i))
    deco=[dec(s) for s in sl if len(s)>0]
    print('rec %3d: %s' % (i, ' | '.join(deco)))
    shown+=1
    if shown>=25: break

print('\n=== FLAG-record S1 vs S2 differences (rec 0..15) ===')
for i in range(16):
    a=rec(S1,i); b=rec(S2,i)
    diff=[j for j in range(49) if a[j]!=b[j]]
    if i<=3 or diff:
        print('rec %2d diffs@%s  S1=%s  S2=%s' % (i, diff, a.hex(), b.hex()))
