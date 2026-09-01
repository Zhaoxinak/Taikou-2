# -*- coding: utf-8 -*-
"""Event-handler evidence dumper (v8).

For a given list of candidate function addresses, print the structural evidence
that distinguishes a TRUE event handler (reads [ctx+0]=id, and also touches
other ctx fields / calls getCtx/FIRE) from a false positive (compares a
struct's first field to a constant but nothing else).
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

import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE
CALL_CTX = 0x49f6b0; CALL_FIRE = 0x49b860

def disasm_fn(va, nbytes=0x400):
    end = va + nbytes; cur = va; out = []
    while cur < end:
        chunk = MEM[off(cur):off(end)]
        got = list(md.disasm(chunk, cur))
        if not got: cur += 1; continue
        for ins in got:
            if ins.address >= end: break
            out.append(ins)
        last = out[-1]; nxt = last.address + last.size
        cur = nxt if nxt > cur else cur + 1
    return out

def evidence(fn):
    insns = disasm_fn(fn)
    ctx = any(ins.mnemonic=='call' and ins.operands and ins.operands[0].type==CS_OP_IMM
              and (ins.operands[0].imm&0xffffffff)==CALL_CTX for ins in insns)
    fire = any(ins.mnemonic=='call' and ins.operands and ins.operands[0].type==CS_OP_IMM
               and (ins.operands[0].imm&0xffffffff)==CALL_FIRE for ins in insns)
    # find assertion base regs
    bases = set()
    asserts = []
    for idx, ins in enumerate(insns):
        ops = ins.operands
        if ins.mnemonic=='cmp' and len(ops)==2:
            o0,o1=ops[0],ops[1]
            if o0.type==CS_OP_MEM and o0.mem.index==0 and o0.mem.disp==0 and o1.type==CS_OP_IMM:
                b=md.reg_name(o0.mem.base) if o0.mem.base else None
                if b and 0<=(o1.imm&0xffff)<=0x3f:
                    bases.add(b); asserts.append((ins.address, ins.mnemonic+' '+ins.op_str))
        if ins.mnemonic in ('mov','movzx','movsx') and len(ops)==2:
            o1=ops[1]
            if o1.type==CS_OP_MEM and o1.mem.index==0 and o1.mem.disp==0 and ops[0].type==CS_OP_REG:
                b=md.reg_name(o1.mem.base) if o1.mem.base else None
                if b: bases.add(b); asserts.append((ins.address, ins.mnemonic+' '+ins.op_str+'   ; load id'))
    # field reads on assertion bases
    fields = {b:set() for b in bases}
    for ins in insns:
        for o in ins.operands:
            if o.type==CS_OP_MEM and o.mem.index==0:
                b=md.reg_name(o.mem.base) if o.mem.base else None
                if b in fields:
                    fields[b].add(o.mem.disp)
    return ctx, fire, sorted(bases), asserts, fields, len(insns)

import sys
addrs = [int(a,16) for a in sys.argv[1:]]
for fn in addrs:
    ctx, fire, bases, asserts, fields, n = evidence(fn)
    print(f"\n=== {fn:#010x}  (insns={n}) ctx={ctx} fire={fire} ===")
    print("  assertion sites:")
    for a,s in asserts[:12]:
        print(f"    {a:#010x}: {s}")
    for b in bases:
        flds=sorted(fields[b])
        print(f"  base {b}: field offsets read = {flds}")
