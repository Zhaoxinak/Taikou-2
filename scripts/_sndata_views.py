#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0：dump 每类型代表记录的 3 文本视图 (rec+6/19/32)，判 payload 是否文本。"""
import struct
from collections import Counter, OrderedDict

def read_records(path):
    d = open(path, 'rb').read()
    body = d[16:]
    return [body[i*49:(i+1)*49] for i in range(len(body)//49)]

def gbk(b):
    z = b.find(b'\x00')
    seg = b if z < 0 else b[:z]
    for cut in range(len(seg), -1, -1):
        try:
            return seg[:cut].decode('gbk'), cut
        except: continue
    return "", 0

def dump(path, max_types=18):
    recs = read_records(path)
    # 按 type 分组取第一个
    bytype = OrderedDict()
    for r in recs:
        t = struct.unpack_from('<H', r, 0)[0] & 0xff
        bytype.setdefault(t, []).append(r)
    print(f"### {path} 共 {len(recs)} 条, {len(bytype)} 种 type\n")
    for t, grp in list(bytype.items())[:max_types]:
        r = grp[0]
        idw, subw, flagrel = struct.unpack_from('<HHH', r, 0)
        v6 = gbk(r[6:49]); v19 = gbk(r[19:49]); v32 = gbk(r[32:49])
        # 三段是否含 null（文本特征）
        hasnull6 = (b'\x00' in r[6:49]); hasnull19 = (b'\x00' in r[19:49]); hasnull32 = (b'\x00' in r[32:49])
        print(f"type=0x{t:02x}({t})  idw=0x{idw:04x} subw=0x{subw:04x} flagrel=0x{flagrel:04x}  x{len(grp)}")
        print(f"   v[6]len{v6[1]:2d}: {v6[0]!r}")
        print(f"  v[19]len{v19[1]:2d}: {v19[0]!r}")
        print(f"  v[32]len{v32[1]:2d}: {v32[0]!r}")
        print(f"   null? 6:{hasnull6} 19:{hasnull19} 32:{hasnull32}  raw={r.hex()}")

dump('Taikou2 Original/SNDATA1.TR2')
