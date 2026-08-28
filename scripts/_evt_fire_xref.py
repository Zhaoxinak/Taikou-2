# -*- coding: utf-8 -*-
"""Find all call sites to a set of 'fire event' style functions. Each caller is a
candidate event/opcode handler. Prints caller VA and the surrounding function (nearest
preceding call-target or stack-frame prologue)."""
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

TARGETS = [int(a,16) for a in sys.argv[1:]] if len(sys.argv)>1 else [0x49b860,0x4e84b0,0x4e83e0,0x49f6b0,0x44e280]
CODE_LO, CODE_HI = 0x400000, 0x600000

# build set of all call-target VAs (function starts) for context
call_targets = set()
code = MEM[(CODE_LO-BASE):(CODE_HI-BASE)]
for ins in md.disasm(code, CODE_LO):
    if ins.mnemonic == 'call':
        op = ins.operands[0]
        if op.type == X86_OP_IMM:
            call_targets.add(op.imm)

def find_callers():
    res = {t: [] for t in TARGETS}
    for ins in md.disasm(code, CODE_LO):
        if ins.mnemonic == 'call':
            op = ins.operands[0]
            if op.type == X86_OP_IMM and op.imm in TARGETS:
                res[op.imm].append(ins.address)
    return res

# nearest function start = largest call_target <= addr (within 0x4000)
def nearest_fn(addr):
    best = None
    for t in call_targets:
        if t <= addr and (best is None or t > best):
            best = t
    return best

if __name__ == '__main__':
    res = find_callers()
    for t in TARGETS:
        print(f"=== callers of {t:#010x} ({len(res[t])}) ===")
        for a in sorted(set(res[t])):
            fn = nearest_fn(a)
            print(f"  call@{a:#010x}  (fn~{fn:#010x})")
