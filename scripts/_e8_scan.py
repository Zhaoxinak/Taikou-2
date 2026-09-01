# -*- coding: utf-8 -*-
"""Scan for E8-relative CALL sites whose target is a given VA. This finds callers
even when there's no absolute immediate reference (the 'no immediate ref' case)."""
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

import os, struct

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
BASE = 0x400000

def find_callers(target):
    hits = []
    n = len(IMG)
    i = 0
    while i < n - 5:
        if IMG[i] == 0xE8:
            rel = struct.unpack_from("<i", IMG, i + 1)[0]
            site = BASE + i
            tgt = site + 5 + rel
            if tgt == target:
                hits.append(site)
        i += 1
    return hits

for t, name in ((0x47ff68, "DISPATCHER 0x47ff68"),
                (0x47fc60, "FANOUT 0x47fc60"),
                (0x4e8625, "LOOP1 0x4e8625"),
                (0x4882b1, "0x4882b1")):
    h = find_callers(t)
    print("%s: %d E8-call sites" % (name, len(h)))
    for s in h[:20]:
        print("    call at 0x%06x" % s)
