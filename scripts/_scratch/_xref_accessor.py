#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Xref-scan the unpacked EXE for direct CALLs to the record accessor 0x47d890
(and its sibling 0x47d8d0). For each call site, disassemble the few preceding
instructions to recover the pushed record index (or register source), then the
following instructions to see how the 49 bytes are consumed.
"""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = open('F:/Games/Taikou 2/scripts/_unpacked_mem.bin','rb').read()
BASE = 0x400000
TARGETS = {0x47d890:'accA', 0x47d8d0:'accB'}

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# find direct E8 calls to each target
def resolve(site):
    rel = struct.unpack('<i', IMG[site+1:site+5])[0]
    return site+5+rel

hits=[]
for off in range(len(IMG)-5):
    if IMG[off]==0xE8:
        t=resolve(off)
        if t in TARGETS:
            hits.append((off,t))
print('direct calls found:', len(hits))
for off,t in hits:
    va=BASE+off
    print('\n=== call %s @ VA 0x%x (file off 0x%x) ===' % (TARGETS[t], va, off))
    # disassemble 24 bytes before and 16 after
    pre = IMG[max(0,off-24):off+5]
    post= IMG[off+5:off+5+24]
    print('  PRE:')
    for ins in md.disasm(pre, va-24):
        mark='>' if ins.address==va else ' '
        print('   %s 0x%x: %s %s' % (mark, ins.address, ins.mnemonic, ins.op_str))
    print('  POST:')
    for ins in md.disasm(post, va+5):
        print('     0x%x: %s %s' % (ins.address, ins.mnemonic, ins.op_str))
        if ins.address-va > 30: break
