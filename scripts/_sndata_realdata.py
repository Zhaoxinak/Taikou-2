#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""找出 SNDATA 中真正含非旗标字节的记录（实体数据），并完整 dump 候选，寻找城码/武将id等价字段。"""
import os, json

DATA = r"F:\Games\Taikou2"
raw = open(os.path.join(DATA, "SNDATA1.TR2"), "rb").read()
body = raw[16:]
N, SZ = 833, 49
recs = [body[i*SZ:(i+1)*SZ] for i in range(N)]

FAMILY = {0x00,0x01,0x0c,0x0d,0x0e,0x0f,0xf3}
def is_real(r):
    return any(b not in FAMILY for b in r)

real = [i for i,r in enumerate(recs) if is_real(r)]
print(f"=== 含非旗标字节的记录数: {len(real)} / {N} ===")
print("索引:", real[:60])

# 这些记录的偏移值分布（非 family 字节）
from collections import Counter
off_vals = {o: Counter() for o in range(SZ)}
for i in real:
    for o,b in enumerate(recs[i]):
        if b not in FAMILY:
            off_vals[o][b]+=1
print("\n=== 非旗标字节出现的偏移及取值 ===")
for o in range(SZ):
    if off_vals[o]:
        top = off_vals[o].most_common(6)
        rng = (min(off_vals[o]), max(off_vals[o]))
        print(f"  off {o:2d}: count={sum(off_vals[o].values()):3d} range={rng} top={[(hex(v),n) for v,n in top]}")

# dump 前 8 条 real 记录完整 hex
print("\n=== 前 8 条 real 记录完整 hex ===")
for i in real[:8]:
    print(f"  [{i:3d}] " + " ".join(f"{x:02x}" for x in recs[i]))
