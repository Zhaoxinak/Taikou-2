#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 17: find e8 xrefs to the 5 action executors + menu callback 0x469180.
The AI decision function likely calls one of these directly with the chosen action."""
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

targets = {
    0x468af0: "ACT0 普通攻击 executor",
    0x46a680: "ACT1 executor",
    0x468cd0: "ACT2 快刀 executor",
    0x468f00: "ACT3 executor",
    0x4663f0: "ACT4 一击必杀 executor",
    0x469180: "menu callback 0x469180",
    0x4692f0: "player main-menu cb 0x4682f0",
    0x468250: "special submenu cb 0x468250",
}

def find_xrefs(target, lo=0x460000, hi=0x4c0000):
    hits = []
    for ins in md.disasm(MEM[lo-BASE:hi-BASE], lo):
        if ins.mnemonic != "call":
            continue
        try:
            disp = int.from_bytes(MEM[ins.address-BASE+1:ins.address-BASE+5], "little", signed=True)
        except Exception:
            continue
        dest = ins.address + ins.size + disp
        if dest == target:
            hits.append(ins.address)
    return sorted(hits)

out = []
for va, desc in targets.items():
    xr = find_xrefs(va)
    out.append(f"\n--- xrefs to {va:#08x} ({desc}) ---")
    out.append("  " + (", ".join(f"{x:#08x}" for x in xr) if xr else "NONE"))

open(_ROOT + '/scripts/_ai12.txt',"w",encoding="utf-8").write("\n".join(out))
for va, desc in targets.items():
    xr = find_xrefs(va)
    print(f"xrefs {va:#08x} ({desc}): {xr if xr else 'NONE'}")
