# -*- coding: utf-8 -*-
"""
_probe_dip18.py — 反汇编 0x4b9250（工作完了结算主函数，跳表 0x4b9824 14 项）
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
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

o = 0x4B9250 - BASE
n = 0
for ins in md.disasm(MEM[o:o + 0x5C0], 0x4B9250):
    print(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
    n += 1
    if n >= 200 or ins.mnemonic == "ret":
        break
