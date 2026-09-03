#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Follow the category DB globals 0x526c50 / 0x526cb4 to find the 14-category table."""
import struct
BASE = 0x400000
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"
with open(IMG, "rb") as f:
    MEM = f.read()

def at(va, n):
    return MEM[va-BASE:va-BASE+n]
def rd32(va):
    return struct.unpack("<I", at(va,4))[0]
def is_ptr(v):
    return BASE <= v < BASE+len(MEM)

def gbk(b):
    # decode shift-jis? No, Chinese game -> GBK. Try GBK.
    try:
        return b.split(b"\x00")[0].decode("gbk", "replace")
    except Exception:
        return "?"

print("=== globals ===")
for g in (0x526c50, 0x526cb4, 0x526c58, 0x5152d0):
    v = rd32(g)
    print(f"  @0x{g:x} = 0x{v:x}  {'IN-IMAGE' if is_ptr(v) else 'OUT'}")

# 0x526c50 content
print("\n=== bytes @0x526c50 (32) ===")
print(" ".join(f"{b:02x}" for b in at(0x526c50, 32)))

# follow 0x526c50: it's likely a vtable ptr or a container. Read 0x526c50 as ptr to struct.
p = rd32(0x526c50)
print(f"\n@0x526c50 -> 0x{p:x}")
if is_ptr(p):
    print("  bytes:", " ".join(f"{b:02x}" for b in at(p, 32)))
    # maybe p is vtable; read p as vtable: first entry = method ptr
    vt0 = rd32(p)
    print(f"  vtable[0] @0x{p:x} = 0x{vt0:x}")
    # try reading as container: maybe [p] = ptr to array, [p+4]=count
    arr = rd32(p)
    cnt = rd32(p+4)
    print(f"  arr=0x{arr:x} cnt=0x{cnt:x}")

# 0x526cb4
p2 = rd32(0x526cb4)
print(f"\n@0x526cb4 -> 0x{p2:x}")
if is_ptr(p2):
    print("  bytes:", " ".join(f"{b:02x}" for b in at(p2, 32)))

# Search for the 6 known category-name strings as a contiguous block (the 6 names might be sequential)
names_off = 0x504938 - BASE
print(f"\n=== 6 names block @0x504938 (GBK) ===")
for i in range(6):
    off = names_off + i*9
    print(f"  [{i}] {gbk(at(0x504938+i*9, 9))!r}")
