#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Profile SNDATA 49-byte records to crack field semantics.

SNDATA1.TR2 / SNDATA2.TR2 = 16B "TAIKOU2_SCENARIO" + 833*49B + 23B tail.
We classify records and profile every byte offset [0:49] to find
id-like (small range), flag-like (0/1), and payload structure.
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

import struct, collections, os, json

ROOT = "F:/Games/Taikou2"
OUT = _ROOT + '/scripts'

def load(path):
    raw = open(os.path.join(ROOT, path), "rb").read()
    assert raw[:16] == b"TAIKOU2_SCENARIO", raw[:16]
    body = raw[16:]
    n = (len(body) - 23) // 49
    recs = [body[i*49:(i+1)*49] for i in range(n)]
    return recs, raw

def classify(rec):
    if rec == bytes(49):
        return "allzero"
    # fill-slot patterns: single repeated byte (0xff/0x0c/0xf3) or two-byte repeat
    if len(set(rec)) == 1:
        return f"fill-{rec[0]:02x}"
    return "datablock"

scenarios = {"scenario1": "SNDATA1.TR2", "scenario2": "SNDATA2.TR2"}
profiles = {}
for sc, fn in scenarios.items():
    recs, _ = load(fn)
    n = len(recs)
    # per-offset distinct-value profile
    offset_profile = []
    for off in range(49):
        vals = [r[off] for r in recs]
        c = collections.Counter(vals)
        distinct = len(c)
        offset_profile.append({
            "off": off,
            "distinct": distinct,
            "min": min(vals), "max": max(vals),
            "zero_frac": c.get(0,0)/n,
            "top": c.most_common(6),
        })
    # record classification
    classes = collections.Counter(classify(r) for r in recs)
    # id_word / sub_word / flag / rel_word distributions
    id_words = collections.Counter(struct.unpack("<H", r[0:2])[0] for r in recs)
    sub_words = collections.Counter(struct.unpack("<H", r[4:6])[0] for r in recs)
    flags = collections.Counter(r[6] for r in recs)
    rel_words = collections.Counter(struct.unpack("<H", r[12:14])[0] for r in recs)
    profiles[sc] = {
        "n": n, "classes": dict(classes),
        "offset_profile": offset_profile,
        "id_words": {f"0x{v:04x}": c for v,c in id_words.most_common(25)},
        "sub_words_top": {f"0x{v:04x}": c for v,c in sub_words.most_common(15)},
        "flags": {f"0x{v:02x}": c for v,c in flags.most_common()},
        "rel_words_top": {f"0x{v:04x}": c for v,c in rel_words.most_common(15)},
    }
    print(f"=== {sc}: {n} records ===")
    print("  classes:", dict(classes))
    print("  id_words top:", list(id_words.most_common(8)))
    print("  sub_words top:", list(sub_words.most_common(8)))
    print("  flags:", dict(flags))
    print("  rel_words top:", list(rel_words.most_common(8)))

# Print the offset profile table for scenario1 (the informative one)
print("\n=== offset profile (scenario1) ===")
print(" off  distinct  min  max  zero%   top6(values:count)")
for p in profiles["scenario1"]["offset_profile"]:
    top = " ".join(f"{v}:{c}" for v,c in p["top"])
    print(f"  {p['off']:2d}   {p['distinct']:3d}    {p['min']:3d}  {p['max']:3d}  {p['zero_frac']*100:5.1f}%  {top}")

# Cross-scenario offset correlation: which offsets change between sc1/sc2
sc1 = load("SNDATA1.TR2")[0]
sc2 = load("SNDATA2.TR2")[0]
diff_offs = [o for o in range(49) if any(sc1[i][o]!=sc2[i][o] for i in range(len(sc1)))]
same_offs = [o for o in range(49) if all(sc1[i][o]==sc2[i][o] for i in range(len(sc1)))]
print(f"\n=== cross-scenario: {len(diff_offs)} offsets differ, {len(same_offs)} identical ===")
print("  identical offsets:", same_offs)
print("  differing offsets:", diff_offs)

# Save profile
json.dump(profiles, open(os.path.join(OUT, "_sndata_profile.json"), "w"), indent=1)
print("\nsaved _sndata_profile.json")
