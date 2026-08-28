#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析 SNDATA 49B 记录结构：分类记录、字段偏移分布、与武将/城镇交叉验证。"""
import os, json
from collections import Counter

DATA = r"F:\Games\Taikou2"
raw = open(os.path.join(DATA, "SNDATA1.TR2"), "rb").read()
assert raw[:16] == b"TAIKOU2_SCENARIO", raw[:16]
body = raw[16:]
N = 833
SZ = 49
recs = [body[i*SZ:(i+1)*SZ] for i in range(N)]

def classify(r):
    vals = set(r)
    if vals == {0}: return "zero"
    if vals <= {0,1}: return "bits01"
    if vals <= {0,0x0c}: return "bits0c"
    if len(vals) <= 3: return "few(%d)"%len(vals)
    return "data"

classes = Counter(classify(r) for r in recs)
print("=== 记录分类 (共 %d) ===" % N)
for k,v in classes.most_common():
    print(f"  {k}: {v}")

# 看每条记录第一个非零字节偏移，找"结构边界"
print("\n=== 前 12 条记录预览 ===")
for i in range(12):
    r = recs[i]
    hx = " ".join(f"{b:02x}" for b in r[:16])
    print(f"  [{i:3d}] {classify(r):8s} {hx}")

# 字段偏移分布：对 data 类记录，统计各偏移出现的高频值
data_recs = [r for r in recs if classify(r)=="data"]
print(f"\n=== data 类记录数: {len(data_recs)} ===")

# 每个偏移的字节值分布（仅 data 类）
print("\n=== 各偏移字节取值范围 (data 类, 取 min/max/常见值) ===")
for off in range(SZ):
    vals = [r[off] for r in data_recs]
    c = Counter(vals)
    top = c.most_common(3)
    print(f"  off {off:2d}: min={min(vals):3d} max={max(vals):3d} top={[(hex(v),n) for v,n in top]}")

# word 字段 off 0,4,12 的分布
print("\n=== word 字段分布 ===")
for off in [0,4,12]:
    words = [r[off] | (r[off+1]<<8) for r in data_recs]
    print(f"  off {off}: values={sorted(set(words))[:20]}")
