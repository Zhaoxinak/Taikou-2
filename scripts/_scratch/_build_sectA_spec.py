#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build sectA_spec.json — SECT_A naming from call-chain trace + HJMAPDAT cross-check.

Method (续17/续22): no constant-index call sites; (col,row) always from entity bytes or
map-derived helpers (0x43a420/0x43a440). Cell low nibble = terrain/move class index 0..7.
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

import json, struct, io, sys, statistics as st
from collections import defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
TEXT_END = 0x4d0000

GETLO, GETHI, SETLO = 0x439050, 0x4390c0, 0x439080

# --- static tables for cross-ref ---
def u8(a):
    return MEM[a - BASE]

def u16(a):
    return struct.unpack_from('<H', MEM, a - BASE)[0]

LUT_A = [u8(0x503138 + i) for i in range(256)]
LUT_B = [u8(0x503140 + i) for i in range(256)]
ATK_DIV = [u8(0x503770 + i) for i in range(20)]
MOVE_A = [u8(0x5036a0 + i) for i in range(8)]

# --- find all calls ---
def calls_to(target):
    out = []
    i = 0
    while True:
        i = MEM.find(b'\xe8', i, TEXT_END - BASE)
        if i < 0:
            break
        rel = struct.unpack_from('<i', MEM, i + 1)[0]
        t = (i + BASE) + 5 + rel
        if GETLO <= t <= SETLO + 0x80 or t in (GETLO, GETHI, SETLO):
            if t == target:
                out.append(i + BASE)
        i += 1
    return sorted(out)

def disasm_range(va, n):
    chunk = MEM[va - BASE: va - BASE + n]
    return list(md.disasm(chunk, va))

def classify_getlo_site(va):
    """Heuristic: what happens to AL after getLo."""
    insns = disasm_range(va, 80)
    post = []
    for ins in insns:
        if ins.address <= va:
            continue
        post.append(ins)
        if len(post) >= 12:
            break
    text = ' '.join(f'{i.mnemonic} {i.op_str}' for i in post)
    role = 'unknown'
    if '0x5036a0' in text or '0x5036a8' in text or '0x5036c0' in text or '0x5036c8' in text:
        role = 'move_cost_lut'
    elif '0x503770' in text or '0x503778' in text:
        role = 'atk_divisor_lut'
    elif '0x503138' in text or '0x503140' in text:
        role = 'post_lut_transform'
    elif 'cmp' in text and ('0x7' in text or '0x8' in text or '0xa' in text or '0x2' in text):
        role = 'class_threshold_check'
    elif '0x438b80' in text:
        role = 'bounded_passability'
    elif '0x439110' in text:
        role = 'predicate_is_class_2'
    elif 'call' in text and '0x43e870' in text:
        role = 'facility_lookup'
    tags = []
    # arg pattern from ~20 insns before call
    pre = disasm_range(va - 60, 60)
    pre_s = ' '.join(f'{i.mnemonic} {i.op_str}' for i in pre)
    if '+ 0]' in pre_s or '+ 0x0]' in pre_s:
        tags.append('arg_col_from_entity+0')
    if '+ 2]' in pre_s or '+ 0x2]' in pre_s:
        tags.append('arg_row_from_entity+2')
    if '0x43a440' in pre_s or '0x43a420' in pre_s:
        tags.append('map_spawn_derivation')
    if 'cmp' in pre_s and '0x14' in pre_s:
        tags.append('bounds_col_lt_20')
    if 'cmp' in pre_s and '0x9' in pre_s:
        tags.append('bounds_row_lt_9')
    return role, tags, text[:120]

def classify_gethi_site(va):
    insns = disasm_range(va, 60)
    post = ' '.join(f'{i.mnemonic} {i.op_str}' for i in insns if i.address > va)[:120]
    role = 'hi_nibble_combat_mod'
    if '0x42d' in post:
        role = 'damage_formula_hi_compare'
    if '0x436' in post:
        role = 'fire_tactic_hi_compare'
    return role, post[:100]

# --- HJMAPDAT stats ---
hj = open('F:/Games/Taikou2/HJMAPDAT.DAT', 'rb').read()
N = len(hj) // 1700
ca = defaultdict(list)
row_active = defaultdict(int)
for b in range(N):
    A = hj[b * 1700: b * 1700 + 180]
    for r in range(9):
        row = A[r * 20:(r + 1) * 20]
        if any(x & 0xF for x in row):
            row_active[r] += 1
        for c in range(20):
            ca[(r, c)].append(A[r * 20 + c] & 0xF)

row_profiles = {}
for r in range(9):
    row_profiles[str(r)] = {
        'active_battles': row_active[r],
        'col_means': [round(st.mean(ca[(r, c)]), 2) for c in range(20)],
    }

# row pair symmetry
mirrors = []
A0 = hj[0:180]
for a, b in [(0, 1), (7, 8), (2, 3), (4, 5)]:
    eq = A0[a * 20:(a + 1) * 20] == A0[b * 20:(b + 1) * 20]
    mirrors.append({'rows': [a, b], 'battle0_identical': eq})

# --- call site catalog ---
getlo_sites = []
for va in calls_to(GETLO):
    role, tags, snippet = classify_getlo_site(va)
    getlo_sites.append({
        'va': f'0x{va:08x}',
        'consumer_role': role,
        'arg_hints': tags,
        'post_call': snippet,
    })

