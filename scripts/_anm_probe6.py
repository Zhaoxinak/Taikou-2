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
import sys, struct, collections, re
sys.path.insert(0, _ROOT + '/scripts')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
RUNNER = 0x496BA0


def back_args(callva, nargs, back=0x60):
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


# 收集调用点
sites = []
for ins in disasm_all(md, MEM[0x1000:], 0x401000):
    if ins.mnemonic == 'call' and ins.op_str.startswith('0x'):
        try:
            if int(ins.op_str, 16) == RUNNER:
                sites.append(ins.address)
        except ValueError:
            pass
print('call sites:', len(sites))

lit = collections.Counter()
reg = collections.Counter()
none = []
for s in sites:
    a = back_args(s, 1)
    if not a:
        none.append(s)
    elif isinstance(a[0], int):
        lit[a[0]] += 1
    else:
        reg[str(a[0])] += 1
print('literal args:', sum(lit.values()), ' distinct:', len(lit))
print('  min', min(lit) if lit else None, 'max', max(lit) if lit else None)
print('  top30:', lit.most_common(30))
print('reg args:', reg.most_common())
print('unresolved:', len(none), [hex(x) for x in none[:20]])

# 字面量是否都 < 520
big = {k: v for k, v in lit.items() if k >= 520}
print('args >= 520:', big)
