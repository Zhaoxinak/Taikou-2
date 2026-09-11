#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find G0 军资金 wrapper + parent function + ebp field map + getters."""
from __future__ import annotations

import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(r"F:\Games\Taikou 2")

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

code = open("scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
out = open("scripts/_scratch/_eval_g0.txt", "w", encoding="utf-8")


def dump(va, n, title=""):
    out.write(f"\n=== {title or hex(va)} ===\n")
    for i in md.disasm(code[va - BASE : va - BASE + n], va):
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")


# Search lea with disp near 0x50b6ba (G0)
for disp in range(0x50B6B0, 0x50B6D0):
    needle = struct.pack("<I", disp)
    st = 0
    while True:
        j = code.find(needle, st)
        if j < 0:
            break
        # check if lea
        if j >= 3 and code[j - 3] == 0x8D:
            out.write(f"lea? @{BASE+j-3:#x} disp={disp:#x}\n")
            dump(BASE + j - 0x40, 0x60, f"near {disp:#x}")
        st = j + 1

# Parent: find function containing all wrappers — start ~0x497a00
dump(0x497A00, 0x100, "parent head 497a00")

# Find callers of 0x497xxx block - look for call into 0x497a80 or similar entry
# Walk back from first wrapper gate to find real function entry
dump(0x497A80, 0x80, "497a80")
dump(0x497900, 0x100, "497900")

# getters
for va, name in [
    (0x49BDE0, "49bde0 support?"),
    (0x49BDF0, "49bdf0 horse?"),
    (0x49BE00, "49be00 gun?"),
]:
    dump(va, 0x40, name)

# Find e8 targeting range 0x497af0..0x498400
targets = {}
for i in range(len(code) - 5):
    if code[i] != 0xE8:
        continue
    rel = struct.unpack_from("<i", code, i + 1)[0]
    tgt = BASE + i + 5 + rel
    if 0x497A00 <= tgt < 0x498500:
        targets.setdefault(tgt, []).append(BASE + i)

out.write("\ncalls into wrapper region:\n")
for t in sorted(targets):
    out.write(f"  {t:#x}: {len(targets[t])} {[hex(c) for c in targets[t][:5]]}\n")

# Also search 缺乏/丰富/富强 group via disp 0x50b6b8 (=ba-2)
out.write("\n=== raw G0 slots ===\n")
for i in range(3):
    va = 0x50B6BA + i * 9
    raw = code[va - BASE : va - BASE + 9]
    s = raw.split(b"\x00")[0].decode("gbk", "ignore")
    out.write(f"  {va:#x}: {s!r} {raw.hex()}\n")
for i in range(3):
    va = 0x50B6B8 + i * 9
    raw = code[va - BASE : va - BASE + 9]
    s = raw.split(b"\x00")[0].decode("gbk", "ignore")
    out.write(f"  alt {va:#x}: {s!r} {raw.hex()}\n")

# Search cmp patterns like 军资金 thresholds - word money often large
# Look for lea 0x50b6b8 in whole image as bytes
for pat in [struct.pack("<I", 0x50B6B8), struct.pack("<I", 0x50B6BA), struct.pack("<I", 0x50B6BC)]:
    hits = []
    st = 0
    while True:
        j = code.find(pat, st)
        if j < 0:
            break
        hits.append(BASE + j)
        st = j + 1
    out.write(f"pat {pat.hex()}: {[hex(h) for h in hits]}\n")

out.close()
print("done", len(targets))
