#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Separate SNDATA records into (a) genuine GBK-text records and
(b) binary/structured records, and dump readable strings from each."""
S1 = open('F:/Games/Taikou2/SNDATA1.TR2','rb').read()
HDR=16; STRIDE=49; N=833
def rec(i): return S1[HDR+i*STRIDE:HDR+i*STRIDE+STRIDE]

def rtype(b):
    s=set(b)
    if s <= {0,1,0x0c,0x0a}: return 'FLAG'
    return 'TEXT' if any(x>=0x80 for x in b) else 'MIXED'

def gbk_runs(b):
    """Yield maximal runs of bytes that decode as valid GBK (ascii or dbyte)."""
    runs=[]; cur=bytearray(); i=0
    while i < len(b):
        if b[i] < 0x80:
            cur.append(b[i]); i+=1; continue
        if i+1<len(b) and (0x40<=b[i+1]<=0xfe) and b[i+1]!=0x7f:
            cur+=b[i:i+2]; i+=2; continue
        # break
        if len(cur)>=1: runs.append(bytes(cur)); cur=bytearray()
        i+=1
    if cur: runs.append(bytes(cur))
    return runs

def longest_gbk_run(b):
    return max((len(r) for r in gbk_runs(b)), default=0)

def invalid_high_pairs(b):
    """count high bytes that are NOT start of a valid GBK dbyte AND not ascii."""
    c=0; i=0
    while i<len(b):
        if b[i]<0x80:
            i+=1; continue
        if i+1<len(b) and (0x40<=b[i+1]<=0xfe) and b[i+1]!=0x7f:
            i+=2; continue
        c+=1; i+=1
    return c

# Classify
text_recs=[]; binary_recs=[]
for i in range(N):
    if rtype(rec(i))!='TEXT': continue
    b=rec(i)
    lgr=longest_gbk_run(b)
    inv=invalid_high_pairs(b)
    if lgr>=6 and inv<=3:
        text_recs.append(i)
    else:
        binary_recs.append((i,lgr,inv))

print('Genuine GBK-text records: %d' % len(text_recs))
print('Binary/structured records: %d' % len(binary_recs))
print('\n--- sample GBK-text records (rec idx : decoded) ---')
for i in text_recs[:40]:
    b=rec(i)
    s=''.join(r.decode('gbk','replace') for r in gbk_runs(b) if len(r)>=1)
    s=''.join(ch if ch!='\ufffd' else '.' for ch in s)
    print('  %3d: %s' % (i, s))

print('\n--- binary records: (idx, longest_gbk_run, invalid_high_bytes) first 40 ---')
for t in binary_recs[:40]:
    print('  ', t)
if binary_recs:
    print('\n--- FULL hex dump of 3 binary records (idx, hex) ---')
    for i,_,_ in binary_recs[:3]:
        b=rec(i)
        print('rec %d:'%i, ' '.join('%02x'%x for x in b))
        print('      asc:', ''.join(chr(x) if 32<=x<127 else '.' for x in b))
