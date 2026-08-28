#!/usr/bin/env python3
# xref: find occurrences of a VA as a 4-byte LE immediate anywhere in the image.
# Usage: python _xref.py 0x504603 0x504941 0x503b08 0x504658
import sys, struct

BIN = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
data = open(BIN, "rb").read()

targets = [int(a, 16) for a in sys.argv[1:]]
print(f"image {len(data)} bytes, base 0x{BASE:x}", flush=True)
for va in targets:
    imm = struct.pack("<I", va)
    hits = []
    start = 0
    while True:
        i = data.find(imm, start)
        if i < 0:
            break
        hits.append(BASE + i)
        start = i + 1
    print(f"\nVA 0x{va:06x} ({imm.hex()}) -> {len(hits)} xrefs")
    for h in hits:
        print(f"    ref @ 0x{h:06x}")
