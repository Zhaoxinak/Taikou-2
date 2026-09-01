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


def back_args(callva, nargs, back=0x80):
    st = max(BASE + 0x1000, callva - back)
    seq = list(disasm_all(md, MEM[st - BASE:callva - BASE], st))
    anchor = None
    for idx, ins in enumerate(seq):
        if ins.address + ins.size == callva:
            anchor = idx
    if anchor is None:
        return []
    args, prev_end = [], callva
    for k in range(anchor, -1, -1):
        it = seq[k]
        if it.address + it.size != prev_end:
            break
        prev_end = it.address
        if it.mnemonic == 'push':
            o = it.op_str
            try:
                v = int(o, 16) if o.startswith('0x') else int(o)
            except ValueError:
                v = o
            args.append(v)
            if len(args) == nargs:
                break
        elif it.mnemonic in ('ret', 'jmp'):
            break
        elif it.mnemonic == 'add' and it.op_str.startswith('esp'):
            break
    return args


if __name__ == '__main__':
    dis(0x47AD60, 0x47AD80, 'op 0x49 handler')
    dis(0x47ADC0, 0x47ADE0, 'op 0x4F handler')
    print()
    dis(0x4966D0, 0x4967A0, 'op 0x53 handler (sub4966d0)')
    print()
    dis(0x496B50, 0x496B60, 'op 0x57 handler (sub496b50)')
    dis(0x47B600, 0x47B620, 'prolog helper 0x47b600')
