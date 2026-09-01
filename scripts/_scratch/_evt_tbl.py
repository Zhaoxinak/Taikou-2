# -*- coding: utf-8 -*-
"""Locate function-pointer tables containing a target VA as a 4-byte LE immediate,
then dump the surrounding table of pointers (candidate opcode->handler table)."""
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

import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()

def va2off(va): return va - BASE

TARGETS = [int(a,16) for a in sys.argv[1:]] if len(sys.argv)>1 else [0x4e82c0]
needles = {t: struct.pack('<I', t) for t in TARGETS}

hits = {t: [] for t in TARGETS}
for t in TARGETS:
    nb = needles[t]
    start = 0
    while True:
        i = MEM.find(nb, start)
        if i < 0: break
        hits[t].append(BASE + i)
        start = i + 1

for t in TARGETS:
    print(f"=== {t:#010x} appears {len(hits[t])} times as data ===")
    for off in hits[t]:
        print(f"  data at {off:#010x} (file {off-BASE})")
        # dump 64 bytes around it as 4-byte LE pointers
        lo = max(0, (off-BASE)-32)
        chunk = MEM[lo:(off-BASE)+64]
        # align to 4
        for j in range(0, len(chunk)-3, 4):
            v = struct.unpack('<I', chunk[j:j+4])[0]
            if 0x401000 <= v < 0x4d0000:
                print(f"    +{j-32+ (off-BASE-lo) and 0:}` -> {BASE+lo+j:#010x}: {v:#010x}")
