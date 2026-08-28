# -*- coding: utf-8 -*-
"""Analyze HJMAPDAT.DAT section A (9 classes x 20 attrs, low nibble) across 38 battles.
Goal: infer naming of 9 rows (classes) and 20 cols (attributes) from value patterns.
Reads the authoritative data file, not the static EXE buffer.
"""
import json, sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from collections import defaultdict
import statistics as st

DAT = "F:/Games/Taikou2/HJMAPDAT.DAT"
data = open(DAT, 'rb').read()
N = len(data) // 1700
print('battles =', N, 'rem', len(data) % 1700)

# build 38 x 9 x 20 low-nibble matrix
mat = []
for b in range(N):
    A = data[b*1700: b*1700+180]
    rows = []
    for u in range(9):
        row = [A[u*20 + c] & 0xf for c in range(20)]
        rows.append(row)
    mat.append(rows)

# per (class, attr): mean across battles
ca = defaultdict(list)
for b in range(N):
    for u in range(9):
        for c in range(20):
            ca[(u, c)].append(mat[b][u][c])

print('\n=== PER-CLASS profile (mean of 20 attrs over 38 battles) ===')
for u in range(9):
    means = [round(st.mean(ca[(u,c)]), 2) for c in range(20)]
    print(' class%2d: %s' % (u, means))

print('\n=== PER-ATTRIBUTE stats (mean,std,min,max) over all 9*38 cells ===')
attr_info = []
for c in range(20):
    vals = [ca[(u,c)][i] for u in range(9) for i in range(len(ca[(u,c)]))]
    attr_info.append((c, st.mean(vals), st.pstdev(vals), min(vals), max(vals)))
for c, m, sd, lo, hi in attr_info:
    print('  attr%2d: mean=%4.2f std=%4.2f range[%d..%d]' % (c, m, sd, lo, hi))

# Which attributes best separate the 9 classes? (largest between-class variance)
print('\n=== ATTRIBUTES that DISCRIMINATE classes (high between-class spread) ===')
disc = []
for c in range(20):
    class_means = [st.mean(ca[(u,c)]) for u in range(9)]
    disc.append((c, max(class_means)-min(class_means), class_means))
disc.sort(key=lambda t: -t[1])
for c, spread, cm in disc[:12]:
    print('  attr%2d spread=%4.2f class_means=%s' % (c, spread, [round(x,1) for x in cm]))

# Are the 9 class profiles stable across battles? (consistency = fixed soldier types)
print('\n=== CLASS PROFILE STABILITY across battles (per attr, across-battle std) ===')
for u in range(9):
    across_std = [round(st.pstdev(ca[(u,c)]), 2) for c in range(20)]
    print(' class%2d across-battle std: %s' % (u, across_std))
