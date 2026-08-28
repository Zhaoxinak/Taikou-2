#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 SNDATA 各记录 43B payload，找值域被收紧到 城码(0..91) / 武将id(0..699) 的偏移 → 强字段信号。"""
import os
from collections import Counter

DATA = r"F:\Games\Taikou2"
raw = open(os.path.join(DATA, "SNDATA1.TR2"), "rb").read()
body = raw[16:]
N, SZ = 833, 49
recs = [body[i*SZ:(i+1)*SZ] for i in range(N)]
FILL = {0x00,0x01,0x0c,0x0d,0x0e,0x0f,0xf3,0xff}

# payload = rec[6:49]
def payloads():
    for r in recs:
        yield r[6:49]

# 对每个 payload 偏移 o(0..42)，统计非填充字节的 (min,max,count)
stats = {}
for o in range(43):
    vals = []
    for p in payloads():
        b = p[o]
        if b not in FILL:
            vals.append(b)
    if vals:
        stats[o] = (min(vals), max(vals), len(vals))

print("=== payload 偏移中 字节值域 ≤91 (候选城码字段) ===")
for o in range(43):
    if o in stats:
        mn,mx,c = stats[o]
        if mx <= 91 and c >= 20:
            print(f"  payload[{o}] (rec+{6+o}): min={mn} max={mx} count={c}  <<< 城码候选")

print("\n=== payload 偏移中 字节值域 92..255 但分布集中 (候选 clan/标志) ===")
for o in range(43):
    if o in stats:
        mn,mx,c = stats[o]
        if 92 <= mx <= 255 and c >= 20:
            print(f"  payload[{o}] (rec+{6+o}): min={mn} max={mx} count={c}")

# word 级：找 rec 偏移 w(偶数, 0..47) 处 word 值域 ≤699 (候选武将id) — 仅看真实记录
print("\n=== word 级 值域 0..699 (候选武将id) 的 rec 偏移 ===")
wordstats={}
for o in range(0, SZ-1, 1):
    vals=[]
    for r in recs:
        w = r[o] | (r[o+1]<<8)
        # 排除全填充组合
        if r[o] not in FILL or r[o+1] not in FILL:
            # 仅当 word 不是常见的填充对
            if w not in (0x0c0c,0xf3f3,0x0f0f,0x0101,0xffff,0x0000,0x0a0a):
                vals.append(w)
    if vals:
        wordstats[o]=(min(vals),max(vals),len(vals))
for o in range(0,SZ-1):
    if o in wordstats:
        mn,mx,c=wordstats[o]
        if mx<=699 and c>=15:
            print(f"  rec[{o}:{o+2}] word: min={mn} max={mx} count={c}  <<< 武将id候选")
