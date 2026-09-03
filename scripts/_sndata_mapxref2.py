#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E8-相对调用扫描: 收集对 map 方法(及 dispatch)的直接 call 调用者。"""
import struct
BASE = 0x400000
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"
with open(IMG, "rb") as f:
    MEM = f.read()

TARGETS = {0x478990, 0x478a20, 0x478770, 0x4787c0, 0x47be00, 0x478a20,
           0x47bed0, 0x4624f0, 0x462fd0}
# 仅扫描代码段(避开明显数据密集尾部)
START_OFF = 0x401000 - BASE
END_OFF   = 0x4f5000 - BASE

callers = {t: [] for t in TARGETS}
off = START_OFF
while off < END_OFF - 5:
    if MEM[off] == 0xE8:
        rel = struct.unpack("<i", MEM[off+1:off+5])[0]
        va = off + BASE
        tgt = (va + 5 + rel) & 0xFFFFFFFF
        if tgt in TARGETS:
            callers[tgt].append(va)
    off += 1

for t in sorted(TARGETS):
    cs = callers[t]
    print(f"--- callers of {t:#08x} ({len(cs)}):")
    for c in cs:
        print(f"    {c:#08x}")