gethi_sites = []
for va in calls_to(GETHI):
    role, snippet = classify_gethi_site(va)
    gethi_sites.append({
        'va': f'0x{va:08x}',
        'consumer_role': role,
        'post_call': snippet,
    })

# --- naming proposal ---
# Rows: internal deployment tier 0..8 (NOT 1:1 with 3 display classes at 0x50bfe8)
row_names = {
    '0': {'label': 'tier_0', 'note': 'battle0 mirror of tier_1; primary left-wing template band'},
    '1': {'label': 'tier_1', 'note': 'most frequently populated row (38/38 battles)'},
    '2': {'label': 'tier_2', 'note': 'secondary line; often paired with tier_3'},
    '3': {'label': 'tier_3', 'note': 'mid/ reserve; lower mean values'},
    '4': {'label': 'tier_4', 'note': 'reserve / sparse'},
    '5': {'label': 'tier_5', 'note': 'reserve / sparse'},
    '6': {'label': 'tier_6', 'note': 'special slot (row6 col0 often =1 in battle0)'},
    '7': {'label': 'tier_7', 'note': 'mirror of tier_8; right-wing template band'},
    '8': {'label': 'tier_8', 'note': 'battle0 mirror of tier_7'},
}

# Cols: 20 parameter slots — values are terrain_class_idx not column semantics
col_roles = []
for c in range(20):
    vals = [st.mean(ca[(r, c)]) for r in range(9)]
    spread = max(vals) - min(vals)
    col_roles.append({
        'col': c,
        'label': f'param_slot_{c:02d}',
        'between_tier_spread': round(spread, 2),
        'note': 'slot value indexes move/atk LUT (0..7); not a named stat column in EXE',
    })

spec = {
    'buffer': '0x512e58',
    'source': 'HJMAPDAT.DAT section A (180B per battle record)',
    'layout': {
        'formula': 'index = col + 20 * row',
        'cols': 20,
        'rows': 9,
        'getLo': '0x439050  SECT_A[col + 20*row] & 0xF',
        'getHi': '0x4390c0  SECT_A[col + 20*row] >> 4  (dead: hi nibble always 0 in 38 battles)',
        'setLo': '0x439080  write low nibble preserving hi',
    },
    'entity_binding': {
        'commander_or_unit': {
            'byte_at_0': 'col (0..19) → SECT_A column index',
            'byte_at_2': 'row (0..8) → SECT_A row index',
            'evidence': ['0x42d270 damage', '0x42d321 atkDivisor', '0x423a13', '0x438a6b movement family'],
        },
        'unit_slot_0x513910': {
            'byte_at_5': 'map_x (0..19, cmp 0x14)',
            'byte_at_7': 'map_y (coarse, pairs with x for getLo in move AI 0x423fb0)',
        },
        'index_helpers': {
            '0x43a420': 'DIR8 word table @0x503710',
            '0x43a440': 'SPAWN_TYPE word table @0x503712 (feint/dummy spawn)',
            '0x43a410': 'runtime byte table @0x512f28 (filled at battle prep 0x43a080)',
        },
    },
    'cell_value_semantics': {
        'low_nibble': {
            'name': 'terrain_class_idx',
            'range': '0..7 (8-15 unused in HJMAPDAT)',
            'consumers': {
                'move_cost': '0x438a60/aa0/af0/b30 → 0x5036a0/a8/c0/c8 (+snow via 0x43cad0)',
                'attack_divisor': '0x43a9c0 → 0x503770/778 (+ facility/height adjust)',
                'lut_remap': '0x423f90/423fa0 → 0x503138/140 (UI/placement remap)',
            },
        },
        'high_nibble': {
            'name': 'combat_mod_tier',
            'live': False,
            'intended': '0x436840 fire +50 if atk_hi > def_hi; 0x42d270 damage ±1 divisor',
        },
    },
    'rows': row_names,
    'cols': col_roles,
    'row_symmetry_battle0': mirrors,
    'row_profiles': row_profiles,
    'call_sites': {
        'getLo_count': len(getlo_sites),
        'getLo': getlo_sites,
        'getHi_count': len(gethi_sites),
        'getHi': gethi_sites,
    },
    'static_lut': {
        '0x503138_first20': LUT_A[:20],
        '0x503140_first20': LUT_B[:20],
        'atk_divisor_table': ATK_DIV,
        'move_cost_table_A': MOVE_A,
    },
    'naming_status': {
        'rows': 'partial — 9 internal tiers mapped; human JP names not in EXE (3-class table is display-only)',
        'cols': 'structural only — 20 tuning slots; no 20-string master table exists',
        'values': 'closed — terrain_class_idx into static LUTs (§3.12)',
    },
}

with open(_ROOT + '/scripts/sectA_spec.json', 'w', encoding='utf-8') as f:
    json.dump(spec, f, ensure_ascii=False, indent=2)

# summary stdout
roles = defaultdict(int)
for s in getlo_sites:
    roles[s['consumer_role']] += 1
print('wrote scripts/sectA_spec.json')
print('getLo sites by role:', dict(roles))
print('row active battles:', {r: row_active[r] for r in range(9)})
