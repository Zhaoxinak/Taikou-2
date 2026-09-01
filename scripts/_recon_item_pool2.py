#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recon 2: disassemble pool identity/value methods to learn indexing."""
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
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
def get_bytes(va, n): return IMG[va - BASE: va - BASE + n]
def disasm(va, n=0x140, label=''):
    print(f"\n=== {label}  0x{va:x} ===")
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
    for ins in md.disasm(get_bytes(va, n), va):
        print(f"  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}")

for va, lbl in [
    (0x49c010, "getTypeName vtable[1]"),
    (0x49c1f0, "getShortName vtable[5]"),
    (0x49c200, "getSecondaryName vtable[6]"),
    (0x49c030, "getPoolIndex vtable[2]"),
    (0x49c070, "getValue vtable[0]"),
    (0x49c250, "getValueAlt vtable[4]"),
]:
    disasm(va, 0x140, lbl)
