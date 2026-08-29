# -*- coding: utf-8 -*-
"""Dump section-A accessor call sites (arg-setup windows) + name-table clues."""
import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
TEXT_START, TEXT_END = 0x401000, 0x4d0000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

DEF = {
    0x439050: 'getLo(a,c)=SECT_A[a+20*c]&0xF',
    0x4390c0: 'getHi(a,c)=SECT_A[a+20*c]>>4',
    0x439080: 'setLo(a,c,v)',
}

def all_calls():
    out = []
    i = 0
    while True:
        i = MEM.find(b'\xe8', i, TEXT_END - BASE)
        if i < 0:
            break
        rel = struct.unpack_from('<i', MEM, i + 1)[0]
        t = (i + BASE) + 5 + rel
        if TEXT_START <= t < TEXT_END:
            out.append((i + BASE, t))
        i += 1
    return out

CALLS = all_calls()

def dis_window(va, before=64, after=4):
    start = max(TEXT_START, va - before)
    chunk = MEM[start - BASE: va + after + 8 - BASE]
    out = []
    for ins in md.disasm(chunk, start):
        if ins.address > va + after:
            break
        mark = '>>>' if ins.address == va else '   '
        out.append(f'{mark} {ins.address:#08x}  {ins.bytes.hex():<18s} {ins.mnemonic} {ins.op_str}')
    return out

def gbk(b):
    try:
        return b.split(b'\x00')[0].decode('gbk', 'replace')
    except Exception:
        return repr(b)

print('==================================================')
print('SECT_A static dump (0x512e58, 200B):')
raw = MEM[0x512e58 - BASE: 0x512e58 - BASE + 200]
print('  all-zero?', not any(raw), ' first24=', raw[:24].hex())

print('\nName table CORPS_ATTRS_A @0x5099d8 (stride 5):')
for k in range(8):
    b = MEM[0x5099d8 - BASE + k*5: 0x5099d8 - BASE + k*5 + 5]
    print(f'  [{k}] {b.hex()}  {gbk(b)}')
print('Name table CORPS_ATTRS_B @0x509a78 (stride 5):')
for k in range(8):
    b = MEM[0x509a78 - BASE + k*5: 0x509a78 - BASE + k*5 + 5]
    print(f'  [{k}] {b.hex()}  {gbk(b)}')

print('\n==================================================')
for t, nm in DEF.items():
    sites = [s for s, tt in CALLS if tt == t]
    print(f'\n##### {nm}   ({t:#x})  callers={len(sites)} #####')
    for s in sites:
        print(f'  --- call @{s:#08x} ---')
        for line in dis_window(s, before=72, after=2):
            print('     ' + line)
