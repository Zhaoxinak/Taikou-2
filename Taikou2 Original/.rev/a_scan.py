#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a_scan.py — 在 clean_dump 里按操作数模式搜索指令
用法: python a_scan.py "+ 0x60]" "+ 0x62]"
"""
import sys, capstone, pathlib
D = pathlib.Path(r'F:\Games\Taikou 2\Taikou2 Original\.rev\clean_dump.bin').read_bytes()
BASE = 0x400000
LO, HI = 0x401000, 0x133000
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
pats = sys.argv[1:]
code = D[LO - BASE:HI - BASE]
i = 0
while i < len(code):
    x = None
    for z in md.disasm(code[i:i + 16], LO + i):
        x = z
        break
    if x is None:
        i += 1
        continue
    if all(p in x.op_str for p in pats):
        print('  %08X  %-20s %s %s' % (x.address, x.bytes.hex(), x.mnemonic, x.op_str))
    i += x.size
