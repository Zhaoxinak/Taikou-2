#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 14: locate the AI decision point.
- Disasm 0x46ab20 (called from 0x468860 with ecx=0x514818) — candidate AI decision setter.
- Disasm 0x46baa0, 0x46ba20, 0x46bbb0 (also called by 0x468860) to see if any sets this+0xc.
- Re-scan ALL [reg+0xc] writers and group each into its function; report the containing function
  start address so we can cross-check whether it's on the AI path.
"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def disasm_range(va_start, va_end, label=""):
    out = []
    if label:
        out.append(f"===== {label} [{va_start:#08x} .. {va_end:#08x}] =====")
    for ins in md.disasm(MEM[va_start-BASE:va_end-BASE], va_start):
        out.append(f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}")
    return out

out = []
out += disasm_range(0x46ab20, 0x46ad20, "0x46ab20 (candidate AI decision)")
out += disasm_range(0x46baa0, 0x46bc00, "0x46baa0 (AI setup a)")
out += disasm_range(0x46ba20, 0x46bc00, "0x46ba20 (AI setup b)")
out += disasm_range(0x46bbb0, 0x46bd00, "0x46bbb0 (AI setup c)")

open(r"F:\Games\Taikou 2\scripts\_ai8.txt","w",encoding="utf-8").write("\n".join(out))
print("WROTE _ai8.txt ; bytes:", len("\n".join(out)))
