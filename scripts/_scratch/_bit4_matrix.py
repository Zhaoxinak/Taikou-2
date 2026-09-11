#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bit4 SET/TEST + matrix static seed catalog."""
from __future__ import annotations

import json
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
texts = json.load(open("scripts/msgx_all_texts.json", encoding="utf-8"))["texts"]
out = open("scripts/_scratch/_bit4_matrix.txt", "w", encoding="utf-8")


def dis(va, n=0x80):
    return list(md.disasm(code[va - BASE : va - BASE + n], va))


def callers(target):
    hits = []
    for i in range(len(code) - 5):
        if code[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", code, i + 1)[0]
        if BASE + i + 5 + rel == target:
            hits.append(BASE + i)
    return hits


def last_push(site):
    for i in reversed(list(dis(site - 0x20, 0x20))):
        if i.address >= site:
            continue
        if i.mnemonic == "push":
            return i.op_str
    return "?"


out.write("=== bit4 setter call args ===\n")
for h in callers(0x49ABC0):
    out.write(f"  {h:08x} arg={last_push(h)}\n")

out.write("\n=== bit3 setter call args ===\n")
for h in callers(0x49ABA0):
    out.write(f"  {h:08x} arg={last_push(h)}\n")

# test +0x1c, 0x10
out.write("\n=== test [reg+0x1c],0x10 sites ===\n")
for pat in (b"\xf6\x46\x1c\x10", b"\xf6\x47\x1c\x10", b"\xf6\x43\x1c\x10",
            b"\xf6\x41\x1c\x10", b"\xf6\x45\x1c\x10", b"\x80\x7e\x1c\x10"):
    st = 0
    while True:
        j = code.find(pat, st)
        if j < 0:
            break
        va = BASE + j
        st = j + 1
        out.write(f"\n-- {va:08x} --\n")
        for i in dis(va - 0x30, 0x70):
            if va - 0x20 <= i.address <= va + 0x40:
                mark = ">>" if i.address == va else "  "
                out.write(f"{mark}{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")
                if i.mnemonic == "push":
                    try:
                        v = int(i.op_str, 16) if i.op_str.startswith("0x") else int(i.op_str)
                        if 0x100 <= v <= 0x3000:
                            t = texts.get(str(v), "")
                            out.write(f"    MSG {v:#x}={t[:80]}\n")
                    except ValueError:
                        pass

# also and/or with 0x10 on +0x1c besides setters
out.write("\n=== nearby MSG for bit4 clear wrapper 0x4ca0e1 ===\n")
for i in dis(0x4CA080, 0x80):
    out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")

# Matrix: catalog all imm triples
out.write("\n=== matrix imm write catalog ===\n")
WRITERS = {"A": 0x4A0FF0, "B": 0x4A1010, "C": 0x4A1030}


def parse_pushes(site, lookback=80):
    pushes = []
    for ins in md.disasm(code[site - lookback - BASE : site - BASE], site - lookback):
        if ins.mnemonic != "push":
            continue
        op = ins.op_str.strip()
        try:
            v = int(op, 16) if op.startswith("0x") or op.startswith("-0x") else int(op)
            pushes.append(("imm", v))
        except ValueError:
            pushes.append(("reg", op))
    return pushes[-3:] if len(pushes) >= 3 else pushes


for name, t in WRITERS.items():
    out.write(f"\n## {name}\n")
    for s in callers(t):
        last = parse_pushes(s)
        out.write(f"  {s:08x} {last}\n")

# Confirm bit3 MSG texts
out.write("\n=== bit3 SET site MSG confirm ===\n")
for mid in (0xDB2, 0xDB3, 0xDC0, 0x16E8):
    out.write(f"  {mid:#x}: {texts.get(str(mid))}\n")

# 0x50d764 / 0x504778 names for bit2 UI
out.write("\n=== bit2 UI strings ===\n")
for va in (0x504778, 0x50D764, 0x50D6A0, 0x50D6A4):
    raw = code[va - BASE : va - BASE + 16]
    s = raw.split(b"\x00")[0].decode("gbk", "replace")
    out.write(f"  {va:#x}: {s!r} hex={raw[:12].hex()}\n")

out.close()
print("wrote", out.name)
