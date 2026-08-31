# -*- coding: utf-8 -*-
"""
Climb the call tree: for a set of candidate MIDDLE-LAYER functions, find their
direct callers (E8 rel32 byte-scan) and attribute to containing function.
Goal: locate the AI turn-decision loop that initiates diplomacy.
"""
import os, sys

IMG = r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000

# candidate middle-layer / dispatch functions to trace
wanted = {
    0x4a84e0: "fn_4a84e0 (8 diplo ops)",
    0x4e8220: "fn_4e8220 (4 diplo ops)",
    0x4a7af0: "fn_4a7af0 (2 diplo ops)",
    0x4b9250: "settlement_main_4b9250",
    0x4c5699: "work_dispatch_4c5699",
    0x4c41e0: "player_pressure_4c41e0",
    0x4c4320: "player_friendly_4c4320",
    0x416a60: "rise_alliance_event_416a60",
    0x4c2c50: "setup_daimyo_4c2c50",
    0x4c75f0: "ruin_worsen_4c75f0",
    0x4b5b60: "friendly_success_fn_4b5b60",
    0x4b5fa0: "pressure_submit_fn_4b5fa0",
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
od = r"F:/Games/Taikou 2/scripts/_ai_dip_tree.txt"
with open(od, 'w') as f:
    f.write(txt)
print(txt)
print("\n[written]", od)
