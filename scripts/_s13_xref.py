#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S13 (0x5185b6) xref scanner v2 — recovers the real instruction containing
each 4-byte immediate by trying candidate start offsets (x86 max len 15)."""
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

import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BIN = _ROOT + '/scripts/_unpacked_mem.bin'
data = open(BIN, 'rb').read()
BASE = 0x400000
MEM_BASE = 0x5185b6
MEM_END  = MEM_BASE + 2280

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

needles = {}
for va in range(MEM_BASE - 4, MEM_END + 4):
    needles[struct.pack('<I', va & 0xffffffff)] = va

hits = {}
for va_bytes, target in needles.items():
    start = 0
    while True:
        pos = data.find(va_bytes, start)
        if pos < 0:
            break
        # try candidate instruction starts around pos (immediate is usually near end)
        found = None
        for s in range(pos - 6, pos + 1):
            if s < 0:
                continue
            try:
                insn = next(md.disasm(data[s:s+15], BASE + s))
            except Exception:
                continue
            ib = data[s:s+insn.size]
            rel = pos - s
            if rel >= 0 and rel + 4 <= len(ib) and ib[rel:rel+4] == va_bytes:
                found = (BASE + s, insn.mnemonic, insn.op_str, insn.size)
                break
        if found:
            hits.setdefault(target, []).append(found)
        start = pos + 1

print('=== immediate xrefs to S13 region [0x%X .. 0x%X) ===' % (MEM_BASE-4, MEM_END+4))
total = 0
for target in sorted(hits):
    lst = hits[target]
    total += len(lst)
    print('\n--- target immediate 0x%X : %d refs ---' % (target, len(lst)))
    for addr, mnem, ops, sz in sorted(lst):
        print('  0x%X: %-8s %s' % (addr, mnem, ops))
print('\nTOTAL refs (all targets):', total)
