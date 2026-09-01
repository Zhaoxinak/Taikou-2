# -*- coding: utf-8 -*-
"""dump 结算主函数 0x4b9250 区域, 找 RNG(0x4ebd30) 比较与成败分支, 高亮消息 push."""
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

import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
def rva(p): return p - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dump(a, b, label):
    print(f"\n### {label}")
    for ins in md.disasm(mem[rva(a): rva(b)], a):
        mark = ""
        if ins.mnemonic == "call":
            mark = "  <CALL>"
            if ins.op_str == "0x4ebd30":
                mark += "  <<< RNG(LCG)"
        elif ins.mnemonic == "push":
            m = re.match(r"^0x([0-9a-f]+)$", ins.op_str)
            if m and int(m.group(1),16) >= 0x800 and int(m.group(1),16) <= 0x1000:
                mark = f"  <MSGX {int(m.group(1),16):#x}?>"
        print(f"0x{ins.address:05x}: {ins.mnemonic:9} {ins.op_str}{mark}")

# 结算主函数应覆盖 0x4b9250 .. 0x4b95xx (含高压成功消息 0x92c)
dump(0x4b9250, 0x4b9400, "0x4b9250 段A")
