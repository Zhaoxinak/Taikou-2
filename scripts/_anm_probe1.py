# -*- coding: utf-8 -*-
# <auto: portable root>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>
import sys
sys.path.insert(0, _ROOT + '/scripts')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)


def dis(lo, hi, label=''):
    print('==== ' + label + f' {hex(lo)}..{hex(hi)}')
    for ins in disasm_all(md, MEM[lo - BASE:hi - BASE], lo):
        t = '   ; call' if ins.mnemonic == 'call' and ins.op_str.startswith('0x') else ''
        print(f"0x{ins.address:06x}  {ins.bytes.hex():<20s} {ins.mnemonic:<8s} {ins.op_str}{t}")


if __name__ == '__main__':
    dis(0x496b60, 0x496c80, 'ANMS consumer?')
