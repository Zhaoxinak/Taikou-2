#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Close eval-word residual: prove 0x4d0e* is NOT eval thresholds;
scan data-section ptrs to 0x50b6ba; find 3-tier classifiers near castle stats.
"""
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
out = open("scripts/_scratch/_eval_close.txt", "w", encoding="utf-8")

# --- A: decode 0x50ce78 tables used by 4d0e80 ---
import json

msgx = json.load(open("scripts/msgx_all_texts.json", encoding="utf-8"))
texts = msgx.get("texts") or msgx

out.write("=== 0x50ce78 family as MSG ids ===\n")
for base_name, base in [
    ("ce78", 0x50CE78),
    ("ce80", 0x50CE80),
    ("ce88", 0x50CE88),
    ("ce90", 0x50CE90),
    ("ce98", 0x50CE98),
]:
    out.write(f"\n-- {base_name} @ {base:#x} --\n")
    for i in range(8):
        w = struct.unpack_from("<H", code, base - BASE + i * 2)[0]
        t = texts.get(str(w), texts.get(str(w), "?"))
        if isinstance(t, dict):
            t = t.get("text") or t
        out.write(f"  [{i}] id={w:#x}={w}: {t!r}\n")

# --- B: any dword in image == 0x50b6ba or inside table ---
TBL, N = 0x50B6BA, 24 * 9
ptr_hits = []
for off in range(0, len(code) - 3, 4):
    v = struct.unpack_from("<I", code, off)[0]
    if TBL <= v < TBL + N:
        ptr_hits.append((BASE + off, v))
out.write(f"\ndword ptrs into eval table: {len(ptr_hits)}\n")
for a, v in ptr_hits[:30]:
    out.write(f"  @{a:#x} = {v:#x}\n")

# --- C: 3-way tier picker pattern: cmp; jb/jae; cmp; jb/jae; mov 0/1/2 ---
# Look near castle field readers. Simpler: find functions that return 0..2
# after two ascending cmps on same register.

# Scan for: cmp ax, imm1; jb X; cmp ax, imm2; ... within 20 bytes
# where imm1 < imm2 and both in plausible sets

SMALL = {20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 100}
BIG = {500, 800, 1000, 1500, 1800, 2000, 2500, 3000, 4000, 5000, 8000, 10000}

candidates = []
# Find all cmp ax, imm16
sites = []
st = 0
while True:
    j = code.find(b"\x66\x3d", st)
    if j < 0:
        break
    imm = struct.unpack_from("<H", code, j + 2)[0]
    if imm in SMALL or imm in BIG:
        sites.append((BASE + j, imm))
    st = j + 1

# Pair consecutive within 0x30 with ascending imm
for i in range(len(sites) - 1):
    a, ia = sites[i]
    b, ib = sites[i + 1]
    if 0 < b - a <= 0x30 and ia < ib and (
        (ia in SMALL and ib in SMALL) or (ia in BIG and ib in BIG)
    ):
        candidates.append((a, ia, ib))

out.write(f"\nascending cmp-ax pairs: {len(candidates)}\n")
for a, ia, ib in candidates:
    out.write(f"\n--- {a:#x} thresholds {ia}/{ib} ---\n")
    for i in md.disasm(code[a - BASE - 0x40 : a - BASE + 0x80], a - 0x40):
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")
        if i.address > a + 0x50:
            break

# --- D: 47ca70 row order from field string pushes (static!) ---
# From earlier disasm, push order vs bp:
# bp==0: 军资金 (0x509584) field[9]
# bp<=1: 军粮 (0x50957c) field[8]
# bp<=2: 士兵数 field[7]
# bp<=3: 洋枪 field[6]
# bp<=4: 军马 field[5]
# bp>=1: 俸禄 field[4]
# bp>=2: 支持率 field[3]
# ... need rest of function

out.write("\n=== 47ca70 full remaining ===\n")
for i in md.disasm(code[0x47CA70 - BASE : 0x47CD00 - BASE], 0x47CA70):
    if i.mnemonic == "push" and ("0x509" in i.op_str or "0x8" in i.op_str):
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")
    elif i.mnemonic.startswith("j") or i.mnemonic == "cmp" and "bp" in i.op_str:
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")
    elif i.mnemonic == "ret":
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")
        break

out.close()
print("ptrs", len(ptr_hits), "pairs", len(candidates))
