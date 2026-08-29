#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze HJMAPDAT.DAT record structure (38 records x 1700 bytes)."""
import struct, collections

DAT = r"F:/Games/Taikou2/HJMAPDAT.DAT"
with open(DAT, "rb") as f:
    buf = f.read()

print(f"file size = {len(buf)} (0x{len(buf):x})")
REC = 1700
nrec = len(buf) // REC
print(f"records of {REC} bytes -> {nrec} records (mod={len(buf)%REC})")

def stats(region, name):
    c = collections.Counter(region)
    vals = sorted(c)
    mn = min(region); mx = max(region)
    print(f"  [{name}] len={len(region)} min={mn} max={mx} distinct={len(c)}")
    # show top value histogram
    top = c.most_common(8)
    print(f"      top: " + ", ".join(f"{v}:{n}" for v,n in top))
    return mn, mx

for r in (0, 1, 2, 19, 37):
    if r >= nrec: 
        continue
    rec = buf[r*REC:(r+1)*REC]
    print(f"\n=== record {r} (offset 0x{r*REC:x}) ===")
    # header bytes
    print("  first 32 bytes:", " ".join(f"{b:02x}" for b in rec[:32]))
    print("  u16 LE [0:16]:", [struct.unpack_from("<H", rec, i)[0] for i in range(0,16,2)])
    # three sections per loader: 180 + 760 + 760
    A = rec[0:180]
    B = rec[180:180+760]
    C = rec[180+760:180+760+760]
    stats(A, "A(0..180)")
    stats(B, "B(180..940)")
    stats(C, "C(940..1700)")
    # try 4bpp decode of B and C -> 1520 cells each
    for lbl, sec in (("B", B), ("C", C)):
        cells = []
        for byte in sec:
            cells.append(byte & 0xF)
            cells.append(byte >> 4)
        cc = collections.Counter(cells)
        print(f"    {lbl} as 4bpp -> 1520 cells, distinct={len(cc)}, max={max(cells)}, top={cc.most_common(6)}")
    # try grid hypotheses for section B (1 byte/cell)
    for (w,h) in [(40,19),(19,40),(38,20),(20,38),(10,76),(76,10),(8,95),(95,8),(50,15),(15,50)]:
        if w*h == len(B):
            print(f"    B fits {w}x{h} @1bpp/cell")
    for (w,h) in [(40,38),(38,40),(20,76),(76,20),(19,80),(80,19),(16,95),(95,16),(10,152),(8,190),(4,380),(5,304),(2,760),(1,760)]:
        if w*h == 1520:
            print(f"    B fits {w}x{h} @4bpp(2cells/byte)=1520 cells")
