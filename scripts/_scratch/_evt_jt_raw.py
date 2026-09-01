# -*- coding: utf-8 -*-
"""Raw-byte scan for jump-table dispatchers: FF 24 <SIB=85/8D/95/9D/A5/AD/B5/BD> <disp32>.
For each, read the table at disp32 and resolve entries as:
  abs(entry), rel-to-table (disp32+signed), rel-to-jmp-instr (jmp_va+6+signed).
Report any entry resolving to TARGET, and all tables with >8 valid absolute entries."""
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
TARGET = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x4e82c0
CODE_LO, CODE_HI = 0x400000, 0x600000
SIBS = [0x85,0x8D,0x95,0x9D,0xA5,0xAD,0xB5,0xBD]

def resolve(tbl, jmp_va, entries, target):
    abs_h=[]; relt_h=[]; relj_h=[]
    for i,v in enumerate(entries):
        if CODE_LO <= v < CODE_HI and v == target:
            abs_h.append(i)
        rv = v & 0xffffffff
        if rv & 0x80000000: rv -= 0x100000000
        t1 = (tbl + rv) & 0xffffffff
        t2 = ((jmp_va + 6) + rv) & 0xffffffff
        if CODE_LO <= t1 < CODE_HI and t1 == target:
            relt_h.append((i,rv))
        if CODE_LO <= t2 < CODE_HI and t2 == target:
            relj_h.append((i,rv))
    return abs_h, relt_h, relj_h

found = []
i = 0
n = len(MEM) - 7
while i < n:
    if MEM[i]==0xFF and MEM[i+1]==0x24 and MEM[i+2] in SIBS:
        disp = struct.unpack('<I', MEM[i+3:i+7])[0]
        jmp_va = BASE + i
        found.append((jmp_va, disp & 0xffffffff))
        i += 7
    else:
        i += 1

print(f"found {len(found)} candidate jmp[reg*4+disp] dispatchers")
matches = 0
for jmp_va, tbl in found:
    if not (CODE_LO <= tbl < len(MEM)-1024):
        continue
    entries = struct.unpack('<256I', MEM[tbl-BASE:tbl-BASE+1024])
    abs_h, relt_h, relj_h = resolve(tbl, jmp_va, entries, TARGET)
    valid_abs = sum(1 for v in entries[:64] if CODE_LO <= v < CODE_HI)
    if abs_h or relt_h or relj_h:
        matches += 1
        print(f"\n*** MATCH jmp@{jmp_va:#010x} tbl={tbl:#010x}")
        print(f"    abs={abs_h} rel_tbl={relt_h} rel_jmp={relj_h}")
    if valid_abs > 8:
        # print dispatch tables with many valid entries (likely real)
        print(f"  dispatch jmp@{jmp_va:#010x} tbl={tbl:#010x} valid_abs(64)={valid_abs}")
print(f"\nmatches: {matches}")
