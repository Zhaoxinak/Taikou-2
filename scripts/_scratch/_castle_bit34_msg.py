#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resolve MSGX at castle bit3 SET sites; classify this-ptr; scan word>>11/12."""
from __future__ import annotations

import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(r"F:\Games\Taikou 2")

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

code = open("scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
CASTLE, ENT = 0x51EB88, 0x519868
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# Load MSGX if available
msgx_paths = [
    "scripts/msgx_decoded.txt",
    "scripts/msgx.json",
    "Taikou2 Original/MSGX.DAT",
]
for p in msgx_paths:
    print("exists", p, os.path.exists(p))


def dis(va, n=0x100):
    return list(md.disasm(code[va - BASE : va - BASE + n], va))


# Deep dump SET=1 sites
for va in (0x4B3F80, 0x4B40C0, 0x4B4200, 0x4B4400, 0x4D8600, 0x4CA0A0, 0x4A7000):
    print(f"\n======== {va:08x} ========")
    for i in dis(va, 0x120):
        if i.mnemonic == "call" or i.mnemonic == "push" or "0x1c" in i.op_str or "0x1b" in i.op_str or "51eb88" in i.op_str or "519868" in i.op_str:
            print(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}")

# word[+0x1b] >> 11 / >> 12 (bit3 / bit4 of high byte)
print("\n=== shr 0xb / 0xc after word[+0x1b] ===")
for shr_imm in (0xB, 0xC, 0xD):
    # c1 e8 0b = shr eax, imm8 ; 66 c1 e8 0b = shr ax
    for pat in (bytes([0xC1, 0xE8, shr_imm]), bytes([0x66, 0xC1, 0xE8, shr_imm]),
                bytes([0xC1, 0xE9, shr_imm]), bytes([0x66, 0xC1, 0xE9, shr_imm]),
                bytes([0xC1, 0xEA, shr_imm]), bytes([0x66, 0xC1, 0xEA, shr_imm]),
                bytes([0xC1, 0xEB, shr_imm]), bytes([0x66, 0xC1, 0xEB, shr_imm])):
        st = 0
        while True:
            j = code.find(pat, st)
            if j < 0:
                break
            va = BASE + j
            st = j + 1
            # lookback 0x20 for +0x1b
            ctx = code[j - 0x20 : j + 4]
            if b"\x1b" not in ctx:
                continue
            print(f"shr {shr_imm} @ {va:08x}")
            for i in dis(va - 0x18, 0x40)[:12]:
                print(f"  {i.address:08x}  {i.mnemonic:8s} {i.op_str}")

# Try decode MSG via known msg loader table if present
# Search for string refs near db2
print("\n=== try find MSG text tables ===")
# common: msg bank
for needle in [b"\xb2\x0d\x00\x00", b"\xdb\x0d"]:  # little 0xdb2
    pass

# Grep scripts for msgx decode helper
import glob
for g in glob.glob("scripts/*msgx*"):
    print(" ", g)
