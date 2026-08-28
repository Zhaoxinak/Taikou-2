#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump SNDATA1 记录完整字节，并用武将 home_city / 城码 交叉验证记录是否按武将索引排列。"""
import os, json

DATA = r"F:\Games\Taikou2"
raw = open(os.path.join(DATA, "SNDATA1.TR2"), "rb").read()
body = raw[16:]
N, SZ = 833, 49
recs = [body[i*SZ:(i+1)*SZ] for i in range(N)]

# 加载武将 home_city
b = json.load(open("F:/Games/Taikou 2/scripts/bsdata.json", encoding="utf-8"))
gens = {c["id"]: c for c in b["characters"]}

def dump(i):
    r = recs[i]
    print(f"\n--- record[{i}] ---")
    print("  hex:", " ".join(f"{x:02x}" for x in r))
    # 找所有可能的小数值（城码 0..91 / 武将id 0..699）
    words = [r[o]|(r[o+1]<<8) for o in range(0, SZ-1, 1)]
    # 城码候选（0..91）出现在哪些偏移
    town_hits = [(o, r[o]) for o in range(SZ) if 0 <= r[o] <= 91 and r[o] != 0x0c]
    word_town = [(o, r[o]|(r[o+1]<<8)) for o in range(0, SZ-1) if 0 <= (r[o]|(r[o+1]<<8)) <= 91]
    print(f"  byte 城码候选(0..91,≠0c): {town_hits}")
    print(f"  word 城码候选(0..91): {word_town}")
    gen_hits = [(o, r[o]|(r[o+1]<<8)) for o in range(0, SZ-1) if 0 <= (r[o]|(r[o+1]<<8)) <= 699]
    print(f"  word 武将id候选(0..699): {gen_hits}")

# 交叉验证：若 record[i] 对应 general i，应有 home_city 或 lord 出现
print("=== 交叉验证：记录 i 是否含 general i 的 home_city/已知码 ===")
for gi in [0, 13, 16, 27]:
    g = gens[gi]
    hc = g["home_city"]
    r = recs[gi]
    hits = [(o, r[o]) for o in range(SZ) if r[o] == hc]
    whits = [(o, r[o]|(r[o+1]<<8)) for o in range(0, SZ-1) if (r[o]|(r[o+1]<<8)) == hc]
    print(f"  gen#{gi} {g['name']} home_city={hc}: byte命中={hits} word命中={whits}")

print("\n=== 完整 dump: records 0, 13, 16, 27 ===")
for i in [0, 13, 16, 27]:
    dump(i)
