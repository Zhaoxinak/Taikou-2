#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析 HJMAPDAT.DAT section A：9 单位类型 × 40 nibble 属性；并 dump 名表候选找兵种名。"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
DATA = "F:/Games/Taikou2"

def rd(fname):
    return open(os.path.join(DATA, fname), "rb").read()

hj = rd("HJMAPDAT.DAT")
N = len(hj) // 1700
print("HJMAPDAT.DAT battles:", N, "rem", len(hj) % 1700)

def battle(rec):
    base = rec * 1700
    A = hj[base:base+180]
    return A

def unit_rows(A):
    rows = []
    for u in range(9):
        b = A[u*20:(u+1)*20]
        lo = [x & 0xf for x in b]
        hi = [x >> 4 for x in b]
        rows.append((lo, hi))
    return rows

# 检查跨战役一致性：battle0 vs 其他
b0 = unit_rows(battle(0))
print("\n=== battle0 9 单位类型 (lo=低nibble属性0-19, hi=高nibble属性20-39) ===")
for u,(lo,hi) in enumerate(b0):
    print(f"  U{u}: lo={lo}")
    print(f"      hi={hi}")

# 跨战役对比：每个 (u,c) 是否恒定
print("\n=== 跨战役 (U,c) 取值分布 (统计每格出现的不同值) ===")
from collections import defaultdict
variation = defaultdict(set)
for rec in range(N):
    rows = unit_rows(battle(rec))
    for u in range(9):
        for c in range(20):
            variation[(u,c,'lo')].add(rows[u][0][c])
            variation[(u,c,'hi')].add(rows[u][1][c])
const_lo = sum(1 for k in variation if k[2]=='lo' and len(variation[k])==1)
const_hi = sum(1 for k in variation if k[2]=='hi' and len(variation[k])==1)
print(f"  lo 格中恒定(单值)数: {const_lo}/180 ; hi 格中恒定数: {const_hi}/180")

# 单位类型间对比：是否 9 行彼此不同（=9种兵种）还是重复
print("\n=== battle0 各 U 行是否互异 ===")
seen = {}
for u,(lo,hi) in enumerate(b0):
    key = (tuple(lo), tuple(hi))
    seen.setdefault(key, []).append(u)
for key, us in seen.items():
    print(f"  行 {us} 相同: lo={key[0]} hi={key[1]}")

# U0 是否全 0（可能是"无/空"占位）?
allzero = [u for u,(lo,hi) in enumerate(b0) if all(x==0 for x in lo) and all(x==0 for x in hi)]
print("\n  battle0 全零单位行:", allzero, " (若含0, 可能 U0=空/无兵)")

# ── 名表候选 dump (0x506ca8, 370条 GBK 变长 null) ──
mem = open(_ROOT + '/scripts/_unpacked_mem.bin',"rb").read()
BASE=0x400000
def mrd(va,sz): return mem[va-BASE:va-BASE+sz]
tbl = mrd(0x506ca8, 370*9)
names=[]
for i in range(370):
    e = tbl[i*9:(i+1)*9]
    try: t = e.split(b"\x00")[0].decode("gbk")
    except: t=""
    names.append(t)
print("\n=== 名表 0x506ca8 条目 290-369 ===")
for i in range(290,370):
    print(f"  [{i:3d}] {names[i]}")
