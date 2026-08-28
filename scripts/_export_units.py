#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出 HJMAPDAT.DAT section A 为 9 类 x 20 属性(低4位) 矩阵，供复刻方接入。"""
import os, json, struct
DATA = "F:/Games/Taikou2"
hj = open(os.path.join(DATA, "HJMAPDAT.DAT"), "rb").read()
N = len(hj) // 1700
assert len(hj) % 1700 == 0, "size not multiple of 1700"

battles = []
for rec in range(N):
    A = hj[rec*1700: rec*1700 + 180]
    rows = []
    for u in range(9):
        b = A[u*20:(u+1)*20]
        lo = [x & 0xF for x in b]
        hi = [x >> 4 for x in b]
        rows.append({"lo": lo, "hi": hi})
    battles.append({
        "id": rec,
        "units": rows,   # 9 类 x {lo:[20], hi:[20]}；hi 在全部战役恒 0
    })

out = {
    "source": "C:HJMAPDAT.DAT section A (first 180B of each 1700B record)",
    "buffer": "0x512e58",
    "accessor": "0x439050 getLo(a,c)=buf[a*20+c]&0xF ; 0x4390c0 getHi=buf[a*20+c]>>4",
    "layout": "9 unit/force classes (a=0..8) x 20 attributes (c=0..19), each attribute a 4-bit value 0-15",
    "notes": "high nibble (hi) is 0 in all 38 battles; values observed 0/1/2; per-battle varying (scenario config, not global fixed stats)",
    "battle_count": N,
    "battles": battles,
}
with open("hjmapdat_units.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("wrote hjmapdat_units.json :", N, "battles x 9 units x 20 attrs")
# 快速统计：battle0 的 U0/U1 (互同) 与 U3/U4/U5 (全0) 验证
b0 = battles[0]["units"]
print("battle0 U0.lo:", b0[0]["lo"])
print("battle0 U3.lo (全零?):", b0[3]["lo"])
print("hi all zero across file:", all(u["hi"]==[0]*20 for b in battles for u in b["units"]))
