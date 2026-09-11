#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe castle +0x1c bit3/bit4 callers for MSGX / play semantics."""
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


def callers(target):
    out = []
    for i in range(len(code) - 5):
        if code[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", code, i + 1)[0]
        if BASE + i + 5 + rel == target:
            out.append(BASE + i)
    return out


def dis(va, n=0x80):
    return list(md.disasm(code[va - BASE : va - BASE + n], va))


def dump_around(site, lookback=0x60, lookfwd=0x20):
    print(f"\n==== call @{site:08x} ====")
    for i in dis(site - lookback, lookback + lookfwd):
        mark = ">>" if i.address == site else "  "
        print(f"{mark}{i.address:08x}  {i.mnemonic:8s} {i.op_str}")


# bit3 = 0x49aba0, bit4 = 0x49abc0
for name, tgt in (("bit3", 0x49ABA0), ("bit4", 0x49ABC0)):
    hits = callers(tgt)
    print(f"\n########## {name} setter {tgt:08x} n={len(hits)}")
    for h in hits:
        # collect nearby push imm that look like MSGX
        msgs = []
        for i in dis(h - 0x80, 0x90):
            if i.address > h:
                break
            if i.mnemonic == "push":
                try:
                    v = int(i.op_str, 16) if i.op_str.startswith("0x") else int(i.op_str)
                    if 0x100 <= v <= 0x3000:
                        msgs.append(v)
                except ValueError:
                    pass
            if i.mnemonic == "call" and "0x47b900" in i.op_str:
                pass
        # arg to setter
        arg = "?"
        for i in reversed(list(dis(h - 0x30, 0x30))):
            if i.address >= h:
                continue
            if i.mnemonic == "push":
                arg = i.op_str
                break
        print(f"  {h:08x} arg={arg} msgs={msgs[-6:]}")
        dump_around(h, 0x50, 0x10)

# Also test [reg+0x1c], 8 / 0x10 consumers (castle)
print("\n########## test bit3/bit4 consumers")
for pat, label in [
    (b"\xf6\x46\x1c\x08", "test [esi+0x1c],8"),
    (b"\xf6\x47\x1c\x08", "test [edi+0x1c],8"),
    (b"\xf6\x43\x1c\x08", "test [ebx+0x1c],8"),
    (b"\xf6\x41\x1c\x08", "test [ecx+0x1c],8"),
    (b"\xf6\x46\x1c\x10", "test [esi+0x1c],0x10"),
    (b"\xf6\x47\x1c\x10", "test [edi+0x1c],0x10"),
    (b"\xf6\x43\x1c\x10", "test [ebx+0x1c],0x10"),
    (b"\xf6\x41\x1c\x10", "test [ecx+0x1c],0x10"),
    (b"\xf6\x46\x1c\x04", "test [esi+0x1c],4"),
    (b"\xf6\x47\x1c\x04", "test [edi+0x1c],4"),
]:
    st = 0
    hits = []
    while True:
        j = code.find(pat, st)
        if j < 0:
            break
        hits.append(BASE + j)
        st = j + 1
    print(f"{label}: {len(hits)} {[hex(h) for h in hits[:12]]}")
    for h in hits[:4]:
        dump_around(h, 0x20, 0x30)
