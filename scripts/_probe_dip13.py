# -*- coding: utf-8 -*-
"""
_probe_dip13.py — 反汇编外交结算函数（使者帰還）
  入口候选: 0x4b94xx (msg 0x92b/0x92c/0x92d), 0x4b9dd9 (msg 0x94d)
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

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def func_start(va):
    o = va - BASE
    lim = max(0, o - 0x1200)
    i = o
    while i > lim:
        b = MEM[i]
        if b == 0xC3:
            return BASE + i + 1
        if b == 0xC2 and i + 2 < SZ:
            return BASE + i + 3
        i -= 1
    return BASE + lim


def dis(va, maxins=500):
    o = va - BASE
    out = []
    for ins in md.disasm(MEM[o:o + maxins * 8], va):
        out.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        if len(out) >= maxins:
            break
        if ins.mnemonic == "ret":
            break
    return "\n".join(out)


fs = func_start(0x4B94DC)
print(f"  结算函数入口 = {fs:#x}")
print("=" * 78)
print(dis(fs, 520))
