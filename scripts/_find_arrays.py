#!/usr/bin/env python3
"""Empirical scan of SAVEDATA block 0 for assignment arrays.
Block 0 = file[0x198 : 0x198+0x5000]. Plaintext (XOR key 0).
Look for:
  - 92 LE-words all in [0,699]  (castle owner = general ID)
  - 92 LE-words all in [0,91]   (unlikely but check)
  - 92 bytes  all in [0,40]     (castle owner = clan ID)
  - 700 bytes all in [0,91]      (general -> stationed castle)
  - 700 bytes all in [0,699]     (general -> lord general)
Report offset, raw sample, and distinct-value set.
"""
import struct

P = r"F:/Games/Taikou2/SAVEDATA.TR2"
d = open(P, "rb").read()
BLK = 0x198
END = BLK + 0x5000
seg = d[BLK:END]

def run_words(off, n, lo, hi):
    w = struct.unpack("<%dH" % n, seg[off:off+n*2])
    return all(lo <= x <= hi for x in w), w

def run_bytes(off, n, lo, hi):
    b = seg[off:off+n]
    return all(lo <= x <= hi for x in b), b

cands = []
# 92-word arrays
for off in range(0, len(seg)-92*2, 1):
    ok, w = run_words(off, 92, 0, 699)
    if ok:
        cands.append((BLK+off, "92W[0,699]", list(w[:14])))
# 92-byte clan arrays
for off in range(0, len(seg)-92, 1):
    ok, b = run_bytes(off, 92, 0, 40)
    if ok and len(set(b)) > 10:
        cands.append((BLK+off, "92B[0,40]", list(b[:14])))
# 700-byte general->castle
for off in range(0, len(seg)-700, 1):
    ok, b = run_bytes(off, 700, 0, 91)
    if ok:
        cands.append((BLK+off, "700B[0,91]", list(b[:14])))
# 700-byte general->lord
for off in range(0, len(seg)-700, 1):
    ok, b = run_bytes(off, 700, 0, 699)
    if ok:
        cands.append((BLK+off, "700B[0,699]", list(b[:14])))

# de-dup nearby
seen = []
for c in sorted(cands):
    if not any(abs(c[0]-s[0]) < 8 for s in seen):
        seen.append(c)
print(f"found {len(seen)} candidate arrays")
for off, kind, samp in seen[:40]:
    print(f"  file@{off:#06x}  {kind}  sample={samp}")
