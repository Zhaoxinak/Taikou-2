# -*- coding: utf-8 -*-
"""a_range.py — 从指令边界线性反汇编并只打印 [lo, hi) 区间
用法: python a_range.py <anchor_va> <lo_va> <hi_va>
"""
import sys, pathlib, capstone

D = pathlib.Path(r'F:\Games\Taikou 2\Taikou2 Original\.rev\clean_dump.bin').read_bytes()
BASE = 0x400000
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
anchor = int(sys.argv[1], 16)
lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
off = anchor - BASE
for i in md.disasm(D[off:off + 0x800], anchor):
    if i.address >= hi:
        break
    if i.address >= lo:
        print('%08X  %-22s %s %s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))
