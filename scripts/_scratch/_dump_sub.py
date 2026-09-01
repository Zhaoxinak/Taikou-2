#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反汇编指定 sub-loader 的前 N 条 call 与关键指令, 找出其读取机制."""
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
BASE = 0x400000
data = open(_ROOT + '/scripts/_unpacked_mem.bin',"rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dump(addr, n=120):
    chunk = data[addr-BASE:addr-BASE+0x400]
    calls = []
    for i, ins in enumerate(md.disasm(chunk, addr)):
        if i >= n: break
        s = f"{ins.address:#010x}  {ins.mnemonic} {ins.op_str}"
        if ins.mnemonic == "call":
            calls.append(s)
        if i < 60:  # 只打印前 60 条看结构
            print(s)
    print("\n--- 全部 call (前 %d 条) ---" % n)
    for s in calls:
        print(s)

if __name__ == "__main__":
    import sys
    a = int(sys.argv[1],16) if len(sys.argv)>1 else 0x47dae0
    n = int(sys.argv[2]) if len(sys.argv)>2 else 120
    dump(a, n)
