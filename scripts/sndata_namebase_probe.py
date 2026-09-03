#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe the 6 'name base' values: are they string pointers or inline strings?"""
import struct
BASE = 0x400000
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"
with open(IMG, "rb") as f:
    MEM = f.read()

def at(va, n):
    return MEM[va-BASE:va-BASE+n]

def is_printable(b):
    return all(32 <= c < 127 or c in (9, 10, 13) for c in b)

print("=== raw bytes @0x504938 (40 bytes) ===")
raw = at(0x504938, 0x48)
print(" ".join(f"{b:02x}" for b in raw))

bases = [0x504938, 0x504941, 0x50494a, 0x504953, 0x50495c, 0x504965]
print("\n=== 6 name bases: value + if ptr->ASCII ===")
for b in bases:
    v = struct.unpack("<I", at(b, 4))[0]
    print(f"  @0x{b:x} = 0x{v:x}", end="")
    # if v looks like an image pointer, try reading ascii there
    if BASE <= v < BASE + len(MEM):
        s = at(v, 24)
        if is_printable(s[:16]):
            txt = s[:16].decode("ascii", "replace").rstrip("\x00")
            print(f"  -> ASCII@{v:x}: '{txt}'", end="")
    print()

# name base id2/3/9 overrides
print("\n=== id overrides ===")
for name, b in (("id2",0x504a41),("id3",0x504a38),("id9",0x504a4a)):
    v = struct.unpack("<I", at(b, 4))[0]
    print(f"  {name} @0x{b:x} = 0x{v:x}", end="")
    if BASE <= v < BASE + len(MEM):
        s = at(v, 24)
        if is_printable(s[:16]):
            print(f"  -> ASCII@{v:x}: '{s[:16].decode('ascii','replace').rstrip(chr(0))}'", end="")
    print()
