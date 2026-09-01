# -*- coding: utf-8 -*-
"""
Map the battle-simulation code cluster: split into functions, score each by
arithmetic density / rand() usage / references to known battle data tables.

Goal: locate the per-tick damage / combat-resolution function(s).
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

import sys, io, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from capstone import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()

def rd(va, n):
    off = va - BASE
    return MEM[off:off + n]

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# known battle-related data addresses
KNOWN = {
    0x512868: 'TERRAIN_MAP(760)',
    0x512b60: 'DEPLOY_MAP/UNIT_ARR(stride8)',
    0x512e58: 'SECT_A_PARAMS(9x20)',
    0x512f10: 'DEPLOY_SPRITE_TAB(20)',
    0x513a78: 'TERRAIN_ATTR(5x16)',
    0x503138: 'LUT_A(val curve)',
    0x503140: 'LUT_B(val curve)',
    0x503710: 'DIR8_OFFSETS',
    0x503740: 'TIER_THR',
    0x503750: 'TIER_BASE',
    0x503760: 'TIER_RND',
    0x522ce4: 'CITY_OWNER_BITS(92)',
    0x519868: 'ENTITY_TAB(370x47)',
    0x524978: 'VISUAL_POOL',
}
RAND = {0x4ebd30: 'rand()', 0x4ebd60: 'rand()%n'}
ACCESSORS = {
    0x439050: 'getLo(a,c)',
    0x4390c0: 'getHi(a,c)',
    0x439080: 'setLo(a,c)',
    0x43e820: 'terrainAttr(i)',
    0x43e8b0: 'terrainScan',
    0x43a460: 'pickVariant',
}

START, END = 0x438800, 0x43ac00

# --- pass 1: find function starts (push ebp; mov ebp,esp) and all call targets
insns = []
va = START
while va < END:
    chunk = rd(va, min(4096, END - va))
    got = False
    for ins in md.disasm(chunk, va):
        insns.append(ins)
        va = ins.address + ins.size
        got = True
    if not got:
        va += 1

by_addr = {i.address: i for i in insns}
starts = set()
for idx, ins in enumerate(insns):
    if ins.mnemonic == 'push' and ins.op_str == 'ebp':
        nxt = insns[idx + 1] if idx + 1 < len(insns) else None
        if nxt and nxt.mnemonic == 'mov' and nxt.op_str in ('ebp, esp',):
            starts.add(ins.address)

call_targets = collections.Counter()
for ins in insns:
    if ins.mnemonic == 'call' and ins.op_str.startswith('0x'):
        try:
            t = int(ins.op_str, 16)
        except ValueError:
            continue
        call_targets[t] += 1
        if START <= t < END:
            starts.add(t)

starts = sorted(starts)
print(f'[*] region {START:#x}-{END:#x}  insns={len(insns)}  functions={len(starts)}')

# --- pass 2: per-function profile
ARITH = {'imul', 'mul', 'idiv', 'div', 'sar', 'shl', 'shr', 'add', 'sub', 'inc', 'dec', 'neg', 'and', 'or', 'xor'}
HEAVY = {'imul', 'mul', 'idiv', 'div'}

bounds = list(zip(starts, starts[1:] + [END]))
profiles = []
for s, e in bounds:
    body = [i for i in insns if s <= i.address < e]
    if not body:
        continue
    mn = collections.Counter(i.mnemonic for i in body)
    heavy = sum(mn[m] for m in HEAVY)
    arith = sum(mn[m] for m in ARITH)
    refs, rands, accs, outcalls = set(), 0, set(), set()
    for i in body:
        txt = i.op_str
        for a, nm in KNOWN.items():
            if f'{a:#x}' in txt:
                refs.add(nm)
        if i.mnemonic == 'call' and txt.startswith('0x'):
            try:
                t = int(txt, 16)
            except ValueError:
                continue
            if t in RAND:
                rands += 1
            elif t in ACCESSORS:
                accs.add(ACCESSORS[t])
            else:
                outcalls.add(t)
    profiles.append(dict(start=s, end=e, n=len(body), heavy=heavy, arith=arith,
                         refs=refs, rands=rands, accs=accs, outcalls=outcalls,
                         xrefs=call_targets.get(s, 0), cmp=mn['cmp'], jcc=sum(v for k, v in mn.items() if k.startswith('j') and k != 'jmp')))

print()
print('addr       size  ins  imul/div arith cmp jcc rand xref  accessors            tables')
print('-' * 118)
for p in sorted(profiles, key=lambda x: -(x['heavy'] * 10 + len(x['accs']) * 5 + len(x['refs']) * 3)):
    if p['heavy'] == 0 and not p['accs'] and not p['refs']:
        continue
    print(f"{p['start']:#08x} {p['end']-p['start']:5d} {p['n']:4d} {p['heavy']:8d} {p['arith']:5d} "
          f"{p['cmp']:3d} {p['jcc']:3d} {p['rands']:4d} {p['xrefs']:4d}  "
          f"{','.join(sorted(p['accs'])):20s} {','.join(sorted(p['refs']))}")

print()
print('[*] all functions in region (addr size ins) :')
line = []
for p in sorted(profiles, key=lambda x: x['start']):
    line.append(f"{p['start']:#x}/{p['end']-p['start']}")
print('  ' + '  '.join(line))
