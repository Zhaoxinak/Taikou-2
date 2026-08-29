#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
S1=open('F:/Games/Taikou2/SNDATA1.TR2','rb').read()
HDR=16;STRIDE=49;N=833
def rec(i): return S1[HDR+i*STRIDE:HDR+i*STRIDE+STRIDE]
def runs(b):
    out=[];cur=bytearray();i=0
    while i<len(b):
        x=b[i]
        if x in (0x0c,0xf3):
            if cur:out.append(bytes(cur));cur=bytearray();i+=1;continue
        if x>=0x80:
            if i+1<len(b) and 0x40<=b[i+1]<=0xfe and b[i+1]!=0x7f:
                cur+=b[i:i+2];i+=2;continue
            else: cur.append(x);i+=1;continue
        else: cur.append(x);i+=1
    if cur:out.append(bytes(cur))
    return out
text_runs=[]
for i in range(N):
    for r in runs(rec(i)):
        if any(x>=0x80 for x in r): text_runs.append(r)
print('genuine text runs:',len(text_runs))

def strict_ok(t):
    try: t.decode('gbk'); return True
    except UnicodeDecodeError: return False

# LE as-is
le=sum(1 for r in text_runs if strict_ok(r))
# BE swap pairs
okbe=0
for r in text_runs:
    out=bytearray();i=0
    while i+1<len(r): out+=bytes([r[i+1],r[i]]);i+=2
    if len(r)%2: out.append(r[-1])
    if strict_ok(bytes(out)): okbe+=1
# XOR / ADD
best=[('LE',le),('BE',okbe)]
for C in range(256):
    ok=sum(1 for r in text_runs if strict_ok(bytes((c^C)&0xff for c in r)))
    best.append(('XOR%d'%C,ok))
for C in range(256):
    ok=sum(1 for r in text_runs if strict_ok(bytes((c+C)&0xff for c in r)))
    best.append(('ADD%d'%C,ok))
best.sort(key=lambda kv:-kv[1])
print('total runs:',len(text_runs))
for k,v in best[:10]:
    print('  %-8s %d (%.1f%%)'%(k,v,100*v/len(text_runs)))
