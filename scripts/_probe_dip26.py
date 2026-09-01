# -*- coding: utf-8 -*-
"""dump 几个 setter 调用方站点原始汇编, 确认调用约定与 lv 走向."""
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

SITES = [0x40e7de, 0x4c2e73, 0x4c2e91, 0x4c78b8, 0x4c78ce,
         0x4a7cb5, 0xabce9, 0x416ab4, 0x416ac0, 0x4b60ef, 0x4b6280]

for s in SITES:
    print(f"\n{'='*60}\n0x{s:x}: 前 0x50 字节 (call 在末端标记)\n{'='*60}")
    code = mem[rva(s)-0x50: rva(s)+2]
    for ins in md.disasm(code, s-0x50):
        mark = "  <<< SET" if ins.address == s else ""
        print(f"0x{ins.address:05x}: {ins.mnemonic:9} {ins.op_str}{mark}")
