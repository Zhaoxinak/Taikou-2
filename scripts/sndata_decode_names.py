#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Decode the 6 base + 3 id-override category name strings (GBK, 9 bytes each)."""
import struct
BASE = 0x400000
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"
with open(IMG, "rb") as f:
    MEM = f.read()

def gbk9(va):
    b = MEM[va-BASE:va-BASE+9]
    return b.split(b"\x00")[0].decode("gbk", "replace")

print("=== 6 base names (class0..5) ===")
bases = [(0,0x504938),(1,0x504941),(2,0x50494a),(3,0x504953),(4,0x50495c),(5,0x504965)]
for idx, va in bases:
    print(f"  class{idx} @0x{va:x}: {gbk9(va)!r}")

print("\n=== class1 override names (id 2/3/9) ===")
for idn, va in ((2,0x504a41),(3,0x504a38),(9,0x504a4a)):
    print(f"  id{idn} class1 @0x{va:x}: {gbk9(va)!r}  (替换默认的 米市行情)")

print("\n=== the 4 distinct name-sets ===")
std = [gbk9(v) for _,v in bases]
print("  Group A (212 ids):", std)
print("  Group B (id2):", [std[0], gbk9(0x504a41), std[2], std[3], std[4], std[5]])
print("  Group C (id3):", [std[0], gbk9(0x504a38), std[2], std[3], std[4], std[5]])
print("  Group D (id9):", [std[0], gbk9(0x504a4a), std[2], std[3], std[4], std[5]])

# byte-level dump for verification
print("\n=== raw bytes (hex) ===")
for label, va in (("class0",0x504938),("class1",0x504941),("class2",0x50494a),
                  ("class3",0x504953),("class4",0x50495c),("class5",0x504965),
                  ("id2",0x504a41),("id3",0x504a38),("id9",0x504a4a)):
    b = MEM[va-BASE:va-BASE+9]
    print(f"  {label} @0x{va:x}: {b.hex(' ')}")
