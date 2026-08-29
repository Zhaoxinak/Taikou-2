# -*- coding: utf-8 -*-
"""
Alignment-independent xref finder.

1. Locate every raw little-endian 32-bit occurrence of each target address in .text.
2. Recover the enclosing instruction by trying backward start offsets.
3. Recover the enclosing function by scanning back for the `55 8B EC` prologue.
"""
import sys, io, struct, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
TEXT_START, TEXT_END = 0x401000, 0x4d0000
md = Cs(CS_ARCH_X86, CS_MODE_32)

TARGETS = {
    0x503138: 'LUT_A', 0x503140: 'LUT_B',
    0x512868: 'TERRAIN', 0x512b60: 'UNITARR', 0x512e58: 'PARAMS',
    0x512f10: 'SPRITETAB', 0x513a78: 'TERRAINATTR',
}
# call-based targets: find E8 rel32 encodings instead
CALL_TARGETS = {
    0x439050: 'getLo', 0x4390c0: 'getHi', 0x439080: 'setLo',
    0x43e820: 'terrainAttr', 0x4ebd30: 'rand', 0x4ebd60: 'randmod',
}

PROLOGUE = b'\x55\x8b\xec'

def find_prologue_before(off, limit=0x2000):
    best = -1
    lo = max(0, off - limit)
    idx = MEM.rfind(PROLOGUE, lo, off + 1)
    return idx

def instr_at_covering(off, target_off):
    """try start offsets to find an instruction whose bytes cover target_off"""
    for back in range(1, 12):
        s = off - back
        if s < 0:
            continue
        for ins in md.disasm(MEM[s:s + 16], s + BASE):
            ie = (ins.address - BASE) + ins.size
            if (ins.address - BASE) <= target_off < ie:
                return ins
            break
    return None

hits = collections.defaultdict(list)   # func_va -> list of (va, sym, mnemonic, op_str)

# --- absolute data references
for addr, nm in TARGETS.items():
    pat = struct.pack('<I', addr)
    pos = TEXT_START - BASE
    end = TEXT_END - BASE
    while True:
        i = MEM.find(pat, pos, end)
        if i < 0:
            break
        ins = instr_at_covering(i, i)
        pr = find_prologue_before(i)
        fva = pr + BASE if pr >= 0 else None
        if ins:
            hits[fva].append((ins.address, nm, ins.mnemonic, ins.op_str))
        else:
            hits[fva].append((i + BASE, nm + '?', 'data', f'{addr:#x}'))
        pos = i + 1

# --- call references (E8 rel32)
for addr, nm in CALL_TARGETS.items():
    pos = TEXT_START - BASE
    end = TEXT_END - BASE
    while pos < end:
        i = MEM.find(b'\xe8', pos, end)
        if i < 0:
            break
        rel = struct.unpack_from('<i', MEM, i + 1)[0]
        tgt = (i + BASE) + 5 + rel
        if tgt == addr:
            pr = find_prologue_before(i)
            fva = pr + BASE if pr >= 0 else None
            hits[fva].append((i + BASE, nm, 'call', f'{addr:#x}'))
        pos = i + 1

print('func        hits  symbols')
print('-' * 104)
rows = []
for f, lst in hits.items():
    c = collections.Counter(x[1] for x in lst)
    rows.append((f, len(lst), c))
for f, n, c in sorted(rows, key=lambda r: -r[1]):
    fs = f'{f:#08x}' if f else '   ??   '
    print(f'{fs} {n:5d}  ' + ', '.join(f'{k}x{v}' for k, v in c.most_common()))

print()
print('=' * 104)
print('LUT_A/LUT_B consumers (effective-value curves -> combat resolution):')
for f, lst in sorted(hits.items(), key=lambda kv: kv[0] or 0):
    syms = {x[1] for x in lst}
    if 'LUT_A' in syms or 'LUT_B' in syms:
        fs = f'{f:#x}' if f else '??'
        print(f'\n--- func {fs}   ({len(lst)} refs)')
        for va, nm, mn, txt in sorted(lst):
            print(f'    {va:#08x}  {mn:8s} {txt:46s} ; {nm}')
