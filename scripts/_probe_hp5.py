#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 5: anchor the duel control flow to find HP init.
1) find e8-rel32 xrefs to key fns: 0x47b5c0(menu), 0x4682f0(main-cb), 0x468250(special-cb), 0x46ade0(attack-dispatch), 0x466340(step3)
2) disassemble each caller window + the duel main candidate.
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

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def va_off(va): return va - BASE

def xref_e8(target_va):
    """Return list of caller VA that do 'call target_va' (e8 rel32)."""
    tg = va_off(target_va)
    pat = bytes([0xe8])
    out = []
    pos = 0
    while True:
        i = MEM.find(pat, pos)
        if i < 0: break
        pos = i + 1
        if i+5 > len(MEM): continue
        rel = int.from_bytes(MEM[i+1:i+5], "little", signed=True)
        dest = (i + 5) + rel
        if dest == tg:
            out.append(BASE + i)
    return out

def disasm_range(va_start, va_end):
    s = va_off(va_start)
    e = va_off(va_end)
    return "\n".join(f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}"
                     for ins in md.disasm(MEM[s:e], va_start))

targets = {
    0x47b5c0: "menu_fn",
    0x4682f0: "main_menu_cb",
    0x468250: "special_menu_cb",
    0x46ade0: "attack_dispatch",
    0x466340: "step3_apply",
    0x469cb0: "谁来出战/换人?",
}
out = []
for t, name in targets.items():
    xs = xref_e8(t)
    out.append(f"\n===== xref to {name} (0x{t:08x}) : {len(xs)} callers =====")
    for x in xs[:12]:
        out.append(f"  caller @ 0x{x:08x}")

# Disassemble candidate main-loop / setup regions
regions = {
    "step3_apply 0x466340": (0x466340, 0x4663c0),
    "attack_dispatch 0x46ade0": (0x46ade0, 0x46af20),
    "duel attacker-flow 0x469d00": (0x469d00, 0x469e10),
    "duel setup? 0x4669a0..0x466a40": (0x4669a0, 0x466a40),
}
for name, (a, b) in regions.items():
    out.append(f"\n----- disasm {name} -----")
    out.append(disasm_range(a, b))

open(_ROOT + '/scripts/_hp5.txt', "w", encoding="utf-8").write("\n".join(out))
print("WROTE _hp5.txt")
