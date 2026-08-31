#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 3: find how HP globals are addressed at init.
- lea r32, [0x514995] / [0x514835]  (8D + modrm(05/0D/15/1D/25/2D/35/3D) + disp32)
- mov r32, 0x5148xx / 0x5149xx : any block-base or field load
Then for each lea/block-base, disassemble a window AFTER to find the store.
"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

HP = {0x514995: "HP_A", 0x514835: "HP_B"}
ADDR = {va: va.to_bytes(4, "little") for va in HP}

REGS = ["eax","ecx","edx","ebx","esp","ebp","esi","edi"]

def find_pattern(pat, start=0):
    out = []
    pos = start
    while True:
        idx = MEM.find(pat, pos)
        if idx < 0:
            break
        out.append(idx)
        pos = idx + 1
    return out

print("=== lea r32, [HP_A] / [HP_B] ===")
for va in HP:
    ab = ADDR[va]
    for modrm in (0x05,0x0D,0x15,0x1D,0x25,0x2D,0x35,0x3D):
        pat = bytes([0x8D, modrm]) + ab
        for idx in find_pattern(pat):
            reg = modrm & 7
            print(f"  @ off {idx:#08x} va {BASE+idx:#08x}: lea {REGS[reg]}, [0x{va:08x}]")
            ctx = "\n".join(f"    {i.address:#08x}: {i.mnemonic} {i.op_str}" for i in md.disasm(MEM[idx:idx+48], BASE+idx))
            print(ctx)

print("\n=== mov r32, 0x5148xx / 0x5149xx (block base / field load) ===")
# collect all B8..BF + 5148xx / 5149xx
for op in range(0xB8, 0xC0):
    for hi in (0x48, 0x49):
        pat = bytes([op, 0x00, hi, 0x51, 0x00])  # little-endian 0x0051xx00? careful
        # addr = 0x0051xx00 is NOT right. We want 0x5148xx = bytes xx 48 51 00
        pass
# Proper: addr 0x5148xx -> bytes [xx,0x48,0x51,0x00]; 0x5149xx -> [xx,0x49,0x51,0x00]
for hi in (0x48, 0x49):
    for lo in range(0x00, 0x100):
        ab = bytes([lo, hi, 0x51, 0x00])
        for op in range(0xB8, 0xC0):
            pat = bytes([op]) + ab
            for idx in find_pattern(pat):
                reg = op - 0xB8
                va = int.from_bytes(ab, "little")
                print(f"  @ off {idx:#08x} va {BASE+idx:#08x}: mov {REGS[reg]}, 0x{va:08x}")
                ctx = "\n".join(f"    {i.address:#08x}: {i.mnemonic} {i.op_str}" for i in md.disasm(MEM[idx:idx+48], BASE+idx))
                print(ctx)

print("\nDONE")
