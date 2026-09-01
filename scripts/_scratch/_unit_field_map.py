# -*- coding: utf-8 -*-
"""
Build a field-usage map for the battle unit slot struct (15 x 24B @ 0x513910).

Method: every `call 0x43e4a0` (unitSlot accessor) returns the slot pointer in
EAX.  Disassemble the following instructions until EAX is clobbered, and record
each `[eax + disp]` access with size and direction (read / write).

This nails the real semantics of each field and, in particular, settles whether
byte[+0x10] is the terrain type (as previously assumed) or something else.
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

import sys, io, struct, bisect, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
TEXT_START, TEXT_END = 0x401000, 0x4d0000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

ACCESSORS = {
    0x43e4a0: 'unitSlot(i)',
    0x43e4c0: 'unitSlot2(i)',
}

SIZE = {1: 'b', 2: 'w', 4: 'd'}


def call_sites(target):
    """All `e8 rel32` sites whose destination == target."""
    out = []
    i = 0
    while True:
        i = MEM.find(b'\xe8', i, TEXT_END - BASE)
        if i < 0:
            break
        rel = struct.unpack_from('<i', MEM, i + 1)[0]
        if (i + BASE) + 5 + rel == target:
            out.append(i + BASE)
        i += 1
    return out


def follow(va, limit=14):
    """Disassemble from `va` (a call site) and harvest [eax + disp] accesses."""
    hits = []
    chunk = MEM[va - BASE: va - BASE + 0x60]
    seen_call = False
    for k, ins in enumerate(md.disasm(chunk, va)):
        if k == 0:
            seen_call = True
            continue
        if k > limit:
            break
        # stop when eax is redefined by a new call
        if ins.mnemonic == 'call':
            break
        for oi, op in enumerate(ins.operands):
            if op.type == X86_OP_MEM and op.mem.base == X86_REG_EAX and op.mem.index == 0:
                d = op.mem.disp
                if 0 <= d < 0x40:
                    write = (oi == 0 and ins.mnemonic in (
                        'mov', 'add', 'sub', 'or', 'and', 'xor', 'inc', 'dec', 'movzx'))
                    hits.append((d, op.size, write, ins.address, ins.mnemonic, ins.op_str))
        # eax overwritten by a non-memory op -> pointer lost
        if ins.operands and ins.operands[0].type == X86_OP_REG \
                and ins.operands[0].reg in (X86_REG_EAX, X86_REG_AX, X86_REG_AL) \
                and ins.mnemonic in ('mov', 'lea', 'pop', 'xor', 'movzx', 'movsx') \
                and not (len(ins.operands) > 1 and ins.operands[1].type == X86_OP_MEM
                         and ins.operands[1].mem.base == X86_REG_EAX):
            break
    return hits


if __name__ == '__main__':
    agg = collections.defaultdict(lambda: {'r': [], 'w': []})
    for tgt, nm in ACCESSORS.items():
        cs = call_sites(tgt)
        print(f'{nm} @ {tgt:#x}: {len(cs)} call sites')
        for c in cs:
            for (d, sz, w, ia, mn, ops) in follow(c):
                agg[(d, sz)]['w' if w else 'r'].append((ia, mn, ops))

    print('\n===== unit slot field map (offset, size) =====')
    for (d, sz) in sorted(agg):
        e = agg[(d, sz)]
        print(f'\n  +{d:#04x} {SIZE.get(sz, sz)}  reads={len(e["r"])} writes={len(e["w"])}')
        for tag in ('r', 'w'):
            for (ia, mn, ops) in e[tag][:6]:
                print(f'        [{tag}] {ia:#08x}  {mn:<7s} {ops}')
