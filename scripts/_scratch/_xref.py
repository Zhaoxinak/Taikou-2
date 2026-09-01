#!/usr/bin/env python3

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
# xref: find occurrences of a VA as a 4-byte LE immediate anywhere in the image.
# Usage: python _xref.py 0x504603 0x504941 0x503b08 0x504658
import sys, struct

BIN = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
data = open(BIN, "rb").read()

targets = [int(a, 16) for a in sys.argv[1:]]
print(f"image {len(data)} bytes, base 0x{BASE:x}", flush=True)
for va in targets:
    imm = struct.pack("<I", va)
    hits = []
    start = 0
    while True:
        i = data.find(imm, start)
        if i < 0:
            break
        hits.append(BASE + i)
        start = i + 1
    print(f"\nVA 0x{va:06x} ({imm.hex()}) -> {len(hits)} xrefs")
    for h in hits:
        print(f"    ref @ 0x{h:06x}")
