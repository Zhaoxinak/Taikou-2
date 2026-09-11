#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe5: reverse 0x466290 return values; search tables for 15/36 as SFX ids."""
import os, struct, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def rd(va, n):
    o = va - BASE
    return MEM[o : o + n] if 0 <= o and o + n <= len(MEM) else b""


def find_calls(target):
    out = []
    off = 0
    while True:
        i = MEM.find(b"\xE8", off)
        if i < 0:
            break
        rel = struct.unpack_from("<i", MEM, i + 1)[0]
        if (BASE + i + 5 + rel) & 0xFFFFFFFF == target:
            out.append(BASE + i)
        off = i + 1
    return out


def imm_val(tok):
    tok = tok.strip()
    m = re.fullmatch(r"(0x[0-9a-fA-F]+|[0-9]+)", tok)
    if not m:
        return None
    s = m.group()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


# Disassemble 0x466290
print("=== 0x466290 ===")
for i in md.disasm(rd(0x466290, 0x120), 0x466290):
    print(f"{hex(i.address)}: {i.mnemonic} {i.op_str}")
    if i.mnemonic == "ret" or (i.mnemonic.startswith("ret") and i.address > 0x466290):
        if i.address > 0x4662f0:
            break

# Also 0x466340 (used nearby)
print("\n=== 0x466340 ===")
for i in md.disasm(rd(0x466340, 0x80), 0x466340):
    print(f"{hex(i.address)}: {i.mnemonic} {i.op_str}")
    if i.mnemonic.startswith("ret") and i.address > 0x466340:
        break

# Wider context of callers that pass esi/edi as arg1
print("\n=== wider context 0x46af00..0x46b160 ===")
for i in md.disasm(rd(0x46af00, 0x260), 0x46af00):
    mark = ""
    if i.mnemonic == "call" and i.op_str in ("0x46bc00", "0x466290", "0x4997c0"):
        mark = " <<<"
    print(f"{hex(i.address)}: {i.mnemonic} {i.op_str}{mark}")

# Search for byte tables that look like SFX id lists containing 0x0f or 0x24
# Heuristic: sequences of bytes all < 39, length >= 4, containing 15 or 36
print("\n=== byte-table heuristic (runs of SFX-range bytes incl 15 or 36) ===")
hits = []
i = 0
N = len(MEM)
while i < N:
    if MEM[i] < 39:
        j = i
        while j < N and MEM[j] < 39:
            j += 1
        run = MEM[i:j]
        if len(run) >= 4 and (15 in run or 36 in run):
            # filter: must have some diversity and not all zero
            if len(set(run)) >= 3 and any(b > 0 for b in run):
                hits.append((BASE + i, list(run[:32]), len(run)))
        i = j
    else:
        i += 1
print(f"candidate runs: {len(hits)}")
for va, run, ln in hits[:40]:
    print(f"  {hex(va)} len={ln} data={run}")

# Word tables: sequences of uint16 < 39
print("\n=== word-table heuristic ===")
whits = []
for i in range(0, N - 2, 2):
    # start of potential run
    w0 = struct.unpack_from("<H", MEM, i)[0]
    if w0 >= 39:
        continue
    vals = []
    j = i
    while j + 2 <= N:
        w = struct.unpack_from("<H", MEM, j)[0]
        if w >= 39:
            break
        vals.append(w)
        j += 2
        if len(vals) > 64:
            break
    if len(vals) >= 4 and (15 in vals or 36 in vals) and len(set(vals)) >= 3:
        whits.append((BASE + i, vals, len(vals)))
print(f"candidate word runs: {len(whits)}")
for va, vals, ln in whits[:30]:
    print(f"  {hex(va)} n={ln} data={vals[:24]}")

# Search movzx/mov loads of 15/36 into a register that eventually reach play
# Already know no mov-imm near play_sfx. Search store of 15/36 into globals that might be SFX slots.
print("\n=== mov [mem], 15 or 36 (C6/C7 patterns via disasm of code denser regions) ===")
# Scan code for: C6 05 xx xx xx xx 0F  or C7 05 xx xx xx xx 0F 00 00 00
# byte store
for imm, tag in [(0x0F, 15), (0x24, 36)]:
    # C6 05 xx xx xx xx imm
    pat = bytes([0xC6, 0x05])
    off = 0
    found = []
    while True:
        i = MEM.find(pat, off)
        if i < 0 or i + 7 > N:
            break
        if MEM[i + 6] == imm:
            addr = struct.unpack_from("<I", MEM, i + 2)[0]
            found.append((BASE + i, hex(addr)))
        off = i + 1
    print(f"mov byte [abs], {tag}: {found[:20]} n={len(found)}")
    # C7 05 xx xx xx xx imm 00 00 00
    pat2 = bytes([0xC7, 0x05])
    off = 0
    found = []
    while True:
        i = MEM.find(pat2, off)
        if i < 0 or i + 10 > N:
            break
        imm32 = struct.unpack_from("<I", MEM, i + 6)[0]
        if imm32 == tag:
            addr = struct.unpack_from("<I", MEM, i + 2)[0]
            found.append((BASE + i, hex(addr)))
        off = i + 1
    print(f"mov dword [abs], {tag}: {found[:20]} n={len(found)}")

# Check if play_inner 0x499740 is called directly with 15/36
INNER = 0x499740
print(f"\n=== direct calls to play_inner {hex(INNER)} ===")
inner_calls = find_calls(INNER)
print("count", len(inner_calls), [hex(x) for x in inner_calls[:20]])
