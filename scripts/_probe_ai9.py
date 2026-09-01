#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 15: find the dispatch table listing the 4 action-handler fns
0x469480, 0x4694a0, 0x4694e0, 0x469530; and find its caller (the AI decision)."""
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

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

targets = {0x469480, 0x4694a0, 0x4694e0, 0x469530}
# build little-endian dword of each (but search by raw bytes)
import struct
target_bytes = {t: struct.pack("<I", t) for t in targets}

hits = {}
for t, tb in target_bytes.items():
    hits[t] = []
    pos = 0
    while True:
        i = MEM.find(tb, pos)
        if i < 0:
            break
        hits[t].append(BASE + i)
        pos = i + 1

out = []
out.append("=== data references to the 4 handlers (dword in image) ===")
for t in targets:
    out.append(f"  0x{t:08x}: {[hex(x) for x in hits[t]]}")

# For each hit, disassemble ~0x50 bytes before (to find container fn / index source)
out.append("\n=== context around each hit (disasm 0x60 before .. 0x10 after) ===")
seen = set()
for t in targets:
    for h in hits[t]:
        if h in seen:
            continue
        seen.add(h)
        out.append(f"\n--- handler 0x{t:08x} referenced @ 0x{h:08x} ---")
        try:
            for ins in md.disasm(MEM[h-BASE-0x60:h-BASE+0x14], h-0x60):
                out.append(f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}")
        except Exception as e:
            out.append(f"  (err {e})")

open(_ROOT + '/scripts/_ai9.txt',"w",encoding="utf-8").write("\n".join(out))
print("WROTE _ai9.txt")
for t in targets:
    print(f"0x{t:08x}: {hits[t]}")
