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
import sys, struct
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


def callers(target, label=''):
    """E8 call-site scan over whole image (disasm_all based)."""
    out = []
    for ins in disasm_all(md, MEM[0x1000:], 0x401000):
        if ins.mnemonic != 'call':
            continue
        o = ins.op_str
        if not o.startswith('0x'):
            continue
        try:
            v = int(o, 16)
        except ValueError:
            continue
        if v == target:
            out.append(ins.address)
    print(f'---- callers of {label}{hex(target)}: {len(out)}')
    for a in out:
        print('   ', hex(a))
    return out


if __name__ == '__main__':
    for t, l in [(0x496BA0, 'ANMSEQ script runner '),
                 (0x496B50, 'sub496b50 '),
                 (0x4966D0, 'sub4966d0 '),
                 (0x47AD60, 'sub47ad60 '),
                 (0x47ADC0, 'sub47adc0 ')]:
        callers(t, l)
        print()
