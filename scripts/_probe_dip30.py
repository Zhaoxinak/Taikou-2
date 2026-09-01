# -*- coding: utf-8 -*-
"""dump 外交成败判定函数 0x47bed0(友好) 与 0x47b5f0(高压), 找 RNG(0x4ebd30) 比较."""
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

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
def rva(p): return p - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dump(a, b, label):
    print(f"\n### {label} (0x{a:x}-0x{b:x})")
    for ins in md.disasm(mem[rva(a): rva(b)], a):
        mark = ""
        if ins.mnemonic == "call":
            mark = "  <CALL>"
            if ins.op_str == "0x4ebd30":
                mark += "  <<< RNG(LCG)"
        print(f"0x{ins.address:05x}: {ins.mnemonic:9} {ins.op_str}{mark}")

dump(0x47bed0, 0x47c040, "0x47bed0 友好外交成败判定")
dump(0x47b5f0, 0x47b8a0, "0x47b5f0 高压外交成败判定")
