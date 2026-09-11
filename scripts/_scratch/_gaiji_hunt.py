#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hunt gaiji A140..A14F references in text-ish assets + MSGX + MEM strings."""
import os
import json
import struct
import collections

ROOT = r"F:\Games\Taikou 2"
ORIG = os.path.join(ROOT, "Taikou2 Original")
HERE = os.path.join(ROOT, "scripts")
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000

GAIJI = {c: bytes([(c >> 8) & 0xFF, c & 0xFF]) for c in range(0xA140, 0xA150)}

# --- 1. text-ish ORIG files ---
print("=== ORIG text-ish file hits ===")
skip_ext = {".AVI", ".MP3", ".GRP", ".KOS", ".PK8", ".SWP", ".BMP", ".JPG"}
for f in sorted(os.listdir(ORIG)):
    p = os.path.join(ORIG, f)
    if not os.path.isfile(p):
        continue
    ext = os.path.splitext(f)[1].upper()
    if ext in skip_ext:
        continue
    data = open(p, "rb").read()
    counts = {c: data.count(pat) for c, pat in GAIJI.items() if data.count(pat)}
    if counts:
        print(f"{f}: " + ", ".join(f"{hex(k)}={v}" for k, v in sorted(counts.items())))

# --- 2. MESSAGE*.LZW ---
print("\n=== MESSAGE / HEXMES / MSG files ===")
for f in sorted(os.listdir(ORIG)):
    up = f.upper()
    if "MES" in up or "MSG" in up or "HEX" in up:
        p = os.path.join(ORIG, f)
        print(f, os.path.getsize(p))

# --- 3. msgx_all_texts.json ---
print("\n=== msgx_all_texts.json ===")
mp = os.path.join(HERE, "msgx_all_texts.json")
raw = open(mp, "rb").read()
print("size", len(raw))
for c, pat in GAIJI.items():
    n = raw.count(pat)
    if n:
        print(f"  BE {hex(c)}: {n}")

data = json.loads(raw)
print("type", type(data).__name__)
if isinstance(data, dict):
    print("keys sample", list(data.keys())[:10])
elif isinstance(data, list):
    print("len", len(data), "sample0", str(data[0])[:200] if data else None)

# Collect all strings and look for rare CJK candidates
candidates = "堯長香宗我部籠頸垪惣揆梟瓊絆渚戌尭頚篭篭礻礻"
# expand search set
extra = "堯尭長香宗部籠篭頸頚垪惣揆梟瓊絆渚戌靭靱躾辻轟雫榊萩荻雫"
rare = set(extra)

def walk(o, out):
    if isinstance(o, str):
        out.append(o)
    elif isinstance(o, dict):
        for v in o.values():
            walk(v, out)
    elif isinstance(o, list):
        for v in o:
            walk(v, out)

strs = []
walk(data, strs)
print("string count", len(strs))

# Find strings containing any rare char
hits = []
for s in strs:
    for ch in s:
        if ch in rare or (ord(ch) >= 0xE000 and ord(ch) <= 0xF8FF):
            hits.append(s)
            break
print("rare-char strings", len(hits))
for s in hits[:40]:
    print(" ", s[:120])

# Also dump chars that fail gbk roundtrip or are uncommon
from collections import Counter
char_c = Counter()
for s in strs:
    for ch in s:
        if "\u4e00" <= ch <= "\u9fff":
            char_c[ch] += 1

# Print rarest CJK (freq 1..5) that look like gaiji candidates
print("\nRare CJK (freq<=5) sample:")
rare_cjk = [(ch, n) for ch, n in char_c.items() if n <= 5]
rare_cjk.sort(key=lambda x: (x[1], x[0]))
for ch, n in rare_cjk[:80]:
    print(f"  U+{ord(ch):04X} {ch} x{n}")
