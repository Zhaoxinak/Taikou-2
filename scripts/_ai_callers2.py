# -*- coding: utf-8 -*-
"""Trace direct callers (E8) of the AI turn-loop + its sub-deciders."""
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

IMG = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000

wanted = {
    0x4a70b0: "ai_turn_perprov_4a70b0",
    0x4a8250: "ai_dec_A_4a8250",
    0x4a8870: "ai_dec_B_4a8870",
    0x4a8e80: "ai_dec_C_4a8e80",
    0x4a97d0: "ai_dec_D_4a97d0",
    0x4a92c0: "ai_dec_E_4a92c0",
    0x4a94e0: "ai_dec_F_4a94e0",
    0x4a0d10: "ai_active_guard_4a0d10",
    0x4a84e0: "ai_diplo_dec_4a84e0",
}

with open(IMG, 'rb') as f:
    data = f.read()
N = len(data)

func_entries = set()
hits = {t: [] for t in wanted}
i = 0
while i < N - 5:
    if data[i] == 0xE8:
        imm = int.from_bytes(data[i+1:i+5], 'little', signed=True)
        tgt = (BASE + i + 5 + imm) & 0xffffffff
        func_entries.add(tgt)
        if tgt in wanted:
            hits[tgt].append(BASE + i)
    i += 1

sorted_fns = sorted(func_entries)
def containing_fn(caller):
    lo, hi = 0, len(sorted_fns)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_fns[mid] <= caller:
            lo = mid + 1
        else:
            hi = mid
    return sorted_fns[lo - 1] if lo > 0 else None

out = []
for t, name in wanted.items():
    cs = sorted(hits[t])
    out.append(f"=== callers of {name} ({hex(t)}) : {len(cs)} ===")
    for c in cs:
        fn = containing_fn(c)
        out.append(f"  0x{c:x}  (in fn 0x{fn:x})")
txt = "\n".join(out)
od = _ROOT + '/scripts/_ai_callers2.txt'
with open(od, 'w') as f:
    f.write(txt)
print(txt)
print("\n[written]", od)
