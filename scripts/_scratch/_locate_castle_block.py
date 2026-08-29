#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Locate the castle block in the 0x506ca8 name table by sliding against the
92 known (home_city -> castle name) pairs from towns.json.

towns.json: id = home_city (0..91), name = "<castle>城".  The EXE stores the
castle names in this table at some contiguous index k, such that
name_table[k + c] == castle_name(c).  We find k by maximizing matches.
"""
import json, os

SC = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(SC, "_unpacked_mem.bin")
BASE = 0x400000
data = open(BIN, "rb").read()
tbl_off = 0x506ca8 - BASE

def decode_slot(raw):
    end = raw.find(b"\x00")
    if end < 0:
        end = len(raw)
    return raw[:end].decode("gbk", "replace")

def decode_table(stride):
    return [decode_slot(data[tbl_off + i*stride : tbl_off + i*stride + stride]) for i in range(370)]

# build ground truth: home_city -> stripped castle name
tj = json.load(open(os.path.join(SC, "towns.json"), encoding="utf-8"))
truth = {}  # c -> name (no 城)
for t in tj["towns"]:
    c = t["id"]
    nm = t["name"].replace("城", "")
    truth[c] = nm
cs = sorted(truth)

names = decode_table(9)

def score(k):
    return sum(1 for c in cs if 0 <= k + c < 370 and names[k + c] == truth[c])

best_k, best_s = -1, -1
for k in range(0, 370 - 92 + 1):
    s = score(k)
    if s > best_s:
        best_s, best_k = s, k
print(f"stride 9, best castle-block offset k = {best_k}  matches {best_s}/92")

# also try stride 14 for completeness
names14 = decode_table(14)
def score14(k):
    return sum(1 for c in cs if 0 <= k + c < 370 and names14[k + c] == truth[c])
b14 = max(range(0, 370-92+1), key=score14)
print(f"stride 14, best offset k = {b14}  matches {score14(b14)}/92")

# dump the located castle block
k = best_k
print("\n=== castle block @ offset %d (name_table[%d+c] = home_city c) ===" % (k, k))
for c in cs:
    idx = k + c
    mark = "OK" if names[idx] == truth[c] else "  <-- mismatch"
    print(f"  c={c:2d} idx={idx:3d}  {names[idx]!s:8s}  truth={truth[c]}{mark}")

# Save full corrected table (stride 9), with located blocks annotated
out = {
    "stride": 9,
    "verified_by": "sliding match vs towns.json (home_city->castle), offset k=%d, %d/92 match" % (k, best_s),
    "castle_block_offset": k,
    "province_names": names[0:49],     # placeholder; real province block TBD
    "place_names": names[49:292],
    "type_names": names[292:370],
    "castle_names_decoded": [names[k + c] for c in cs],
}
# Rebuild a clean province guess: the 39 entries before the castle block, if they look like provinces
pre = names[0:k]
out["pre_castle_block_0_to_%d" % (k-1)] = pre
json.dump(out, open(os.path.join(SC, "name_table.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote name_table.json (stride 9, castle block @ %d)" % k)
