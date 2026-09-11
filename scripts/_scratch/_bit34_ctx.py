#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(r"F:\Games\Taikou 2")
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

code = open("scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
out = open("scripts/_scratch/_bit34_ctx.txt", "w", encoding="utf-8")


def dump(va, n, title=""):
    out.write(f"\n=== {title or hex(va)} ===\n")
    for i in md.disasm(code[va - BASE : va - BASE + n], va):
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")


dump(0x49AC00, 0x40, "49ac00")
dump(0x49ABA0, 0x20, "49aba0")
dump(0x4B4000, 0x160, "4b4000")
dump(0x4B4200, 0x120, "4b4200")
dump(0x4B4400, 0x120, "4b4400")
dump(0x4D8600, 0x150, "4d8600")
dump(0x4B45A0, 0x80, "4b45a0 test bit3")
dump(0x4E5540, 0x60, "4e5540 test bit2")
dump(0x409650, 0x120, "409650 matrix init")
dump(0x410A70, 0x100, "410a70 matrix read")
out.close()
print("wrote")
