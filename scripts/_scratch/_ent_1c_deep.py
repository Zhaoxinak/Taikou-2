#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deep hunt: entity @28 / +0x1c numeric consumers; castle flag map; matrix seeds."""
from __future__ import annotations

import os
import struct
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(r"F:\Games\Taikou 2")

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

code = open("scripts/_unpacked_mem.bin", "rb").read()
BSD = open("Taikou2 Original/BSDATA1.TR2", "rb").read()
BASE = 0x400000
ENT, CASTLE = 0x519868, 0x51EB88
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def rd(va, n):
    return code[va - BASE : va - BASE + n]


def dis(va, n=0x40):
    return list(md.disasm(rd(va, n), va))


def find_calls(target):
    hits = []
    for i in range(0, len(code) - 5):
        if code[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", code, i + 1)[0]
        if BASE + i + 5 + rel == target:
            hits.append(BASE + i)
    return hits


# --- Castle addresses of setter this ---
print("=== Castle index of fixed setter ecx ===")
for va in (0x51F45F, 0x51F8F9, 0x51F7E2):
    off = va - CASTLE
    print(f"  {va:08x} off={off} idx={off/31:.3f} rem={off%31}")

# --- word[reg+0x1b] sites: classify entity vs castle ---
print("\n=== word[+0x1b] consumers (66 8x 1b / 0f b7) ===")
pats = [
    b"\x66\x8b\x41\x1b",  # mov ax,[ecx+0x1b]
    b"\x66\x8b\x46\x1b",
    b"\x66\x8b\x47\x1b",
    b"\x66\x8b\x43\x1b",
    b"\x66\x8b\x45\x1b",
    b"\x0f\xb7\x41\x1b",
    b"\x0f\xb7\x46\x1b",
    b"\x0f\xb7\x47\x1b",
    b"\x0f\xb7\x43\x1b",
    b"\x8b\x46\x1b",  # mov eax,[esi+0x1b] may be dword
]
seen = set()
for pat in pats:
    st = 0
    while True:
        j = code.find(pat, st)
        if j < 0:
            break
        va = BASE + j
        st = j + 1
        if va in seen:
            continue
        seen.add(va)
        ctx = rd(va - 0x60, 0xA0)
        tags = []
        if struct.pack("<I", ENT) in ctx:
            tags.append("ENT")
        if struct.pack("<I", CASTLE) in ctx:
            tags.append("CASTLE")
        if b"\xae\x4c\x41\x5d" in ctx:
            tags.append("div47")
        if b"\x84\x21\x08\x43" in ctx:
            tags.append("div31")
        # look at next 8 insn for bit ops on high half
        bits = []
        for i in dis(va, 0x30)[:10]:
            op = i.op_str.lower()
            if any(x in op for x in ("0x400", "0x800", "0x1000", "0x2000", "0xa", "0xb", "0xc", "0xd", "0xfbff", "0xf7ff", "0xefff", "0xdfff")):
                bits.append(f"{i.mnemonic} {i.op_str}")
            if "shr" in i.mnemonic and any(x in op for x in ("0xa", "0xb", "0xc", "0xd", "0x8", "0x9")):
                bits.append(f"{i.mnemonic} {i.op_str}")
        if "ENT" in tags or "div47" in tags or bits:
            print(f"  {va:08x} [{'|'.join(tags) or '?'}] bits={bits[:4]}")
            for i in dis(va, 0x28)[:8]:
                print(f"      {i.address:08x}  {i.mnemonic:8s} {i.op_str}")

# --- ENT-tagged +0x1c reads ---
print("\n=== Context @ ENT-tagged +0x1c reads ===")
for va in (0x4CE2C3, 0x4D936B):
    print(f"\n--- {va:08x} ---")
    for i in dis(va - 0x40, 0x80):
        if va - 0x20 <= i.address <= va + 0x30:
            print(f"  {i.address:08x}  {i.mnemonic:8s} {i.op_str}")

# --- Who WRITES entity+0x1c from BSDATA load ---
# loader typically mov [edi+0x1c], al after reading stream
print("\n=== mov [reg+0x1c] writes near entity load ===")
for pat, name in [
    (b"\x88\x47\x1c", "mov [edi+0x1c],al"),
    (b"\x88\x46\x1c", "mov [esi+0x1c],al"),
    (b"\x88\x43\x1c", "mov [ebx+0x1c],al"),
    (b"\x88\x41\x1c", "mov [ecx+0x1c],al"),
    (b"\x66\x89\x47\x1b", "mov [edi+0x1b],ax"),
    (b"\x66\x89\x46\x1b", "mov [esi+0x1b],ax"),
    (b"\x66\x89\x41\x1b", "mov [ecx+0x1b],ax"),
]:
    hits = []
    st = 0
    while True:
        j = code.find(pat, st)
        if j < 0:
            break
        hits.append(BASE + j)
        st = j + 1
    print(f"\n{name}: {len(hits)}")
    for h in hits[:15]:
        ctx = rd(h - 0x40, 0x60)
        tags = []
        if struct.pack("<I", ENT) in ctx:
            tags.append("ENT")
        if struct.pack("<I", CASTLE) in ctx:
            tags.append("CASTLE")
        if b"\xae\x4c\x41\x5d" in ctx:
            tags.append("div47")
        print(f"  {h:08x} [{'|'.join(tags) or '?'}]")

# --- @28 value distribution vs birth high correlation already known ---
print("\n=== @28 high3 / low5 samples ===")
for i, label in [(13, "信长"), (16, "藤吉郎"), (257, "谦信"), (274, "景胜"), (199, "信玄"), (304, "家康")]:
    v = BSD[i * 59 + 0x28]
    birth = BSD[i * 59 + 0x27]
    print(f"  {label}: @28={v:3d} (0x{v:02x}) hi3={v>>5} lo5={v&0x1f} birth_off={birth} year={1490+birth}")

# Compare hi3 to known ranks / archetypes
print("\n=== hi3 distribution ===")
c = Counter(BSD[i * 59 + 0x28] >> 5 for i in range(700) if not BSD[i * 59 : i * 59 + 7].startswith(b"\xd0\xd5"))  # rough
print(dict(sorted(c.items())))
# better filter placeholders
real = []
for i in range(700):
    nm = BSD[i * 59 : i * 59 + 7]
    if nm[:2] == bytes([0xD0, 0xD5]) or nm.startswith(b"\xd0\xd5"):  # 姓 in GBK?
        continue
    try:
        s = nm.split(b"\x00")[0].decode("gbk", "replace")
    except Exception:
        s = ""
    if s.startswith("姓"):
        continue
    real.append(i)
c = Counter(BSD[i * 59 + 0x28] >> 5 for i in real)
print("real hi3", dict(sorted(c.items())), "n", len(real))
c2 = Counter(BSD[i * 59 + 0x28] & 0x1F for i in real)
print("real lo5 top", c2.most_common(12))

# Correlate hi3 with salary @0x34, status, etc
import statistics as st

def corr(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    return num / (da * db) if da and db else 0

hi = [BSD[i * 59 + 0x28] >> 5 for i in real]
lo = [BSD[i * 59 + 0x28] & 0x1F for i in real]
full = [BSD[i * 59 + 0x28] for i in real]
for off, name in [(0x16, "统率"), (0x17, "武力"), (0x18, "智谋"), (0x19, "政治"), (0x1a, "魅力"),
                  (0x34, "俸禄"), (0x2c, "体力"), (0x27, "生年"), (0x38, "状态"), (0x3a, "档")]:
    vals = [BSD[i * 59 + off] for i in real]
    print(f"  corr(@28, {name})={corr(full, vals):+.3f}  hi3={corr(hi, vals):+.3f}  lo5={corr(lo, vals):+.3f}")
