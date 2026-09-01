# -*- coding: utf-8 -*-
"""
Trace direct callers of the diplomacy core functions via pure byte-scan
(E8 rel32). Goal: locate the AI turn-decision function that initiates
diplomacy (the only unbroken diplomacy item, 续89/96).

Targets:
  0x4b5bcb  friendly success (set_diplo + set_lord=同盟)
  0x4b6095  pressure submit (set_diplo + set_lord=支配)
  0x49fe40  set_diplomacy   (bit0-2 = 外交関係 8级)
  0x49ff10  set_master_vassal(bit3-4 = 主从関係 4级)
  0x49fd60  get_diplomacy
  0x49fe70  get_master_vassal

We also attribute each caller to its containing function (nearest direct-call
TARGET <= caller) to cluster AI vs player/handler/init/灭亡 callers.
"""
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
    0x4b5bcb: "friendly_success",
    0x4b6095: "pressure_submit",
    0x49fe40: "set_diplomacy",
    0x49ff10: "set_master_vassal",
    0x49fd60: "get_diplomacy",
    0x49fe70: "get_master_vassal",
}

with open(IMG, 'rb') as f:
    data = f.read()
N = len(data)

# pass 1: all direct-call targets (function entries) + wanted hits
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
    # largest entry <= caller
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
    out.append(f"=== {name} ({hex(t)}) : {len(cs)} callers ===")
    for c in cs:
        fn = containing_fn(c)
        out.append(f"  0x{c:x}  (in fn 0x{fn:x})")

txt = "\n".join(out)
od = _ROOT + '/scripts/_ai_dip_callers.txt'
with open(od, 'w') as f:
    f.write(txt)
print(txt)
print("\n[written]", od)
