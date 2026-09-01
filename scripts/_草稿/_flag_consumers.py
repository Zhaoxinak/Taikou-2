"""Find consumers of each battle-mode flag via raw 4-byte address literal scan (drift-free)."""
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

import struct
BASE = 0x400000
BIN = _ROOT + '/scripts/_unpacked_mem.bin'
data = open(BIN, "rb").read()

flags = {
    0x511bf8: "mode_m1",
    0x51352c: "mode_m2",
    0x513540: "parity",
    0x513548: "battle_type",
    0x513534: "handle_stat",
}

def classify(prev1, prev2):
    if prev1 == 0xA1:
        return "READ (mov reg,[addr])"
    if prev1 == 0xA3:
        return "WRITE (mov [addr],reg)"
    if prev1 in (0x8B, 0x8A):
        return "READ (mov r,[addr])"
    if prev1 in (0x89, 0x88):
        return "WRITE (mov [addr],r)"
    if prev1 == 0x0F and prev2 in (0xB6, 0xB7, 0xBE, 0xBF):
        return "READ (movz/sx r,[addr])"
    if prev1 in (0xC6, 0xC7):
        return "WRITE (mov [addr],imm)"
    if prev1 in (0x80, 0x81, 0x83):
        return "WRITE (alu [addr],imm)"
    if prev1 == 0xFF:
        return "? (ff [addr])"
    if prev1 in (0x68, 0x6A):
        return "PUSH (addr as imm)"
    if prev1 in (0xF6, 0xF7):
        return "? (test [addr])"
    return f"? (op {prev1:#x}/{prev2:#x})"

for addr, name in flags.items():
    lit = struct.pack("<I", addr)
    hits = []
    start = 0
    while True:
        i = data.find(lit, start)
        if i < 0:
            break
        prev1 = data[i-1] if i >= 1 else 0
        prev2 = data[i-2] if i >= 2 else 0
        kind = classify(prev1, prev2)
        hits.append((i + BASE, kind))
        start = i + 1
    reads = [h for h in hits if h[1].startswith("READ") or "PUSH" in h[1]]
    writes = [h for h in hits if h[1].startswith("WRITE")]
    others = [h for h in hits if not (h[1].startswith("READ") or h[1].startswith("WRITE") or "PUSH" in h[1])]
    print(f"\n##### {name} @ {addr:#x}  ({len(hits)} literal refs: {len(reads)}R/{len(writes)}W/{len(others)}?) #####")
    for a, k in (writes + reads)[:30]:
        print(f"  {a:#08x}  {k}")
