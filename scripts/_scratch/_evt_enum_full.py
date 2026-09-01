# -*- coding: utf-8 -*-
"""Event-handler FULL enumeration v4 (post-续82).

Finds EVERY function that calls both getCtx (0x49f6b0) AND FIRE (0x49b860),
then scans the WHOLE function (not just entry) for self-assertions of event
type id stored at [ctx+0] as a word, comparing against an immediate in
[0..0x3f]. Handles arbitrary register indirection (the ctx base may be
moved through several registers) and the `sub reg,0; je / dec / jne`
multi-branch pattern that v3 missed.

Also detects `cmp byte ptr [ctx+0], imm` (8-bit) which the v3 enum did not.
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

# --- function starts from call rel32 targets ---
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

cands = set(enclosing_fn(s) for s in callers(CALL_CTX)) & \
        set(enclosing_fn(s) for s in callers(CALL_FIRE))

def disasm_fn(va, max_bytes=0x1000):
    cur = va; end = va + max_bytes; out = []
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

def find_ctx_self_assert(fn):
    """Look anywhere in fn for cmp [reg+0], imm or cmp [reg+0x..], imm where
    imm is in [0..0x3f] and the reg was set by 'mov reg, eax' after
    call getCtx OR by lea reg, [..] referring to known ctx anchor (0x516610).
    Returns list of ids found in the function.
    """
    insns = disasm_fn(fn, 0x1000)
    ids = set()
    last_call_ctx_va = None
    # track which register holds ctx at each program point
    ctx_reg = None
    for ins in insns:
        m = ins.mnemonic; ops = ins.operands
        # detect mov ecx/edi/eax/ebx/esi/ebp, eax right after call ctx
        if m == 'call' and ops and ops[0].type == CS_OP_IMM \
           and (ops[0].imm & 0xffffffff) == CALL_CTX:
            last_call_ctx_va = ins.address
            ctx_reg = None  # unknown until next mov
            continue
        if m == 'call' and ops and ops[0].type == CS_OP_IMM \
           and (ops[0].imm & 0xffffffff) == CALL_FIRE:
            continue
        # after call getCtx, the next 'mov reg, eax' captures ctx
        if last_call_ctx_va is not None and ctx_reg is None \
           and m == 'mov' and len(ops) == 2 \
           and ops[0].type == CS_OP_REG and ops[1].type == CS_OP_REG \
           and md.reg_name(ops[1].reg) == 'eax':
            ctx_reg = md.reg_name(ops[0].reg)
            continue
        # also if a lea is done explicitly: lea reg, [0x516610]
        if m == 'mov' and len(ops) == 2 \
           and ops[0].type == CS_OP_REG and ops[1].type == CS_OP_IMM \
           and (ops[1].imm & 0xffffffff) == 0x516610:
            ctx_reg = md.reg_name(ops[0].reg)
            continue
        if ctx_reg is None:
            continue
        # cmp word ptr [ctx_reg + 0], imm OR cmp word ptr [ctx_reg], imm
        if m == 'cmp' and len(ops) == 2 \
           and ops[0].type == CS_OP_MEM and ops[0].mem.index == 0 \
           and md.reg_name(ops[0].mem.base) == ctx_reg \
           and ops[0].mem.disp in (0, 0, ) \
           and ops[1].type == CS_OP_IMM:
            v = ops[1].imm & 0xffff
            if 0 <= v <= 0x3f:
                ids.add(v)
    return sorted(ids)

results = []
for fn in sorted(cands):
    ids = find_ctx_self_assert(fn)
    results.append((fn, ids))

print(f"{'handler':12s} {'self-assert ids'}")
for fn, ids in sorted(results, key=lambda x: (len(x[1]), x[0])):
    print(f"{fn:#010x}   {ids}")
print(f"\nTotal handlers: {len(results)}")
print(f"With at least one id assertion: {sum(1 for _, ids in results if ids)}")
# collect unique ids
all_ids = set()
for _, ids in results:
    all_ids.update(ids)
print(f"Unique ids across handlers: {sorted(all_ids)}")
