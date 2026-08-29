#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计全部 833 条 49B 记录的头部字段分布，判断记录类型/ID 编码方式。"""
import os
from collections import Counter

DATA = r"F:\Games\Taikou2"
raw = open(os.path.join(DATA, "SNDATA1.TR2"), "rb").read()
body = raw[16:]
N, SZ = 833, 49
recs = [body[i*SZ:(i+1)*SZ] for i in range(N)]

def w(r, o): return r[o] | (r[o+1]<<8)

h0 = Counter(w(r,0) for r in recs)
h4 = Counter(w(r,4) for r in recs)
h6 = Counter(r[6] for r in recs)
h12 = Counter(w(r,12) for r in recs)
print("record[0:2] 分布:", dict(h0.most_common(10)))
print("record[4:6] 分布:", dict(h4.most_common(10)))
print("record[6]   分布:", dict(h6.most_common(10)))
print("record[12:14]分布:", dict(h12.most_common(10)))

# 找 record[0:2] != 0x4bb8 的异常记录（可能是不同类型/实体）
anom = [i for i,r in enumerate(recs) if w(r,0)!=0x4bb8]
print(f"\nrecord[0:2]!=0x4bb8 的异常记录数: {len(anom)}")
print("异常索引:", anom[:40])
for i in anom[:12]:
    r=recs[i]
    print(f"  [{i:3d}] h0={w(r,0):04x} h4={w(r,4):04x} b6={r[6]:02x} h12={w(r,12):04x} | {r[:16].hex()}")

# record[0:2]==0x4bb8 中，record[4:6] 的取值分布（次 ID？）
b8 = [r for r in recs if w(r,0)==0x4bb8]
print(f"\nrecord[0:2]==0x4bb8 的记录数: {len(b8)}")
print("其中 record[4:6] 取值 (top20):", dict(Counter(w(r,4) for r in b8).most_common(20)))
print("其中 record[6]   取值 (top20):", dict(Counter(r[6] for r in b8).most_common(20)))
