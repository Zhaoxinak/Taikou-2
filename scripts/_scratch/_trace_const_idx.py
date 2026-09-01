# -*- coding: utf-8 -*-
"""For each getLo(0x439050)/getHi(0x4390c0) call site, walk backward and track
the value of EAX (arg1=col=attr 0..19) and ECX (arg2=row=class 0..8).
Report whether the index is a CONSTANT (directly nameable attribute/class) or
caller-derived (register/arg).
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
TEXT0, TEXT1 = 0x401000, 0x4d0000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

TARGETS = {0x439050: 'getLo', 0x4390c0: 'getHi'}

def all_calls():
    out = []
    i = 0
    while True:
        i = MEM.find(b'\xe8', i, TEXT1 - BASE)
        if i < 0: break
        rel = struct.unpack_from('<i', MEM, i + 1)[0]
        t = (i + BASE) + 5 + rel
        if TEXT0 <= t < TEXT1:
            out.append((i + BASE, t))
        i += 1
    return out

CALLS = all_calls()

def track(va, depth=70):
    """Backward-slice EAX (col) and ECX (row) from just before the call."""
    start = max(TEXT0, va - depth * 8)
    chunk = MEM[start - BASE: va + 1 - BASE]
    insts = []
    for ins in md.disasm(chunk, start):
        if ins.address > va: break
        insts.append(ins)
    # state for eax/ecx: None=unknown, int=value, ('arg',k)=from [esp+k], ('reg',r)=copy
    st = {'eax': None, 'ecx': None, 'ax': None, 'cx': None}
    def setreg(r, v):
        st[r] = v
    def resolve(op):
        # operand is immediate?
        try:
            if op.type == X86_OP_IMM:
                return op.imm & 0xffffffff
        except Exception:
            return None
        if op.type == X86_OP_REG:
            return ('reg', op.reg)
        return None
    # We only track simple moves/add into eax/ecx from immediates or args.
    for ins in reversed(insts):
        m = ins.mnemonic
        if m == 'ret' or m.startswith('j') or m == 'call':
            break
        if len(ins.operands) == 2 and m == 'mov':
            dst = ins.operands[0]; src = ins.operands[1]
            dname = md.reg_name(dst.reg) if dst.type == X86_OP_REG else None
            if dname in ('eax', 'ecx'):
                if src.type == X86_OP_IMM:
                    val = src.imm & 0xff
                    st[dname] = val if 0 <= val <= 0xff else ('imm', src.imm)
                elif src.type == X86_OP_REG and md.reg_name(src.reg) in ('eax', 'ecx', 'al', 'cl'):
                    st[dname] = st.get(md.reg_name(src.reg), None)
                elif src.type == X86_OP_MEM and src.mem.base == X86_REG_ESP:
                    st[dname] = ('arg', src.mem.disp)
                else:
                    st[dname] = None
    return st['eax'], st['ecx']

def fmt(v):
    if v is None: return '?'
    if isinstance(v, int): return str(v)
    if isinstance(v, tuple): return v[0]+':'+str(v[1]) if v[0]=='arg' else str(v)
    return str(v)

if __name__ == '__main__':
    for tva, nm in TARGETS.items():
        sites = [s for s, t in CALLS if t == tva]
        print('\n##### %s (%s) : %d call sites #####' % (nm, hex(tva), len(sites)))
        const = 0
        for s in sites:
            eax, ecx = track(s)
            tag = ''
            if isinstance(eax, int) and isinstance(ecx, int):
                tag = '  << CONST col=%d row=%d' % (eax, ecx); const += 1
            elif isinstance(eax, int) or isinstance(ecx, int):
                tag = '  << semi col=%s row=%s' % (fmt(eax), fmt(ecx))
            print('  @%08x  col(EAX)=%s row(ECX)=%s%s' % (s, fmt(eax), fmt(ecx), tag))
        print('  -> constant-index sites: %d' % const)
