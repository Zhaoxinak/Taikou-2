#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hunt entity+0x1c / BSDATA @28 true consumers."""
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

SETTERS = {
    0x49AB80: "bit2 or",
    0x49ABA0: "bit3 or",
    0x49ABC0: "bit4 or",
    0x49ABE0: "bit5 or",
}


def find_calls(target: int) -> list[int]:
    hits = []
    for i in range(0, len(code) - 5):
        if code[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", code, i + 1)[0]
        if BASE + i + 5 + rel == target:
            hits.append(BASE + i)
    return hits


def near_imm(ctx: bytes, imm: int) -> bool:
    return struct.pack("<I", imm) in ctx


def dis_range(va: int, n: int) -> list[str]:
    return [f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}" for i in md.disasm(code[va - BASE : va - BASE + n], va)]


print("=== Setter bodies ===")
for va, name in SETTERS.items():
    print(f"\n--- {va:08x} {name} ---")
    for line in dis_range(va, 0x20):
        print(" ", line)

print("\n=== Call sites ===")
for t, name in SETTERS.items():
    hits = find_calls(t)
    print(f"\n## {t:08x} ({name}) n={len(hits)}")
    for h in hits:
        ctx = code[h - BASE - 0x50 : h - BASE + 5]
        tags = []
        if near_imm(ctx, ENT):
            tags.append("ENT")
        if near_imm(ctx, CASTLE):
            tags.append("CASTLE")
        if near_imm(ctx, REL):
            tags.append("REL")
        lines = []
        for i in md.disasm(code[h - BASE - 0x40 : h - BASE + 5], h - 0x40):
            if i.address > h:
                break
            if i.address >= h - 0x30:
                lines.append(f"{i.mnemonic} {i.op_str}")
        print(f"  {h:08x} [{'|'.join(tags) or '?'}] " + " ;; ".join(lines[-7:]))

# byte [reg+0x1c] reads: 8A 4x 1C / 8A 5x 1C / 0F B6 etc
print("\n=== Direct byte[+0x1c] patterns (sample) ===")
patterns = [
    (b"\x8a\x41\x1c", "mov al,[ecx+0x1c]"),
    (b"\x8a\x46\x1c", "mov al,[esi+0x1c]"),
    (b"\x8a\x47\x1c", "mov al,[edi+0x1c]"),
    (b"\x8a\x43\x1c", "mov al,[ebx+0x1c]"),
    (b"\x0f\xb6\x41\x1c", "movzx eax,[ecx+0x1c]"),
    (b"\x0f\xb6\x46\x1c", "movzx eax,[esi+0x1c]"),
    (b"\x0f\xb6\x47\x1c", "movzx eax,[edi+0x1c]"),
    (b"\xf6\x41\x1c", "test [ecx+0x1c],imm"),
    (b"\xf6\x46\x1c", "test [esi+0x1c],imm"),
    (b"\xf6\x47\x1c", "test [edi+0x1c],imm"),
    (b"\x80\x61\x1c", "and [ecx+0x1c],imm"),
    (b"\x80\x49\x1c", "or [ecx+0x1c],imm"),
    (b"\x88\x41\x1c", "mov [ecx+0x1c],al"),
    (b"\x88\x46\x1c", "mov [esi+0x1c],al"),
]
for pat, name in patterns:
    hits = []
    st = 0
    while True:
        j = code.find(pat, st)
        if j < 0:
            break
        hits.append(BASE + j)
        st = j + 1
    print(f"\n{name}: {len(hits)}")
    for h in hits[:12]:
        ctx = code[h - BASE - 0x30 : h - BASE + 8]
        tags = []
        if near_imm(ctx, ENT):
            tags.append("ENT")
        if near_imm(ctx, CASTLE):
            tags.append("CASTLE")
        if near_imm(ctx, REL):
            tags.append("REL")
        # classify by nearby ÷47 vs ÷31 magic
        nearby = code[h - BASE - 0x80 : h - BASE + 0x40]
        if b"\xae\x4c\x41\x5d" in nearby:  # ÷47 entity
            tags.append("div47")
        if b"\x43\x08\x21\x84" in nearby or b"\x84\x21\x08\x43" in nearby:  # ÷31 castle
            tags.append("div31")
        print(f"  {h:08x} [{'|'.join(tags) or '?'}]")
