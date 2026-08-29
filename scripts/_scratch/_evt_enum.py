# -*- coding: utf-8 -*-
"""Enumerate event-condition handlers: functions that call BOTH 0x49f6b0 (ctx getter)
and 0x49b860 (fire event). For each, extract the opcode(s) it serves via
`cmp word ptr [reg], 0xNN` against the ctx, and the arg/flag field usage.
This reverse-engineers the opcode -> handler map without needing the (runtime) dispatch."""
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
CODE_LO, CODE_HI = 0x400000, 0x600000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va-BASE

CALL_CTX = 0x49f6b0
CALL_FIRE = 0x49b860

# byte-level: find all callers of each
def callers(target):
    out=[]; i=0; n=len(MEM)-5
    while i<n:
        if MEM[i]==0xE8:
            rel=struct.unpack('<i',MEM[i+1:i+5])[0]
            tgt=(BASE+i+5+rel)&0xffffffff
            if tgt==target: out.append(BASE+i)
        i+=1
    return out

# function starts = all call targets (byte-level, whole image, no linear disasm)
fn_starts = set()
i=0; n=len(MEM)-5
while i<n:
    if MEM[i]==0xE8:
        rel=struct.unpack('<i',MEM[i+1:i+5])[0]
        tgt=(BASE+i+5+rel)&0xffffffff
        if CODE_LO <= tgt < CODE_HI:
            fn_starts.add(tgt)
    i+=1
fn_list = sorted(fn_starts)

def enclosing_fn(site):
    best=None
    for t in fn_list:
        if t<=site and (best is None or t>best): best=t
    return best

c_ctx_fns = set(enclosing_fn(s) for s in callers(CALL_CTX))
c_fire_fns = set(enclosing_fn(s) for s in callers(CALL_FIRE))
cands = sorted(c_ctx_fns & c_fire_fns)
print(f"ctx-fns={len(c_ctx_fns)} fire-fns={len(c_fire_fns)} both={len(cands)}")

def disasm_from(va, nbytes=0x400):
    try:
        code = MEM[off(va):off(va)+nbytes]
        return list(md.disasm(code, va))
    except Exception as e:
        return []

import re
def norm(s): return s.replace(' ', '')
results = []
for fn in cands:
    insns = disasm_from(fn)
    if not insns: 
        continue
    opcodes = set()
    reads_arg8 = False
    reads_flags_c = False
    reads_opcode0 = False
    for ins in insns:
        os_ = norm(ins.op_str)
        # opcode id check: 'cmp word ptr [reg], 0xNN' or 'cmp reg16, 0xNN', NN in 1..0x3f
        if ins.mnemonic=='cmp':
            m = re.search(r'(0x[0-9a-fA-F]+)\s*$', ins.op_str)
            if m:
                val=int(m.group(1),16)
                if 1<=val<=0x3f:
                    opcodes.add(val)
        # field usage (normalized)
        if 'ptr[' in os_ and '+8]' in os_: reads_arg8=True
        if 'ptr[' in os_ and '+0xc]' in os_ or '+12]' in os_: reads_flags_c=True
        # opcode read at [ctx+0]
        if 'ptr[' in os_ and '+0]' in os_ and ins.mnemonic in ('mov','cmp'): reads_opcode0=True
    results.append((fn, sorted(opcodes), reads_arg8, reads_flags_c, reads_opcode0, len(insns)))

print(f"\n{'handler':12s} {'opcodes':22s} {'arg8':5s} {'flgC':5s} {'op0':4s} {'ins'}")
for fn,ops,a8,fc,o0,n in results:
    print(f"{fn:#010x}   {str(ops):22s} {str(a8):5s} {str(fc):5s} {str(o0):4s} {n}")
