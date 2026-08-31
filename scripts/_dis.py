#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dis.py <start_va_hex> <end_va_hex>  -- linear disasm dump of _unpacked_mem.bin"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BIN = 'scripts/_unpacked_mem.bin'
data = open(BIN, 'rb').read()
BASE = 0x400000
st = int(sys.argv[1], 16)
en = int(sys.argv[2], 16)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False
o = st - BASE
for insn in md.disasm(data[o:o+(en-st)], st):
    if insn.address >= en:
        break
    print('%08x: %-10s %s' % (insn.address, insn.mnemonic, insn.op_str))
