#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Disassemble the EXE text module around 0x443xxx where GBK lead-byte
checks (cmp al,0x81 / cmp al,0xa1) cluster, to recover the GBK->glyph-index
conversion (the KOEI 字形码 mapping)."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE=open('F:/Games/Taikou 2/scripts/_unpacked_mem.bin','rb').read()
BASE=0x400000

# locate all cmp al,0x81 / cmp al,0xa1
hits=[]
i=0
while i < len(EXE)-1:
    # 3c XX = cmp al, imm8
    if EXE[i]==0x3c:
        imm=EXE[i+1]
        if imm in (0x81,0xa1,0x40,0x7f,0x9f):
            hits.append((BASE+i, imm))
    i+=1
print('cmp al,imm hits total=%d' % len(hits))
from collections import Counter
c=Counter(h for h,_ in hits)
# show clusters
print('addresses of cmp al,0x81/0xa1 (first 40):')
print([hex(a) for a,_ in hits if _ in (0x81,0xa1)][:40])

# disassemble a window around the densest cluster (0x443xxx)
clu=[a for a,_ in hits if 0x443800<=a<=0x444600]
print('\ncluster 0x443800-0x444600 cmp-hits:', len(clu))
if clu:
    lo=min(clu)-0x200; hi=max(clu)+0x200
    lo=max(0,lo-BASE); hi=min(len(EXE),hi-BASE)
    md=Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail=True
    code=EXE[lo:hi]
    print('\n=== disasm 0x%06x - 0x%06x ===' % (BASE+lo, BASE+hi))
    for ins in md.disasm(code, BASE+lo):
        # highlight cmp al,0x81/0xa1
        mark=' <<<' if ins.mnemonic=='cmp' and ins.op_str.startswith('al, ') and ins.op_str.split(', ')[1] in ('0x81','0xa1') else ''
        print('0x%06x: %-10s %s%s' % (ins.address, ins.mnemonic, ins.op_str, mark))
        if ins.address > BASE+hi-0x40: break
