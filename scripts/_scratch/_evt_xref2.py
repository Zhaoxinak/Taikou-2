# -*- coding: utf-8 -*-
"""Find jmp rel32 / call rel32 to a target, and detect jump-table dispatchers
(jmp [base + reg*4]) whose table may hold relative offsets."""
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
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def va2off(va): return va - BASE

TARGETS = [int(a,16) for a in sys.argv[1:]] if len(sys.argv)>1 else [0x4e82c0]

# 1) direct jmp/call rel32 to target
found = {t: [] for t in TARGETS}
base_va = 0x400000
code = MEM[va2off(0x400000):va2off(0x600000)]
for ins in md.disasm(code, base_va):
    if ins.mnemonic in ('call','jmp'):
        op = ins.operands[0]
        if op.type == X86_OP_IMM and op.imm in TARGETS:
            found[op.imm].append(ins.address)
for t in TARGETS:
    print(f"=== direct jmp/call to {t:#010x}: {len(found[t])} ===")
    for a in found[t]:
        print(f"  {a:#010x}  {ins_shorthand(a)}")

def ins_shorthand(va):
    return ''

# 2) detect 'jmp [reg*4 + disp32]' (jump table dispatch) anywhere
print("=== jump-table dispatchers (jmp [reg*4 + imm]) ===")
for ins in md.disasm(code, base_va):
    if ins.mnemonic == 'jmp' and len(ins.operands)==1:
        op = ins.operands[0]
        if op.type == X86_OP_MEM and op.mem.scale == 4 and op.mem.disp:
            tbl = op.mem.disp & 0xffffffff
            if 0x401000 <= tbl < 0x4d0000:
                print(f"  {ins.address:#010x}: jmp [{ins.op_str}]  table={tbl:#010x}")
