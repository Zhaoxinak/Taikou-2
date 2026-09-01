# -*- coding: utf-8 -*-
"""Refined event-condition evaluator enumeration.

Strategy (fixes the noise in _evt_enum.py):
  * Re-syncing linear disassembly per candidate function.
  * Track the ctx BASE register: result of `call 0x49f6b0` lands in EAX, then
    is copied into a base reg (esi/edi/ebx...). That reg is ctxreg.
  * opcode_reg = the 16-bit reg loaded from `word ptr [ctxreg]`  (i.e. [ctx+0]).
  * Only `cmp <opcode_reg>, imm` (or `cmp word ptr [ctxreg], imm`) counts as a
    SERVED opcode. This excludes province-count bounds checks (cmp cl,0x31)
    and unrelated immediates, which use different registers.
  * Also record: getters called (esp. 0x44e280 current-province), whether it
    reads [ctx+8] (arg) and compares something to it, and the relation.
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

import io, sys, struct, json
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

# ---- function starts (all call targets, byte-level, whole image) ----
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

# ---- re-syncing linear disasm from va, until next_fn (or max_bytes) ----
def disasm_fn(va, next_va, max_bytes=0x800):
    end = min(next_va, va + max_bytes) if next_va else va + max_bytes
    cur = va
    out = []
    while cur < end:
        chunk = MEM[off(cur):off(end)]
        got = list(md.disasm(chunk, cur))
        if not got:
            cur += 1
            continue
        for ins in got:
            if ins.address >= end:
                break
            out.append(ins)
        # advance past the disassembled block
        last = out[-1]
        nxt = last.address + last.size
        if nxt <= cur:
            cur += 1
        else:
            cur = nxt
    return out

def r16_of(reg_id):
    # map a 32-bit reg id to its 16-bit subreg name if relevant
    name = md.reg_name(reg_id)
    return name

def analyze(fn):
    nxt = None
    for t in fn_list:
        if t > fn:
            nxt = t; break
    insns = disasm_fn(fn, nxt)
    info = {
        'fn': fn, 'n_ins': len(insns),
        'served_opcodes': set(),
        'ctx_calls': 0, 'fire_calls': 0,
        'getters': set(),
        'reads_arg8': False,
        'reads_opcode0': False,
        'arg_compares': 0,
        'cmp_kinds': set(),
    }
    ctxreg_id = None
    opcode_reg_id = None
    pending_ctx = False
    last_was_call_ctx = False
    for ins in insns:
        m = ins.mnemonic
        ops = ins.operands
        # detect call 0x49f6b0 (ctx getter)
        if m == 'call' and ops and ops[0].type == CS_OP_IMM:
            tgt = ops[0].imm & 0xffffffff
            if tgt == CALL_CTX:
                pending_ctx = True
                last_was_call_ctx = True
                info['ctx_calls'] += 1
            elif tgt == CALL_FIRE:
                info['fire_calls'] += 1
            else:
                info['getters'].add(tgt)
            continue
        # track ctxreg: mov <reg32>, eax  right after ctx call
        if pending_ctx and m == 'mov' and len(ops) == 2 and ops[0].type == CS_OP_REG and ops[1].type == CS_OP_REG and md.reg_name(ops[1].reg) == 'eax':
            ctxreg_id = ops[0].reg
            pending_ctx = False
        last_was_call_ctx = False
        # opcode read: mov <r16>, word ptr [ctxreg]  (disp 0)
        if ctxreg_id is not None and m == 'mov' and len(ops) == 2:
            o0, o1 = ops[0], ops[1]
            if o0.type == CS_OP_REG and o1.type == CS_OP_MEM and o1.mem.base == ctxreg_id and o1.mem.disp == 0 and o1.mem.index == 0:
                # 16-bit reg?
                nm = md.reg_name(o0.reg)
                if nm in ('ax','cx','dx','bx','si','di','bp','sp'):
                    opcode_reg_id = o0.reg
                    info['reads_opcode0'] = True
            # arg read: mov <r>, word ptr [ctxreg+8]
            if o1.type == CS_OP_MEM and o1.mem.base == ctxreg_id and o1.mem.disp == 8 and o1.mem.index == 0:
                info['reads_arg8'] = True
        # direct mem opcode compare: cmp word ptr [ctxreg], imm
        if ctxreg_id is not None and m == 'cmp' and len(ops) == 2:
            o0, o1 = ops[0], ops[1]
            if o0.type == CS_OP_MEM and o0.mem.base == ctxreg_id and o0.mem.disp == 0 and o0.mem.index == 0 and o1.type == CS_OP_IMM:
                v = o1.imm & 0xffff
                if 1 <= v <= 0x3f:
                    info['served_opcodes'].add(v)
            # cmp <opcode_reg>, imm
            if opcode_reg_id is not None and o0.type == CS_OP_REG and o0.reg == opcode_reg_id and o1.type == CS_OP_IMM:
                v = o1.imm & 0xffff
                if 1 <= v <= 0x3f:
                    info['served_opcodes'].add(v)
                info['cmp_kinds'].add('op==%d' % v)
            # arg compare: cmp <r>, word ptr [ctxreg+8]
            if o1.type == CS_OP_MEM and o1.mem.base == ctxreg_id and o1.mem.disp == 8 and o1.mem.index == 0:
                info['arg_compares'] += 1
                info['cmp_kinds'].add(m)
    return info

rows = []
for fn in cands:
    info = analyze(fn)
    rows.append(info)

# sort by served opcode count desc then fn
rows.sort(key=lambda r: (-len(r['served_opcodes']), r['fn']))
print(f"{'handler':12s} {'#op':3s} {'opcodes':18s} {'ctx':3s} {'fire':4s} {'arg8':5s} {'getters'}")
for r in rows:
    g = ','.join('%x' % (t & 0xffffff) for t in sorted(r['getters']))
    print(f"{r['fn']:#010x}   {len(r['served_opcodes']):<3d} {str(sorted(r['served_opcodes'])):18s} {r['ctx_calls']:<3d} {r['fire_calls']:<4d} {str(r['reads_arg8']):5s} {g}")

print("\n=== per-function detail (getters + cmp kinds) ===")
for r in rows:
    if not r['served_opcodes']:
        continue
    g = ','.join('%x' % (t & 0xffffff) for t in sorted(r['getters']))
    print(f"{r['fn']:#010x} opcodes={sorted(r['served_opcodes'])} getters=[{g}] arg8={r['reads_arg8']} argcmp={r['arg_compares']} kinds={sorted(r['cmp_kinds'])}")
