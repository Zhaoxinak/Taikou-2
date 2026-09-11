#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Locate functions that pick eval-word tier 0/1/2 from numeric thresholds."""
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
out = open("scripts/_scratch/_eval_tier.txt", "w", encoding="utf-8")


def dump(va, n, title=""):
    out.write(f"\n=== {title or hex(va)} ===\n")
    for i in md.disasm(code[va - BASE : va - BASE + n], va):
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")


# Decode MSGX ids pushed near 47ca70
import json

msgx = json.load(open("scripts/msgx_all_texts.json", encoding="utf-8"))
texts = msgx.get("texts") or msgx
for mid in range(0x8AC, 0x8B8):
    t = texts.get(str(mid)) or texts.get(mid)
    out.write(f"MSGX {mid:#x}={mid}: {t!r}\n")

# Strings at 0x509584, 0x50957c, ... (pushed by 47ca70)
for va in range(0x509554, 0x509590, 8):
    raw = code[va - BASE : va - BASE + 8]
    try:
        s = raw.split(b"\x00")[0].decode("gbk", "ignore")
    except Exception:
        s = repr(raw)
    out.write(f"str@{va:#x}: {s!r} raw={raw.hex()}\n")

# Field names table
for i in range(10):
    va = 0x50953C + i * 8
    raw = code[va - BASE : va - BASE + 8]
    s = raw.split(b"\x00")[0].decode("gbk", "ignore")
    out.write(f"field[{i}]@{va:#x}: {s!r}\n")

# Find callers of known eval accessors if any
# Search for lea reg, [0x50b6ba] via absolute
# Also search push of group base: 0x50b6ba + g*27
for g in range(8):
    base = 0x50B6BA + g * 27
    needle = struct.pack("<I", base)
    hits = []
    st = 0
    while True:
        j = code.find(needle, st)
        if j < 0:
            break
        hits.append(BASE + j)
        st = j + 1
    out.write(f"group{g} base {base:#x}: {len(hits)} {[hex(h) for h in hits[:8]]}\n")

# Hunt: sequences with two ascending thresholds (e.g. cmp 40 then cmp 80)
# Scan code for cmp imm16 pairs within 0x40 bytes
out.write("\n=== ascending threshold pairs ===\n")
# Find all cmp ax/r16 with imm in {40,55,60,80} and nearby another
THRESH_SMALL = {40, 55, 60, 80, 50, 70, 90, 100}
THRESH_BIG = {1800, 2000, 3000, 1000, 1500, 2500, 5000}

cmp_sites = []  # (va, imm)
# Pattern 66 3d iw
st = 0
while True:
    j = code.find(b"\x66\x3d", st)
    if j < 0:
        break
    imm = struct.unpack_from("<H", code, j + 2)[0]
    if imm in THRESH_SMALL or imm in THRESH_BIG:
        cmp_sites.append((BASE + j, imm, "cmp ax"))
    st = j + 1

# 81 f8..ff id for 32-bit
for r in range(8):
    st = 0
    pref = bytes([0x81, 0xF8 + r])
    while True:
        j = code.find(pref, st)
        if j < 0 or j + 6 > len(code):
            break
        imm = struct.unpack_from("<I", code, j + 2)[0]
        if imm in THRESH_SMALL or imm in THRESH_BIG:
            cmp_sites.append((BASE + j, imm, f"cmp r{r}"))
        st = j + 1

# 66 81 f8..ff iw
for r in range(8):
    st = 0
    pref = b"\x66\x81" + bytes([0xF8 + r])
    while True:
        j = code.find(pref, st)
        if j < 0 or j + 5 > len(code):
            break
        imm = struct.unpack_from("<H", code, j + 3)[0]
        if imm in THRESH_SMALL or imm in THRESH_BIG:
            cmp_sites.append((BASE + j, imm, f"cmp r{r}16"))
        st = j + 1

cmp_sites.sort()
out.write(f"total interesting cmps: {len(cmp_sites)}\n")
# cluster within 0x80
i = 0
while i < len(cmp_sites):
    cluster = [cmp_sites[i]]
    j = i + 1
    while j < len(cmp_sites) and cmp_sites[j][0] - cluster[0][0] < 0x80:
        cluster.append(cmp_sites[j])
        j += 1
    if len(cluster) >= 2:
        out.write(f"\ncluster @{cluster[0][0]:#x}:\n")
        for c in cluster:
            out.write(f"  {c[0]:08x} imm={c[1]} {c[2]}\n")
        dump(cluster[0][0] - 0x20, 0xA0, f"ctx {cluster[0][0]:#x}")
    i = j if j > i + 1 else i + 1

out.close()
print("ok", len(cmp_sites))
