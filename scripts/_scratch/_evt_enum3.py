# -*- coding: utf-8 -*-
"""Event-condition evaluator enumeration v3 — liveness-correct.

Fixes v2 (register reuse false positives):
  * opcode_reg is invalidated when it (or its 32-bit parent) is the DESTINATION
    of a fresh load (mov/lea/pop/movzx/movsx). In-place arithmetic (sub/dec/
    inc/add/and/or/xor/cmp/test/shl/shr/sar/neg) keeps it valid (it is still
    the opcode value being compared).
  * candidate opcodes come ONLY from cmp/sub/test/and/or/xor/dec/inc against a
    LIVE opcode register (or direct `cmp word ptr [ctx+0], imm`).
  * tracks arg register (loaded from [ctx+8]) and whether it is compared.
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
CODE_LO, CODE_HI = 0x400000, 0x600000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE

CALL_CTX = 0x49f6b0
CALL_FIRE = 0x49b860

PARENT32 = {'ax':'eax','bx':'ebx','cx':'ecx','dx':'edx','si':'esi','di':'edi','bp':'ebp','sp':'esp'}
# 8-bit subregs -> 32-bit parent (so writing al/ah invalidates ax/eax too)
SUBREG8 = {'al':'eax','ah':'eax','bl':'ebx','bh':'ebx','cl':'ecx','ch':'ecx',
           'dl':'edx','dh':'edx','sil':'esi','dil':'edi','bpl':'ebp','spl':'esp'}
LOAD_MNEM = {'mov','lea','pop','movzx','movsx'}
ARITH_MNEM = {'sub','dec','inc','add','and','or','xor','cmp','test','neg','shl','shr','sal','sar'}

def reg_family(opreg, opreg32):
    fam = set()
    if opreg: fam.add(opreg)
    if opreg32:
        fam.add(opreg32)
        for s8, d32 in SUBREG8.items():
            if d32 == opreg32:
                fam.add(s8)
    return fam

# ---- function starts ----
fn_starts = set()
i = 0; n = len(MEM) - 5
while i < n:
    if MEM[i] == 0xE8:
        rel = struct.unpack('<i', MEM[i+1:i+5])[0]
        tgt = (BASE + i + 5 + rel) & 0xffffffff
        if CODE_LO <= tgt < CODE_HI:
            fn_starts.add(tgt)
    i += 1
fn_list = sorted(fn_starts)
def enclosing_fn(site):
    best = None
    for t in fn_list:
        if t <= site and (best is None or t > best):
            best = t
    return best
def callers(target):
    out = []
    i = 0; n = len(MEM) - 5
    while i < n:
        if MEM[i] == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            tgt = (BASE + i + 5 + rel) & 0xffffffff
            if tgt == target:
                out.append(BASE + i)
        i += 1
    return out
c_ctx_fns = set(enclosing_fn(s) for s in callers(CALL_CTX))
c_fire_fns = set(enclosing_fn(s) for s in callers(CALL_FIRE))
cands = sorted(c_ctx_fns & c_fire_fns)

def disasm_fn(va, next_va, max_bytes=0x800):
    end = min(next_va, va + max_bytes) if next_va else va + max_bytes
    cur = va; out = []
    while cur < end:
        chunk = MEM[off(cur):off(end)]
        got = list(md.disasm(chunk, cur))
        if not got:
            cur += 1; continue
        for ins in got:
            if ins.address >= end: break
            out.append(ins)
        last = out[-1]; nxt = last.address + last.size
        cur = nxt if nxt > cur else cur + 1
    return out

def analyze(fn):
    nxt = None
    for t in fn_list:
        if t > fn:
            nxt = t; break
    insns = disasm_fn(fn, nxt)
    info = {'fn': fn, 'n': len(insns), 'opcodes': set(), 'ctx':0,'fire':0,
            'getters': set(), 'reads_arg8':False, 'cmp_arg':0, 'writes_ctx4':False}
    ctxreg = None; opreg = None; opreg32 = None; valid = False
    opreg_set_addr = None
    fam = set()
    pending_ctx = False
    for ins in insns:
        m = ins.mnemonic; ops = ins.operands
        if m == 'call' and ops and ops[0].type == CS_OP_IMM:
            tgt = ops[0].imm & 0xffffffff
            if tgt == CALL_CTX:
                pending_ctx = True; info['ctx'] += 1
            elif tgt == CALL_FIRE:
                info['fire'] += 1
            else:
                info['getters'].add(tgt)
            continue
        # ctxreg capture
        if pending_ctx and m == 'mov' and len(ops)==2 and ops[0].type==CS_OP_REG and ops[1].type==CS_OP_REG and md.reg_name(ops[1].reg)=='eax':
            ctxreg = ops[0].reg; pending_ctx = False
        # opcode read
        if ctxreg is not None and m=='mov' and len(ops)==2:
            o0,o1 = ops[0],ops[1]
            if o0.type==CS_OP_REG and o1.type==CS_OP_MEM and o1.mem.base==ctxreg and o1.mem.index==0 and o1.mem.disp==0:
                nm = md.reg_name(o0.reg)
                if nm in PARENT32:
                    opreg = nm; opreg32 = PARENT32[nm]
                    valid = True; opreg_set_addr = ins.address
                    fam = reg_family(opreg, opreg32)
            if o1.type==CS_OP_MEM and o1.mem.base==ctxreg and o1.mem.index==0 and o1.mem.disp==8:
                info['reads_arg8'] = True
        # direct mem opcode compare: cmp word ptr [ctx+0], imm
        if ctxreg is not None and m=='cmp' and len(ops)==2:
            o0,o1 = ops[0],ops[1]
            if o0.type==CS_OP_MEM and o0.mem.base==ctxreg and o0.mem.index==0 and o0.mem.disp==0 and o1.type==CS_OP_IMM:
                v=o1.imm&0xffff
                if 0<=v<=0x3f: info['opcodes'].add(v)
            # arg compare
            if o1.type==CS_OP_MEM and o1.mem.base==ctxreg and o1.mem.index==0 and o1.mem.disp==8:
                info['cmp_arg'] += 1
        # register-based opcode compare (live opreg, incl. subregs)
        if valid and ops and ops[0].type==CS_OP_REG and md.reg_name(ops[0].reg) in fam:
            if m in ('cmp','sub','test','and','or','xor') and len(ops)>=2 and ops[1].type==CS_OP_IMM:
                v=ops[1].imm&0xffff
                if 0<=v<=0x3f: info['opcodes'].add(v)
            elif m in ('dec','inc'):
                info['opcodes'].add(1)
        # liveness: invalidate opreg on a fresh load into any of its subregs
        # (skip the instruction that *set* opreg, which would cancel itself).
        if opreg is not None and len(ops)>=1 and ops[0].type==CS_OP_REG and md.reg_name(ops[0].reg) in fam:
            if m in LOAD_MNEM and ins.address != opreg_set_addr:
                valid = False
    return info

rows = []
for fn in cands:
    rows.append(analyze(fn))
rows.sort(key=lambda r:(-len(r['opcodes']), r['fn']))
print(f"{'handler':12s} {'#op':3s} {'opcodes':20s} {'ctx':3s} {'fire':4s} {'arg8':5s} {'argcmp':6s} {'getters'}")
for r in rows:
    g=','.join('%x'%(t&0xffffff) for t in sorted(r['getters']))
    print(f"{r['fn']:#010x}   {len(r['opcodes']):<3d} {str(sorted(r['opcodes'])):20s} {r['ctx']:<3d} {r['fire']:<4d} {str(r['reads_arg8']):5s} {r['cmp_arg']:<6d} {g}")
print("\n=== detail (opcode-bearing) ===")
for r in rows:
    if not r['opcodes']: continue
    g=','.join('%x'%(t&0xffffff) for t in sorted(r['getters']))
    print(f"{r['fn']:#010x} op={sorted(r['opcodes'])} getters=[{g}] arg8={r['reads_arg8']} argcmp={r['cmp_arg']}")
