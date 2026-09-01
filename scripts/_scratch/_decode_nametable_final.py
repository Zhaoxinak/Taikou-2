#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final decode of 0x506ca8 name table.
Blocks:
  0..48    provinces      (name @ offset 0, null-term GBK)
  49..87   extra places?  (flag-prefixed, variable)
  88..291  castles+towns  (name @ offset 0); castle id c -> index 88+c (verified 82/92)
  292..369 role/职种 types (flag-prefixed, variable)
We pick per-slot the decode (offset 0/1/2) that is cleanest (no U+FFFD) and longest.
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

import json, os
SC = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(SC, _ROOT + '/scripts/_unpacked_mem.bin')
BASE = 0x400000
data = open(BIN, "rb").read()
tbl_off = 0x506ca8 - BASE

def try_dec(chunk, off):
    s = chunk[off:]
    e = s.find(b"\x00")
    if e < 0:
        e = len(s)
    txt = s[:e].decode("gbk", "replace")
    clean = "\ufffd" not in txt
    return txt, clean, len(txt)

def best_dec(chunk):
    cands = []
    for off in (0, 1, 2):
        if off >= len(chunk):
            continue
        txt, clean, ln = try_dec(chunk, off)
        if clean and ln > 0:
            cands.append((ln, off, txt))
    if cands:
        cands.sort(key=lambda x: (-x[0], x[1]))
        return cands[0][2]
    # fallback: first clean-ish
    for off in (0, 1, 2):
        txt, clean, ln = try_dec(chunk, off)
        if txt:
            return txt
    return ""

def slot(i):
    return data[tbl_off + i*9 : tbl_off + i*9 + 9]

provinces = [best_dec(slot(i)) for i in range(0, 49)]
gap       = [best_dec(slot(i)) for i in range(49, 88)]
castles   = [best_dec(slot(i)) for i in range(88, 292)]
types     = [best_dec(slot(i)) for i in range(292, 370)]

print("PROVINCES (0..48):")
print("  ", [p for p in provinces])
print("\nGAP 49..87 (best-effort, flag-prefixed):")
print("  ", [g for g in gap])
print("\nTYPES 292..369 (best-effort, flag-prefixed):")
print("  ", [t for t in types])

# Save
out = {
    "va": "0x506ca8",
    "stride": 9,
    "layout": {
        "provinces": "0..48 (49 国, name @off0)",
        "extra_places": "49..87 (39, flag-prefixed, semantic uncertain)",
        "castles_towns": "88..291 (204 places; castle id c -> index 88+c, verified 82/92 vs towns.json; 10 are authentic alt names)",
        "role_types": "292..369 (78 职种/role names, flag-prefixed)"
    },
    "province_names": provinces,
    "extra_place_names": gap,
    "castle_town_names": castles,
    "role_type_names": types,
}
json.dump(out, open(os.path.join(SC, "name_table.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote name_table.json")
