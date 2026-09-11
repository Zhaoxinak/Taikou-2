#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Classify real [reg+0x1c] (not esp) and find BSDATA apply path for @28."""
from __future__ import annotations

import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(r"F:\Games\Taikou 2")

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

code = open("scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
ENT, CASTLE, REL = 0x519868, 0x51EB88, 0x5197B0
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def dis(va, n=0x60):
    return list(md.disasm(code[va - BASE : va - BASE + n], va))


def dump(va, before=0x30, after=0x40, title=""):
    print(f"\n=== {title or hex(va)} ===")
    for i in dis(va - before, before + after):
        mark = ">>" if i.address == va else "  "
        print(f"{mark}{i.address:08x}  {i.mnemonic:8s} {i.op_str}")


# Precise scan: ModRM disp8 = 0x1c with register base (not esp/ebp SIB stack)
# mov r8, [r+0x1c] encodings commonly: 8A 4x 1C / 8A 5x etc
# Also 0F B6, F6, 80, 88
print("=== Precise [reg+0x1c] byte ops (code 0x401000-0x4f0000) ===")
hits = []
for va in range(0x401000, 0x4F0000):
    off = va - BASE
    # skip if previous makes this mid-insn? use capstone walk instead per chunk
# walk with capstone
va = 0x401000
end = 0x4F0000
while va < end:
    # disasm one at a time is slow; do 4k chunks
    chunk_end = min(va + 0x2000, end)
    for i in md.disasm(code[va - BASE : chunk_end - BASE], va):
        if i.address >= chunk_end:
            break
        op = i.op_str
        if "+ 0x1c]" not in op:
            continue
        if "esp + 0x1c]" in op or "ebp + 0x1c]" in op:
            continue
        # must be mem operand with +0x1c
        if not any(r in op for r in ("eax", "ebx", "ecx", "edx", "esi", "edi")):
            continue
        ctx = code[i.address - BASE - 0x60 : i.address - BASE + 0x20]
        tags = []
        if struct.pack("<I", ENT) in ctx:
            tags.append("ENT")
        if struct.pack("<I", CASTLE) in ctx:
            tags.append("CASTLE")
        if struct.pack("<I", REL) in ctx:
            tags.append("REL")
        if b"\xae\x4c\x41\x5d" in ctx:
            tags.append("div47")
        if b"\x84\x21\x08\x43" in ctx:
            tags.append("div31")
        hits.append((i.address, i.mnemonic, i.op_str, tags))
    va = chunk_end

print(f"total hits: {len(hits)}")
for h in hits:
    print(f"  {h[0]:08x}  {h[1]:8s} {h[2]:40s} {h[3]}")

# Dump interesting ones
for va, title in [
    (0x447992, "447992"),
    (0x449656, "449656"),
    (0x4D3B76, "4d3b76"),
    (0x4D3BA1, "4d3ba1"),
    (0x4D6204, "4d6204 test &7"),
    (0x4DB6A2, "4db6a2"),
    (0x4BC296, "4bc296"),
    (0x4B45C3, "4b45c3 test"),
    (0x4CB69B, "4cb69b test"),
]:
    dump(va, 0x40, 0x50, title)

# Find BSDATA apply: search for reading from 0x524a20 (BUSHOUbuf) + store
print("\n=== xref 0x524a20 (BUSHOUbuf) ===")
needle = struct.pack("<I", 0x524A20)
st = 0
xrefs = []
while True:
    j = code.find(needle, st)
    if j < 0:
        break
    xrefs.append(BASE + j)
    st = j + 1
print("imm xrefs", len(xrefs), [hex(x) for x in xrefs[:30]])

# Serializer inverse — look at 0x47e068 area more (reads) vs writers that apply template
# Search function that does mov [edi+0x1b] from loaded byte sequence
print("\n=== Looking for apply template near 0x47e000 ===")
for i in dis(0x47E000, 0x200):
    if "0x1b" in i.op_str or "0x1c" in i.op_str:
        print(f"  {i.address:08x}  {i.mnemonic:8s} {i.op_str}")
