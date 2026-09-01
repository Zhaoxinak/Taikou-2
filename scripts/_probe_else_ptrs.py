#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_else_ptrs.py -- 跟 0x526c00/0x526c18/0x526c20/0x526c28/0x526c50 指针，解码 else 层资源名。
0x4ecf30(指针) 等取这些地址处的描述符；跟随并判断是 'X:NAME' 串还是 16B 资源表条目。"""
import os, struct
BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_unpacked_mem.bin')
BASE = 0x400000
code = open(BIN,'rb').read()
def rd32(va): return struct.unpack("<I", code[va-BASE:va-BASE+4])[0]
def rdstr(va, n=32):
    raw=code[va-BASE:va-BASE+n]; k=raw.find(0)
    if k<0: k=n
    if k==0: return ""
    try: return bytes(raw[:k]).decode('gbk')
    except Exception: return bytes(raw[:k]).decode('latin-1','replace')
def decode_res_array(b, maxn=8):
    out=[]
    for i in range(maxn):
        a=b+i*16
        if a-BASE+14>len(code): break
        raw=code[a-BASE:a-BASE+14]; nn=raw.find(0)
        if nn<0: nn=14
        if nn==0: break
        try: s=bytes(raw[:nn]).decode('gbk')
        except Exception: s=bytes(raw[:nn]).decode('latin-1','replace')
        if ':' not in s: break
        out.append(s)
    return out

PTRS = [0x526c00,0x526c18,0x526c20,0x526c28,0x526c50]
for p in PTRS:
    v = rd32(p)
    print(f"\n0x{p:06x} -> 0x{v:06x}" + (" (NULL)" if v==0 else ""))
    if v < BASE or v-BASE+4 > len(code):
        print("  越界/非指针，跳过")
        continue
    s = rdstr(v)
    print(f"  作为字符串: {s!r}")
    if ':' in s and s:
        print(f"  => 直接资源名: {s}")
        continue
    # 可能是 16B 资源表条目 / 指针数组
    arr = decode_res_array(v)
    if arr:
        print(f"  => 作为资源数组基址: {arr}")
        continue
    # 可能是 '指向资源名串的指针'
    v2 = rd32(v)
    if BASE <= v2 < BASE+len(code):
        s2 = rdstr(v2)
        if ':' in s2 and s2:
            print(f"  => 指向资源名串 0x{v2:06x}: {s2}")
            continue
    # 或 16B 条目内 [0]=名串指针
    if BASE <= v < BASE+len(code):
        v3 = rd32(v)
        if BASE <= v3 < BASE+len(code):
            s3 = rdstr(v3)
            if ':' in s3 and s3:
                print(f"  => 条目[0]=名串 0x{v3:06x}: {s3}")
