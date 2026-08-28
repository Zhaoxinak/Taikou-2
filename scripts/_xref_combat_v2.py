# -*- coding: utf-8 -*-
"""
Combat xref map, v2.

The binary has almost no `push ebp; mov ebp,esp` prologues (only 80 in 2 MB),
so function starts are derived from the set of all `call rel32` targets.

Output: per-function tally of combat-relevant symbol usage, so we can pin the
per-tick combat-resolution function.
"""
import sys, io, struct, collections, bisect, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
TEXT_START, TEXT_END = 0x401000, 0x4d0000
md = Cs(CS_ARCH_X86, CS_MODE_32)

DATA_TARGETS = {
    0x503138: 'LUT_A', 0x503140: 'LUT_B',
    0x512868: 'TERRAIN', 0x512b60: 'UNITARR', 0x512e58: 'PARAMS',
    0x512f10: 'SPRITETAB', 0x513a78: 'TERRAINATTR',
    0x503710: 'DIR8',
}
CALL_TARGETS = {
    0x439050: 'getLo', 0x4390c0: 'getHi', 0x439080: 'setLo',
    0x43e820: 'terrainAttr', 0x43e8b0: 'terrainScan',
    0x4ebd30: 'rand', 0x4ebd60: 'randmod',
}

# ---------- pass 1: collect every call rel32 in the image ----------
calls = []                     # (site_va, target_va)
i = 0
end = TEXT_END - BASE
while True:
    i = MEM.find(b'\xe8', i, end)
    if i < 0:
        break
    if i + 5 <= len(MEM):
        rel = struct.unpack_from('<i', MEM, i + 1)[0]
        tgt = (i + BASE) + 5 + rel
        if TEXT_START <= tgt < TEXT_END:
            calls.append((i + BASE, tgt))
    i += 1

tgt_count = collections.Counter(t for _, t in calls)
# keep targets called at least twice OR referenced by known symbol set -> function starts
func_starts = sorted({t for t, c in tgt_count.items() if c >= 1})
print(f'[*] call sites={len(calls)}  distinct call targets(=func starts)={len(func_starts)}')

def func_of(va):
    k = bisect.bisect_right(func_starts, va) - 1
    return func_starts[k] if k >= 0 else None

hits = collections.defaultdict(list)

def instr_at(off, cover):
    for back in range(0, 12):
        s = off - back
        if s < 0:
            continue
        for ins in md.disasm(MEM[s:s + 16], s + BASE):
            if (ins.address - BASE) <= cover < (ins.address - BASE) + ins.size:
                return ins
            break
    return None

# ---------- pass 2: absolute data refs ----------
for addr, nm in DATA_TARGETS.items():
    pat = struct.pack('<I', addr)
    pos = TEXT_START - BASE
    while True:
        j = MEM.find(pat, pos, end)
        if j < 0:
            break
        ins = instr_at(j, j)
        va = ins.address if ins else j + BASE
        mn = ins.mnemonic if ins else 'data'
        op = ins.op_str if ins else f'{addr:#x}'
        # keep only refs where the decoded instruction really names the address
        if ins is None or f'{addr:#x}' in op:
            hits[func_of(va)].append((va, nm, mn, op))
        pos = j + 1

# ---------- pass 3: call refs ----------
for site, tgt in calls:
    nm = CALL_TARGETS.get(tgt)
    if nm:
        hits[func_of(site)].append((site, nm, 'call', f'{tgt:#x}'))

# ---------- report ----------
rows = []
for f, lst in hits.items():
    c = collections.Counter(x[1] for x in lst)
    score = (c['getLo'] + c['getHi']) * 4 + c['terrainAttr'] * 4 + c['TERRAINATTR'] * 6 \
            + c['UNITARR'] * 3 + c['PARAMS'] * 3 + c['TERRAIN'] * 2 + c['DIR8'] * 2 \
            + (c['rand'] + c['randmod'])
    rows.append((f, len(lst), c, score))

print()
print('func        refs score  symbols')
print('-' * 110)
for f, n, c, s in sorted(rows, key=lambda r: -r[3])[:32]:
    fs = f'{f:#08x}' if f else '   ??   '
    print(f'{fs} {n:5d} {s:5d}  ' + ', '.join(f'{k}x{v}' for k, v in c.most_common()))

# dump the top combat candidates' ref detail
print()
print('=' * 110)
TOP = [f for f, n, c, s in sorted(rows, key=lambda r: -r[3])[:8] if f]
for f in TOP:
    print(f'\n--- func {f:#x}')
    for va, nm, mn, op in sorted(hits[f]):
        print(f'    {va:#08x}  {mn:9s} {op:44s} ; {nm}')

json.dump({f'{f:#x}': collections.Counter(x[1] for x in lst) for f, lst in hits.items() if f},
          open('scripts/_combat_xref_map.json', 'w'), indent=1)
print('\n[+] wrote scripts/_combat_xref_map.json')
