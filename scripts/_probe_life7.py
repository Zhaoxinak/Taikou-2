# -*- coding: utf-8 -*-
"""dump 0x49a400..0x49a800 取值器簇, 找寿命/死亡/登场相关 getter。"""
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

MEM = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(MEM, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

o = 0x49A400 - BASE
cur = None
for ins in md.disasm(mem[o:o + 0x420], 0x49A400):
    if ins.mnemonic == "ret":
        print(f"  {ins.address:08x}  {ins.mnemonic:<6} {ins.op_str}")
        print()
        cur = None
        continue
    print(f"  {ins.address:08x}  {ins.mnemonic:<6} {ins.op_str}")
