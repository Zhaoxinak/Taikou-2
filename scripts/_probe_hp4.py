#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 4: find DWORD stores to HP globals 0x514995 / 0x514835 (no 0x66 prefix).
Patterns (addr = 4-byte imm following the modrm byte):
  a3 ADDR            mov [ADDR], eax
  89 05/0d/15/1d/25/2d/35/3d ADDR   mov [ADDR], r32
  c7 05 ADDR IMM32  mov [ADDR], imm32
Also: for each hit, disassemble 48 bytes BEFORE to recover the formula (load stat -> compute -> store).
"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

HP = {0x514995: "HP_A(我方)", 0x514835: "HP_B(敌方)"}
ADDR = {va: va.to_bytes(4, "little") for va in HP}
REGS = ["eax","ecx","edx","ebx","esp","ebp","esi","edi"]

def classify_store(pre2):
    b0, b1 = pre2[0], pre2[1]
    if b0 == 0xa3:
        return "STORE_EAX"
    if b0 == 0x89:
        return f"STORE_{REGS[b1 & 7]}"
    if b0 == 0xc7 and (b1 & 0x38) == 0x00:  # modrm reg field 0
        return "STORE_IMM32"
    return None

hits = {va: [] for va in HP}
for va in HP:
    ab = ADDR[va]
    # a3
    pat = bytes([0xa3]) + ab
    pos = 0
    while True:
        i = MEM.find(pat, pos)
        if i < 0: break
        hits[va].append((i-1, "STORE_EAX"))
        pos = i+1
    # 89 05..3d
    for modrm in (0x05,0x0d,0x15,0x1d,0x25,0x2d,0x35,0x3d):
        pat = bytes([0x89, modrm]) + ab
        pos = 0
        while True:
            i = MEM.find(pat, pos)
            if i < 0: break
            hits[va].append((i-2, f"STORE_{REGS[modrm & 7]}"))
            pos = i+1
    # c7 05..3d
    for modrm in (0x05,0x0d,0x15,0x1d,0x25,0x2d,0x35,0x3d):
        pat = bytes([0xc7, modrm]) + ab
        pos = 0
        while True:
            i = MEM.find(pat, pos)
            if i < 0: break
            hits[va].append((i-2, "STORE_IMM32"))
            pos = i+1

out = []
for va in HP:
    out.append(f"\n===== {HP[va]} 0x{va:08x} : {len(hits[va])} dword-store refs =====")
    for off, cls in sorted(set(hits[va])):
        ctx_start = max(0, off - 48)
        ctx = "\n".join(f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}"
                        for ins in md.disasm(MEM[ctx_start:off+8], BASE+ctx_start))
        out.append(f"\n-- {cls} @ off {off:#08x} (va {BASE+off:#08x})")
        out.append(ctx)
open(r"F:\Games\Taikou 2\scripts\_hp4.txt", "w", encoding="utf-8").write("\n".join(out))
print("WROTE _hp4.txt")
print({hex(v): len(set(hits[v])) for v in HP})
