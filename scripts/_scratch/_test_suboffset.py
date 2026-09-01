#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test decoding garbled blocks (49..87, 292..369) from sub-offsets within the
9-byte slot, to see if a leading flag byte hides the name."""
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

def dec_from(chunk, off):
    s = chunk[off:]
    e = s.find(b"\x00")
    if e < 0:
        e = len(s)
    return s[:e].decode("gbk", "replace")

for blk, (lo, hi) in [("49..87", (49, 88)), ("292..369", (292, 370))]:
    print(f"\n===== block {blk} : try sub-offset 0..8 =====")
    for off in range(0, 9):
        vals = []
        for i in range(lo, hi):
            chunk = data[tbl_off + i*9 : tbl_off + i*9 + 9]
            v = dec_from(chunk, off)
            vals.append(v)
        clean = sum(1 for v in vals if "\ufffd" not in v and 0 < len(v) <= 8)
        sample = " ".join(v for v in vals[:14] if v)
        print(f"  off={off} clean={clean:2d}/79  e.g. {sample}")
