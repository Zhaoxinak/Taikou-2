#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump raw 9-byte slots for representative entries of each block to determine
the exact in-slot name layout (flag prefix? null termination?)."""
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

import os
SC = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(SC, _ROOT + '/scripts/_unpacked_mem.bin')
BASE = 0x400000
data = open(BIN, "rb").read()
tbl_off = 0x506ca8 - BASE

def raw(i):
    return data[tbl_off + i*9 : tbl_off + i*9 + 9]

def show(label, idxs):
    print(f"\n--- {label} ---")
    for i in idxs:
        b = raw(i)
        hexs = " ".join(f"{x:02x}" for x in b)
        # try decode from each offset
        tries = {}
        for off in range(0, 9):
            s = b[off:]
            e = s.find(b"\x00")
            e = len(s) if e < 0 else e
            tries[off] = s[:e].decode("gbk", "replace")
        print(f"  [{i:3d}] {hexs}  | o0={tries[0]!r} o1={tries[1]!r} o2={tries[2]!r} o3={tries[3]!r}")

show("provinces (clean @0)", [0, 1, 16, 48])
show("castle block (clean @0)", [88, 89, 154, 179, 288, 291])
show("gap 49..87", [49, 50, 56, 63, 77, 87])
show("type block 292..369", [292, 293, 296, 300, 301, 313, 320, 327, 334, 344, 351, 366, 368, 369])
