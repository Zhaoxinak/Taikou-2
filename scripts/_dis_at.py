# -*- coding: utf-8 -*-
"""Dump raw disassembly at given addresses:  python scripts/_dis_at.py 0x47a390+0x60 ..."""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

for a in sys.argv[1:]:
    if '+' in a:
        s, n = a.split('+')
    else:
        s, n = a, '0x60'
    va = int(s, 16); n = int(n, 16)
    print(f'--- {va:#x} (+{n:#x}) ---')
    for ins in md.disasm(MEM[va - BASE: va - BASE + n], va):
        print(f'   0x{ins.address:x}: {ins.mnemonic} {ins.op_str}')
    print()
