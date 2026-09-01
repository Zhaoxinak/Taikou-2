# -*- coding: utf-8 -*-
"""_writers.py — 找所有对给定绝对地址的「写」指令 (mov/add/sub/... [addr], ...)
用法: python scripts/_writers.py 0x514995"""
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

import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
WRITES = {'mov','add','sub','or','and','xor','inc','dec','shl','shr','imul','movzx','movsx'}

def main():
    targets = [int(x, 16) for x in sys.argv[1:]]
    tset = set(targets)
    i, n = 0, len(MEM) - 16
    while i < n:
        ins = next(md.disasm(MEM[i:i+16], BASE + i), None)
        if ins is None:
            i += 1; continue
        for o in ins.operands:
            if (o.type == CS_OP_MEM and o.mem.base == 0 and o.mem.index == 0
                    and (o.mem.disp & 0xffffffff) in tset):
                # 写操作: 第一个操作数是内存
                if ins.mnemonic in WRITES and ins.operands[0].type == CS_OP_MEM:
                    print(f"  {ins.address:#x}: {ins.mnemonic} {ins.op_str}   ; size={ins.op_str.split()[0]}")
        i += ins.size
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
