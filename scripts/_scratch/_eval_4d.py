#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Disassemble eval threshold classifiers at 0x4d0e*."""
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
out = open("scripts/_scratch/_eval_4d.txt", "w", encoding="utf-8")


def dump(va, n, title=""):
    out.write(f"\n=== {title or hex(va)} ===\n")
    for i in md.disasm(code[va - BASE : va - BASE + n], va):
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")


# Find function starts near 0x4d0e00 - walk back for prologue/align
dump(0x4D0D80, 0x400, "4d0d80..4d1180")

# Find callers of functions in this region
# Guess function entries by looking for ret then next code
entries = []
for va in range(0x4D0D00, 0x4D1200):
    off = va - BASE
    # common: push ebp / mov ecx patterns after int3/nop/ret
    prev = code[off - 1] if off > 0 else 0
    if prev in (0xC3, 0xCC, 0x90) and code[off] in (0x55, 0x53, 0x56, 0x57, 0x51, 0x52, 0x8B, 0x83, 0x81, 0x66, 0x0F):
        entries.append(va)

out.write(f"\ncandidate entries: {[hex(e) for e in entries[:40]]}\n")

# Find e8 calls targeting addresses in 0x4d0e00..0x4d1100
targets = {}
for i in range(len(code) - 5):
    if code[i] != 0xE8:
        continue
    rel = struct.unpack_from("<i", code, i + 1)[0]
    tgt = BASE + i + 5 + rel
    if 0x4D0D00 <= tgt < 0x4D1200:
        targets.setdefault(tgt, []).append(BASE + i)

out.write("\ncallers into region:\n")
for t in sorted(targets):
    out.write(f"  {t:#x}: {len(targets[t])} callers e.g. {[hex(c) for c in targets[t][:6]]}\n")

# Also dump 0x45ac53 cluster (60/80) - might be related
dump(0x45AC20, 0x80, "45ac20 morale?")

out.close()
print("call targets", len(targets))
for t, cs in sorted(targets.items()):
    print(f"  {t:#x}: {len(cs)}")
