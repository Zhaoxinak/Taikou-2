# -*- coding: utf-8 -*-
"""Locate every reference to the diplomacy dispatch tables 0x525e30 / 0x525e50.

Byte-level scan for the little-endian immediate/displacement patterns in the
whole 2MB flat image, then disassemble the enclosing instruction to tell
READ (mov reg,[disp32]) from WRITE (mov [disp32],reg) and find the FILLER
(the code that fills these tables at runtime).
"""
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
def off(va): return va - BASE

TARGETS = {0x525e30: 'DISPATCH_BEHAVIOR', 0x525e50: 'DISPATCH_SUBHANDLE'}

def find_pattern_bytes(va):
    """find raw 4-byte LE occurrences of va in the image"""
    pat = struct.pack('<I', va)
    out = []
    i = 0
    n = len(MEM)
    while True:
        i = MEM.find(pat, i)
        if i < 0:
            break
        out.append(BASE + i)
        i += 1
    return out

def disasm_at(va, window=24):
    """disassemble a small window and return instruction containing/likely at va"""
    best = None
    start = va - window
    code = MEM[off(start):off(va) + window]
    for ins in md.disasm(code, start):
        if ins.address <= va < ins.address + ins.size:
            return ins
        if ins.address >= va:
            if best is None:
                best = ins
            break
    return best

READ_MNEM = {'mov', 'movzx', 'movsx', 'lea', 'push', 'cmp', 'add', 'sub', 'or', 'and', 'test', 'inc'}
WRITE_MNEM = {'mov', 'movzx', 'add', 'sub', 'or', 'and', 'xor', 'inc', 'dec'}

def classify(ins, va):
    """return 'W' if the target is a memory DESTINATION (write), else 'R'"""
    if ins is None:
        return '?'
    for op in ins.operands:
        if op.type == CS_OP_MEM:
            abs_va = None
            if op.mem.base == 0 and op.mem.index == 0:
                abs_va = op.mem.disp & 0xffffffff
            if abs_va == va:
                # memory operand referencing our target
                # in x86 the LAST operand is usually dest for mov, but check mnemonic
                return 'W' if ins.mnemonic in WRITE_MNEM and ins.operands.index(op) == len(ins.operands) - 1 else 'R'
    return 'R'

for tgt, label in TARGETS.items():
    hits = find_pattern_bytes(tgt)
    print(f"\n=== {label} 0x{tgt:08x} : {len(hits)} raw hits ===")
    for h in hits:
        ins = disasm_at(h)
        rw = classify(ins, tgt)
        if ins:
            print(f"  @{h:#010x}  [{rw}]  {ins.address:08x}  {ins.bytes.hex():18s} {ins.mnemonic} {ins.op_str}")
        else:
            print(f"  @{h:#010x}  [?]  (no decode)")
