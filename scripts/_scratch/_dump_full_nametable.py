#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump full stride-9 name table and locate province / castle / town / type clusters."""
import os
SC = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(SC, "_unpacked_mem.bin")
BASE = 0x400000
data = open(BIN, "rb").read()
tbl_off = 0x506ca8 - BASE
def dec(i):
    chunk = data[tbl_off + i*9 : tbl_off + i*9 + 9]
    e = chunk.find(b"\x00"); e = len(chunk) if e < 0 else e
    return chunk[:e].decode("gbk", "replace")
names = [dec(i) for i in range(370)]
print("=== FULL 0x506ca8 name table (stride 9) ===")
for i in range(370):
    print(f"{i:3d}: {names[i]}")
