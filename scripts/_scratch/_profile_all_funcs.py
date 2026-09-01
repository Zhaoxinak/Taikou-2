# -*- coding: utf-8 -*-
"""
Whole-image function profiler.

Function starts = all `call rel32` targets (this binary has almost no
frame-pointer prologues). For every function, count:
  - multiply / divide instructions (formula fingerprint)
  - rand() calls
  - calls to battle entity accessors
  - references to battle data tables

Then rank candidates for "combat resolution / numeric formula".
"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import sys, io, struct, bisect, collections, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
TEXT_START, TEXT_END = 0x401000, 0x4d0000
md = Cs(CS_ARCH_X86, CS_MODE_32)

CALLSYM = {
    0x439050: 'getLo', 0x4390c0: 'getHi', 0x439080: 'setLo',
    0x43e820: 'terrAttr', 0x43e4a0: 'slot15',      # 0x513910 + i*24
    0x4ebd30: 'rand', 0x4ebd60: 'randmod',
    0x423f90: 'LUTA', 0x423fa0: 'LUTB',
}
DATASYM = {
    0x513910: 'SLOT15', 0x512b60: 'UNITARR', 0x512e58: 'SECTA',
    0x512868: 'TERRAIN', 0x513a78: 'TERRATTR', 0x511358: 'GAUGE40',
    0x519868: 'ENTITY370', 0x522ce4: 'CITYOWN',
}

# ---- collect calls
calls = []
i = 0
lim = TEXT_END - BASE
while True:
    i = MEM.find(b'\xe8', i, lim)
    if i < 0:
        break
    rel = struct.unpack_from('<i', MEM, i + 1)[0]
    t = (i + BASE) + 5 + rel
    if TEXT_START <= t < TEXT_END:
        calls.append((i + BASE, t))
    i += 1
targets = collections.Counter(t for _, t in calls)
starts = sorted(targets)
print(f'[*] {len(calls)} call sites, {len(starts)} function starts')

def fidx(va):
    k = bisect.bisect_right(starts, va) - 1
    return starts[k] if k >= 0 else None

# ---- disassemble each function up to next start (cap 4KB)
MULDIV = {'imul', 'mul', 'idiv', 'div'}
prof = {}
for n, s in enumerate(starts):
    e = starts[n + 1] if n + 1 < len(starts) else TEXT_END
    e = min(e, s + 4096)
    body = MEM[s - BASE:e - BASE]
    md_ = md
    muldiv = shifts = cmps = total = 0
    cur = s
    while cur < e:
        got = 0
        for ins in md_.disasm(MEM[cur - BASE:e - BASE], cur):
            total += 1
            if ins.mnemonic in MULDIV:
                muldiv += 1
            elif ins.mnemonic in ('sar', 'shr', 'shl'):
                shifts += 1
            elif ins.mnemonic == 'cmp':
                cmps += 1
            cur = ins.address + ins.size
            got += 1
        if got == 0:
            cur += 1
    prof[s] = dict(size=e - s, ins=total, muldiv=muldiv, shifts=shifts, cmps=cmps,
                   xref=targets[s], sym=collections.Counter(), data=collections.Counter())

# ---- attribute call symbols
for site, t in calls:
    nm = CALLSYM.get(t)
    if nm:
        f = fidx(site)
        if f in prof:
            prof[f]['sym'][nm] += 1

# ---- attribute data refs (byte scan, alignment independent)
for addr, nm in DATASYM.items():
    pat = struct.pack('<I', addr)
    pos = TEXT_START - BASE
    while True:
        j = MEM.find(pat, pos, lim)
        if j < 0:
            break
        f = fidx(j + BASE)
        if f in prof:
            prof[f]['data'][nm] += 1
        pos = j + 1

# ---- rank: numeric formula in a battle context
rows = []
for s, p in prof.items():
    sy, da = p['sym'], p['data']
    battle = (sy['getLo'] + sy['getHi'] + sy['setLo'] + sy['terrAttr'] + sy['slot15']
              + da['SLOT15'] + da['UNITARR'] + da['SECTA'] + da['TERRAIN'] + da['TERRATTR'])
    score = p['muldiv'] * 5 + battle * 6 + (sy['rand'] + sy['randmod']) * 3
    if score > 0:
        rows.append((score, s, p, battle))

print()
print('score  func       size  ins muldiv shf cmp xref  calls                        data')
print('-' * 122)
for score, s, p, battle in sorted(rows, reverse=True)[:35]:
    print(f'{score:5d}  {s:#08x} {p["size"]:5d} {p["ins"]:4d} {p["muldiv"]:6d} {p["shifts"]:3d} '
          f'{p["cmps"]:3d} {p["xref"]:4d}  '
          f'{",".join(f"{k}x{v}" for k,v in p["sym"].most_common()):28s} '
          f'{",".join(f"{k}x{v}" for k,v in p["data"].most_common())}')

json.dump({f'{s:#x}': {k: (dict(v) if isinstance(v, collections.Counter) else v)
                       for k, v in p.items()} for s, p in prof.items() if p['muldiv'] or p['sym'] or p['data']},
          open(_ROOT + '/scripts/_func_profile.json', 'w'), indent=1)
print('\n[+] wrote scripts/_func_profile.json')
