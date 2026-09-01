# -*- coding: utf-8 -*-
"""Extract (arg1,arg2) passed to SECT_A accessors at each call site.

cdecl 2-arg: caller pushes arg2 (class) then arg1 (attr) then `call`.
We scan backwards from the call collecting small immediates (0..0xff) that
look like attr(0..19)/class(0..8) candidates, plus register loads from imm.
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

import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
TEXT_START, TEXT_END = 0x401000, 0x4d0000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

DEF = {0x439050: 'getLo', 0x4390c0: 'getHi', 0x439080: 'setLo'}

def all_calls():
    out = []
    i = 0
    while True:
        i = MEM.find(b'\xe8', i, TEXT_END - BASE)
        if i < 0:
            break
        rel = struct.unpack_from('<i', MEM, i + 1)[0]
        t = (i + BASE) + 5 + rel
        if TEXT_START <= t < TEXT_END:
            out.append((i + BASE, t))
        i += 1
    return out

CALLS = all_calls()

def dis_backward(va, n=24):
    start = max(TEXT_START, va - n * 8)
    chunk = MEM[start - BASE: va + 2 - BASE]
    insts = []
    for ins in md.disasm(chunk, start):
        if ins.address > va:
            break
        insts.append(ins)
    return insts

def imm_of(ins):
    # returns immediate operand value if any (push imm / mov reg, imm / cmp)
    if ins.mnemonic == 'push' and ins.op_str.startswith('0x'):
        return int(ins.op_str, 16)
    if ins.mnemonic in ('mov', 'cmp') and ins.op_str.startswith('e') and ',' in ins.op_str:
        parts = ins.op_str.split(',')
        if len(parts) == 2 and parts[1].strip().startswith('0x'):
            return int(parts[1].strip(), 16)
    return None

def regs_written(ins):
    if ins.mnemonic in ('mov', 'lea', 'xor', 'add', 'sub') and ins.op_str.startswith('e'):
        return ins.op_str.split(',')[0].strip()
    if ins.mnemonic == 'push' and ins.op_str.startswith('e'):
        return ins.op_str.strip()
    return None

def analyze():
    for t, nm in DEF.items():
        sites = [s for s, tt in CALLS if tt == t]
        print(f'\n##### {nm} ({t:#x})  callers={len(sites)} #####')
        for s in sites:
            insts = dis_backward(s, n=26)
            # collect candidates: small immediates pushed, or mov reg,imm just before push reg
            small = []  # (value, kind)
            pushed_regs = []
            for ins in insts:
                im = imm_of(ins)
                if im is not None and 0 <= im <= 0xff:
                    small.append((im, ins.mnemonic + ' ' + ins.op_str))
                if ins.mnemonic == 'push' and ins.op_str.startswith('e'):
                    pushed_regs.append(ins.op_str.strip())
            # Determine args: last two pushes
            args = []
            for ins in insts:
                if ins.mnemonic == 'push':
                    op = ins.op_str.strip()
                    if op.startswith('0x'):
                        args.append(('imm', int(op, 16)))
                    elif op.startswith('e'):
                        # trace last assignment to this reg
                        val = None
                        for j in range(len(insts) - 1, -1, -1):
                            if insts[j] is ins:
                                break
                            rw = regs_written(insts[j])
                            if rw == op:
                                im = imm_of(insts[j])
                                if im is not None and 0 <= im <= 0xff:
                                    val = im
                                break
                        args.append(('reg', op, val))
            host = None
            print(f'  call @{s:#08x}: pushes(last2)={[a for a in args[-2:]]}  smallImm={[x[0] for x in small[-4:]]}')

if __name__ == '__main__':
    analyze()
