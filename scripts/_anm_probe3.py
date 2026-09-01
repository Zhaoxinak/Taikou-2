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

DISPATCH = 0x496D20
JUMPTBL = 0x496CF4

m = MEM[DISPATCH - BASE:DISPATCH - BASE + 0x5A]
print('dispatch map len', len(m))
jt = [struct.unpack_from('<I', MEM, JUMPTBL - BASE + 4 * i)[0] for i in range(11)]
inv = {}
for op, h in enumerate(m):
    inv.setdefault(h, []).append(op)
for h in sorted(inv):
    ops = inv[h]
    print(f'handler {h:2d} @0x{jt[h]:06x}  opcodes({len(ops)}): {[hex(o) for o in ops]}')
print()
print('opcodes with handler 0 (terminate):', [hex(o) for o in inv.get(0, [])])
