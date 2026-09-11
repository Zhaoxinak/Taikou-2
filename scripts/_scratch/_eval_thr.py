#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find eval-word threshold cmps (40/55/60/80/1800/2000/3000) and classify sites."""
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
md.detail = True
out = open("scripts/_scratch/_eval_thr.txt", "w", encoding="utf-8")

# Immediate encodings for cmp
# cmp r/m16, imm16; cmp r/m32, imm32; cmp al/ax/eax, imm
TARGETS = {
    40: [b"\x28\x00", b"\x28"],  # word / byte
    55: [b"\x37\x00", b"\x37"],
    60: [b"\x3c\x00", b"\x3c"],
    80: [b"\x50\x00", b"\x50"],
    1800: [b"\x08\x07"],
    2000: [b"\xd0\x07"],
    3000: [b"\xb8\x0b"],
}

# Search for cmp with imm near known region and globally for large thresholds
# Pattern: 66 81 fa XX XX (cmp dx, imm16) etc.

def find_cmp_imm16(imm: int):
    """Find cmp */imm16 sites via disasm windows around candidate bytes."""
    pat = struct.pack("<H", imm)
    hits = []
    st = 0
    while True:
        j = code.find(pat, st)
        if j < 0:
            break
        # try disasm from j-8..j
        for back in range(0, 12):
            start = j - back
            if start < 0:
                continue
            for i in md.disasm(code[start : start + 16], BASE + start):
                if i.address == BASE + j - (len(i.bytes) - len(pat)) or (
                    i.mnemonic == "cmp" and hex(imm)[2:] in i.op_str.replace("0x", "")
                ):
                    if i.mnemonic == "cmp" and (
                        f"0x{imm:x}" in i.op_str.lower()
                        or f"{imm}" == i.op_str.split(",")[-1].strip()
                        or f"0x{imm:x}" == i.op_str.split(",")[-1].strip().lower()
                    ):
                        hits.append((i.address, i.mnemonic, i.op_str, bytes(i.bytes).hex()))
                        break
            else:
                continue
            break
        st = j + 1
        if len(hits) > 80:
            break
    return hits


for imm in (40, 55, 60, 80, 1800, 2000, 3000):
    # brute: disasm every 0x1000 window looking for cmp with this imm - too slow
    # instead scan for opcode patterns
    hits = []
    # cmp r16, imm16: 66 81 /7 iw  or 66 83 /7 ib (sign-extend)
    # cmp r32, imm32: 81 /7 id
    # cmp ax, imm16: 66 3d iw
    # cmp eax, imm32: 3d id
    imm16 = struct.pack("<H", imm & 0xFFFF)
    imm32 = struct.pack("<I", imm)
    patterns = [
        (b"\x66\x3d" + imm16, "cmp ax"),
        (b"\x3d" + imm32, "cmp eax"),
        (b"\x66\x81" + bytes([0xF8 + r]) + imm16, f"cmp r16,{imm}") for r in range(8)
    ] if False else []
    # manual patterns
    pats = [(b"\x66\x3d" + imm16, "cmp ax,imm")]
    if imm < 0x80 or imm >= 0xFFFFFF80:
        # sign-extend byte forms possible for small
        pass
    pats.append((b"\x3d" + imm32, "cmp eax,imm"))
    for r in range(8):
        pats.append((b"\x66\x81" + bytes([0xF8 + r]) + imm16, f"cmp r{r}16"))
        pats.append((b"\x81" + bytes([0xF8 + r]) + imm32, f"cmp r{r}32"))
        if imm <= 0x7F:
            pats.append((b"\x66\x83" + bytes([0xF8 + r]) + bytes([imm]), f"cmp r{r}16 ib"))
            pats.append((b"\x83" + bytes([0xF8 + r]) + bytes([imm]), f"cmp r{r}32 ib"))
    # also cmp [mem], imm via 81 /7
    for modrm_base in range(0x80):  # too many
        break
    for pat, name in pats:
        st = 0
        n = 0
        while n < 40:
            j = code.find(pat, st)
            if j < 0:
                break
            hits.append((BASE + j, name, pat.hex()))
            st = j + 1
            n += 1
    out.write(f"\n=== imm {imm} : {len(hits)} ===\n")
    for h in hits[:25]:
        out.write(f"  {h[0]:08x} {h[1]} {h[2]}\n")
        # dump context
        for i in md.disasm(code[h[0] - BASE - 0x10 : h[0] - BASE + 0x30], h[0] - 0x10):
            mark = ">>" if i.address == h[0] else "  "
            out.write(f"  {mark}{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")
            if i.address > h[0] + 0x20:
                break

# Specifically dump 0x4d0e00..0x4d1200 fully - earlier probe showed almost empty?
out.write("\n=== FULL 0x4d0e00..0x4d1100 ===\n")
for i in md.disasm(code[0x4D0E00 - BASE : 0x4D1100 - BASE], 0x4D0E00):
    out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")

# Who references field table 0x50953c?
needle = struct.pack("<I", 0x50953C)
st = 0
xrefs = []
while True:
    j = code.find(needle, st)
    if j < 0:
        break
    xrefs.append(BASE + j)
    st = j + 1
out.write(f"\nxrefs 0x50953c: {len(xrefs)} {[hex(x) for x in xrefs[:30]]}\n")

# MSG ids 0x8ac.. near 47ca70 - decode from msgx
out.close()
print("done")
