# -*- coding: utf-8 -*-
"""_dis_ctx.py — 反汇编指定地址前后若干字节（带中心标记）。
用法: python scripts/_dis_ctx.py <addr> <pre> <post>
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

import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE

def main():
    target = int(sys.argv[1], 16)
    pre = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x40
    post = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x40
    start = target - pre
    if start < BASE: start = BASE
    for ins in md.disasm(MEM[off(start):off(target)+post], start):
        if ins.address > target + post: break
        mk = '  <<<' if ins.address == target else ''
        print(f"  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}{mk}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
