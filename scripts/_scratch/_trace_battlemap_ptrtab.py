#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trace battle-map resource-name strings through their pointer table in the
unpacked EXE memory image, then locate the loader functions that reference
the table.

Strategy:
 1. Confirm the string bytes live at the expected VA in the dump.
 2. Search the whole dump for 4-byte LE pointers to each string VA.
 3. Collect all such pointers -> recover the resource-name pointer table
    (base, count, span).
 4. Find code references (CALL / PUSH / MOV) to the table base, or to
    individual entries, to locate the loaders.
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

import struct, re

DUMP = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000  # image base in the dump

with open(DUMP, "rb") as f:
    data = f.read()

print(f"dump size = {len(data)} (0x{len(data):x})")

# --- 1. confirm strings at expected VAs ---
battle_strings = {
    "C:HJMAPDAT.DAT": 0x5036f2,
    "C:HBMAP.LZW":    0x5030da,
    "C:HJMAP.LZW":    0x5034c2,
    "C:HKMAP.LZW":    0x5034e2,
    # other known battle-ish strings from prior analysis
    "C:HKMAPDAT.LZW": None,
    "C:HKMAPNEW.LZW": None,
    "C:HBOBJ.DAT":    None,
}

print("\n=== 1. string bytes at expected VAs ===")
for name, va in battle_strings.items():
    if va is None:
        continue
    off = va - BASE
    chunk = data[off:off+len(name)]
    ok = chunk == name.encode("ascii")
    print(f"  VA 0x{va:06x}  expect={name!r:20}  got={chunk!r}  {'OK' if ok else 'MISMATCH'}")

# --- 2. search for 4-byte LE pointers to each string VA ---
# First, locate the actual VAs of all battle strings by scanning for the
# ASCII names in the dump (in case VA math is off).
print("\n=== 2. locate string VAs by scanning ASCII ===")
found = {}
for name in battle_strings:
    nb = name.encode("ascii")
    idx = data.find(nb)
    if idx >= 0:
        va = idx + BASE
        found[name] = va
        print(f"  {name!r:20} -> VA 0x{va:06x} (file off 0x{idx:x})")
    else:
        print(f"  {name!r:20} -> NOT FOUND in dump")

# --- 3. search for 4-byte LE pointers to each located VA ---
print("\n=== 3. pointer-table entries (4-byte LE -> string VA) ===")
entries = {}  # va -> list of referencing file offsets
for name, va in found.items():
    target = struct.pack("<I", va)
    refs = []
    start = 0
    while True:
        i = data.find(target, start)
        if i < 0:
            break
        refs.append(i + BASE)
        start = i + 1
    entries[va] = refs
    print(f"  {name!r:20} VA=0x{va:06x}  referenced at {len(refs)} place(s): "
          + (", ".join(f"0x{r:06x}" for r in refs[:8]) + (" ..." if len(refs) > 8 else "")))

# --- 4. recover pointer table bounds ---
print("\n=== 4. pointer table recovery ===")
all_refs = sorted({r for refs in entries.values() for r in refs})
if all_refs:
    print(f"  all pointer-table entry VAs: {len(all_refs)}")
    for r in all_refs:
        # try to read the pointer stored there
        off = r - BASE
        ptr = struct.unpack_from("<I", data, off)[0]
        # which string does it point to?
        pts_to = [n for n, v in found.items() if v == ptr]
        print(f"    entry VA=0x{r:06x}  -> 0x{ptr:06x}  {pts_to}")
    # table bounds: min/max
    tmin = min(all_refs)
    tmax = max(all_refs)
    print(f"  table span: 0x{tmin:06x} .. 0x{tmax:06x}  ({(tmax-tmin)//4 + 1} slots @4B)")
else:
    print("  NO direct pointer-table references found (string accessed differently).")
