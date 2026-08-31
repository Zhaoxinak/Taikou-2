# -*- coding: utf-8 -*-
"""Event-handler self-assertion scanner (post-续82/续83, v5).

Goal: find EVERY function that asserts an "event-type id" read from a context
object's first word ([ctx+0]) by comparing it against a small constant in
[0..0x3f], because the event dispatch relies on each handler self-asserting
its own id (no static dispatch table exists — 续81).

Two assertion idioms are caught (both seen in the 7 known handlers):
  (A) direct :  cmp word ptr [BASE+0], imm   (imm in [0..0x3f])  -> jcond
  (B) via-load: mov R2, [BASE+0]  ;  ...  cmp R2, imm  (imm in [0..0x3f]) -> jcond
where BASE is any register that holds the ctx pointer (thiscall `ecx`, a
`getCtx` result moved into some reg, or `esi`/`edi` used as the object ptr).

We scan ALL functions derived from call rel32 targets (not only getCtx+FIRE
callers), because some handlers receive ctx as a parameter and fire via a
sub-eval, so they never call getCtx/FIRE themselves.

Output: every function with >=1 candidate id, plus getCtx/FIRE call flags to
help filter false positives (generic struct field comparisons).
"""
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
CODE_LO, CODE_HI = 0x400000, 0x600000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE

CALL_CTX = 0x49f6b0
CALL_FIRE = 0x49b860

# ---- function starts from call rel32 targets ----
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
fn_next = {fn_list[k]: fn_list[k+1] if k+1 < len(fn_list) else fn_list[k]+0x600
           for k in range(len(fn_list))}

def disasm_fn(va, max_bytes=0x600):
    end = va + max_bytes
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

COND_JMP = {'je','jne','jz','jnz','jg','jge','jae','jl','jle','jb','jbe','js','jns','jo','jno','jp','jnp','jc','jnc','loop','loope','loopne'}

def has_cond_jump(insns, from_idx, window=8):
    for j in range(from_idx+1, min(from_idx+1+window, len(insns))):
        if insns[j].mnemonic in COND_JMP:
            return True
    return False

def find_asserts(insns):
    """Return list of (id, base_reg, kind) candidate assertions in this fn."""
    res = []
    # idiom A: direct cmp [BASE+0], imm
    for idx, ins in enumerate(insns):
        if ins.mnemonic == 'cmp' and len(ins.operands) == 2:
            o0, o1 = ins.operands[0], ins.operands[1]
            if (o0.type == CS_OP_MEM and o0.mem.index == 0 and o0.mem.disp == 0
                    and o1.type == CS_OP_IMM):
                base = md.reg_name(o0.mem.base) if o0.mem.base else None
                v = o1.imm & 0xffff
                if base and 0 <= v <= 0x3f and has_cond_jump(insns, idx, 8):
                    res.append((v, base, 'direct'))
    # idiom B: load [BASE+0] into R2, then cmp R2, imm (within window)
    loads = []
    for idx, ins in enumerate(insns):
        if ins.mnemonic in ('mov','movzx','movsx') and len(ins.operands) == 2:
            o0, o1 = ins.operands[0], ins.operands[1]
            if (o0.type == CS_OP_REG and o1.type == CS_OP_MEM and o1.mem.index == 0
                    and o1.mem.disp == 0):
                base = md.reg_name(o1.mem.base) if o1.mem.base else None
                if base:
                    loads.append((idx, md.reg_name(o0.reg), base))
    for (idx, dst, base) in loads:
        clobbered = False
        for j in range(idx+1, min(idx+12, len(insns))):
            ins = insns[j]
            # stop if dst reg is overwritten by a fresh load
            if (ins.mnemonic in ('mov','movzx','movsx','lea','pop') and len(ins.operands) >= 1
                    and ins.operands[0].type == CS_OP_REG
                    and md.reg_name(ins.operands[0].reg) == dst):
                clobbered = True
                break
            if ins.mnemonic in ('cmp','sub','test','xor','and','or') and len(ins.operands) >= 2:
                o0 = ins.operands[0]
                if o0.type == CS_OP_REG and md.reg_name(o0.reg) == dst:
                    o1 = ins.operands[1]
                    if o1.type == CS_OP_IMM:
                        v = o1.imm & 0xffff
                        if 0 <= v <= 0x3f and has_cond_jump(insns, j, 4):
                            res.append((v, base, 'via-load'))
    return res

def calls_target(insns, target):
    for ins in insns:
        if ins.mnemonic == 'call' and ins.operands and ins.operands[0].type == CS_OP_IMM:
            if (ins.operands[0].imm & 0xffffffff) == target:
                return True
    return False

rows = []
for fn in fn_list:
    insns = disasm_fn(fn, fn_next.get(fn, fn+0x600) - fn)
    if not insns:
        continue
    a = find_asserts(insns)
    if not a:
        continue
    ids = sorted(set(x[0] for x in a))
    bases = sorted(set(x[1] for x in a))
    ctx = calls_target(insns, CALL_CTX)
    fire = calls_target(insns, CALL_FIRE)
    rows.append((fn, ids, bases, ctx, fire, len(insns)))

rows.sort(key=lambda r: (r[1], r[0]))
print(f"{'fn':10s} {'ids':28s} {'bases':10s} {'ctx':4s} {'fire':5s} {'insns'}")
for fn, ids, bases, ctx, fire, nins in rows:
    print(f"{fn:#010x} {str(ids):28s} {str(bases):10s} {str(ctx):4s} {str(fire):5s} {nins}")
all_ids = set()
for _, ids, _, _, _, _ in rows:
    all_ids.update(ids)
print(f"\nFunctions with >=1 candidate id: {len(rows)}")
print(f"Unique candidate ids: {sorted(all_ids)}")
# also list handlers per id
from collections import defaultdict
by_id = defaultdict(list)
for fn, ids, bases, ctx, fire, nins in rows:
    for i in ids:
        by_id[i].append(fn)
print("\n=== handlers per candidate id ===")
for i in sorted(by_id):
    print(f"id {i:2d}: {[f'0x{f:x}' for f in by_id[i]]}")
