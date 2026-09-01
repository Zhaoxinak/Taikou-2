# -*- coding: utf-8 -*-
"""Byte-scan the whole image for absolute function pointers to 0x47ff68 / 0x47fc60
(and a few other decoder candidates) to locate the dispatch table."""
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

targets = {
    0x47ff68: "DISPATCHER",
    0x47fc60: "FANOUT",
    0x4e8625: "LOOP1",
    0x4e89cd: "LOOP2",
    0x4882b1: "CALLER4882b1",
    0x47fb80: "0x47fb80",
    0x47adc0: "0x47adc0",
}

for va, name in targets.items():
    pat = struct.pack("<I", va)
    hits = []
    start = 0
    while True:
        i = IMG.find(pat, start)
        if i < 0:
            break
        hits.append(BASE + i)
        start = i + 1
    # classify: is it in a code region (function) or data region (table)?
    print("%s (0x%06x): %d hits" % (name, va, len(hits)))
    for h in hits[:12]:
        print("    ptr at 0x%06x" % h)
