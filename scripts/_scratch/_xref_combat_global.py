# -*- coding: utf-8 -*-
"""
Global xref sweep across the whole .text for combat-relevant symbols:
  - value-curve LUTs 0x503138 / 0x503140
  - section-A accessors 0x439050 / 0x4390c0 / 0x439080
  - terrain attr accessor 0x43e820
  - unit instance array 0x512b60, param table 0x512e58, terrain 0x512868
Then group hits by enclosing function to reveal the true combat-resolution cluster.
"""
import sys, io, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
TEXT_START, TEXT_END = 0x401000, 0x4d0000   # code region of the unpacked image

md = Cs(CS_ARCH_X86, CS_MODE_32)

TARGETS = {
    0x503138: 'LUT_A', 0x503140: 'LUT_B',
    0x439050: 'getLo', 0x4390c0: 'getHi', 0x439080: 'setLo',
    0x43e820: 'terrainAttr',
    0x512868: 'TERRAIN', 0x512b60: 'UNITARR', 0x512e58: 'PARAMS',
    0x4ebd30: 'rand', 0x4ebd60: 'randmod',
}
TARGET_STRS = {f'{a:#x}': nm for a, nm in TARGETS.items()}

# linear disassembly of whole text, tracking last prologue as "current function"
print('[*] disassembling .text (with resync) ...')
insns = []
va = TEXT_START
while va < TEXT_END:
    chunk = MEM[va - BASE: TEXT_END - BASE]
    n = 0
    for ins in md.disasm(chunk, va):
        insns.append(ins)
        va = ins.address + ins.size
        n += 1
    if n == 0:
        va += 1          # resync past undecodable byte
print(f'    {len(insns)} instructions')

# find prologues
prologue = []
for i in range(len(insns) - 1):
    if insns[i].mnemonic == 'push' and insns[i].op_str == 'ebp' \
       and insns[i + 1].mnemonic == 'mov' and insns[i + 1].op_str == 'ebp, esp':
        prologue.append(insns[i].address)
prologue_set = sorted(prologue)
print(f'    {len(prologue_set)} prologues')

import bisect
def func_of(va):
    k = bisect.bisect_right(prologue_set, va) - 1
    return prologue_set[k] if k >= 0 else None

hits = collections.defaultdict(collections.Counter)   # func -> sym counter
detail = collections.defaultdict(list)
for ins in insns:
    txt = ins.op_str
    if '0x5' not in txt and '0x4' not in txt:
        continue
    for s, nm in TARGET_STRS.items():
        if s in txt:
            f = func_of(ins.address)
            hits[f][nm] += 1
            detail[f].append((ins.address, nm, ins.mnemonic, txt))

print()
print('func       hits  symbols')
print('-' * 100)
for f, c in sorted(hits.items(), key=lambda kv: -sum(kv[1].values())):
    if f is None:
        continue
    tot = sum(c.values())
    if tot < 1:
        continue
    print(f'{f:#08x} {tot:5d}  ' + ', '.join(f'{k}x{v}' for k, v in c.most_common()))

# spotlight: functions that touch LUT_A or LUT_B (the effective-value curves)
print()
print('=' * 100)
print('LUT users (value-curve consumers = likely combat resolution):')
for f, c in sorted(hits.items(), key=lambda kv: kv[0] or 0):
    if f is None:
        continue
    if c['LUT_A'] or c['LUT_B']:
        print(f'\n--- func {f:#x}  ({", ".join(f"{k}x{v}" for k,v in c.most_common())})')
        for va, nm, mn, txt in detail[f]:
            print(f'    {va:#08x}  {mn:8s} {txt:44s} ; {nm}')
