#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Definitively decode the EXE name table @ 0x506ca8 and verify stride.

Layout (per prior reverse work):
  0..48    49 provinces
  49..291  243 places (first 92 = the 92 castles)
  292..369 78 role/title types
Each entry is a fixed-stride slot holding a null-terminated GBK string.

Validation: home_city c (0..91) -> name_table[49 + c] must equal the
community castle list (三户, 八户, 弘前, ..., 清洲 at c=66). We test candidate
strides and pick the one that reproduces the known castle names.
"""
import json, os

SC = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(SC, "_unpacked_mem.bin")
BASE = 0x400000
data = open(BIN, "rb").read()
tbl_off = 0x506ca8 - BASE

# community ground truth: castle id -> name (no 城 suffix)
cc = json.load(open(os.path.join(SC, "castle_names.json"), encoding="utf-8"))
truth = [c["name"] for c in cc["castles"]]  # 200 entries, first 92 are the in-game castles

def decode_slot(raw):
    # raw = bytes of one slot; name is null-terminated GBK
    end = raw.find(b"\x00")
    if end < 0:
        end = len(raw)
    return raw[:end].decode("gbk", "replace")

def decode_table(stride):
    names = []
    for i in range(370):
        chunk = data[tbl_off + i*stride : tbl_off + i*stride + stride]
        names.append(decode_slot(chunk))
    return names

best = None
for stride in (9, 14):
    names = decode_table(stride)
    # castle block == names[49:49+92]
    block = names[49:49+92]
    match = sum(1 for a, b in zip(block, truth[:92]) if a == b)
    # also measure "cleanliness": # of slots with no replacement char and length 1..6 chars
    clean = sum(1 for n in names if "\ufffd" not in n and 0 < len(n) <= 8)
    empties = sum(1 for n in names if n == "")
    print(f"stride {stride}: castle-match {match}/92, clean {clean}/370, empty {empties}")
    if best is None or match > best[1]:
        best = (stride, match, names, block)

stride, match, names, block = best
print(f"\n==> chosen stride = {stride} (castle match {match}/92)")

# detailed castle block dump vs truth
print("\nidx  name_table[49+c]   community")
for c in range(92):
    print(f"  {c:2d}  {block[c]!s:10s}   {truth[c]}")

# province block (0..48) and type block (292..369)
print("\nprovinces (0..48):")
print("  ", [names[i] for i in range(49)])
print("\ntypes (292..369):")
print("  ", [names[i] for i in range(292, 370)])

# save clean decode
out = {
    "stride": stride,
    "verified_by": "cross-check home_city->castle name_table[49+c] vs community castle_names.json",
    "province_names": names[0:49],
    "place_names": names[49:292],
    "type_names": names[292:370],
}
json.dump(out, open(os.path.join(SC, "name_table.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote name_table.json (stride %d)" % stride)
