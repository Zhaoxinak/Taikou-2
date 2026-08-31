#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 19: disassemble the 5 action executors (0x80 bytes each) to confirm:
- do they set this+0xc (action code)?
- do they call 0x468860 / 0x468640 (the performer)?
This reveals how the AI routes to the same executors."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

targets = {
    0x468af0: "ACT0 (普通攻击? from menu idx0)",
    0x46a680: "ACT1 (瞄准? from menu idx1)",
    0x468cd0: "ACT2 (快刀? from menu idx2)",
    0x468f00: "ACT3 (击中要害? from menu idx3)",
    0x4663f0: "ACT4 (一击必杀 from menu idx4)",
}
out = []
for va, label in targets.items():
    out.append(f"\n===== {label} @ {va:#08x} =====")
    for ins in md.disasm(MEM[va-BASE:va-BASE+0x90], va):
        out.append(f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}")

open(r"F:\Games\Taikou 2\scripts\_ai16.txt","w",encoding="utf-8").write("\n".join(out))
print("WROTE _ai16.txt")
