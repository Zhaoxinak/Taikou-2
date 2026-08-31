# -*- coding: utf-8 -*-
"""Event-handler self-assertion scanner (v7, hybrid).

Function starts = call rel32 targets  UNION  post-ret / forward-jmp addresses
UNION  standard prologues (byte pattern 55 89 E5 = push ebp; mov ebp, esp).
This gives clean per-function boundaries AND captures vtable-only handlers
(e.g. 0x4e82c0) that are never `call`-referenced.

Per function, detect both assertion idioms (direct cmp [base+0] and via-load),
plus signals (calls getCtx/FIRE, reads [base+8] arg / [base+0xc] flags).
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
COND_JMP = {'je','jne','jz','jnz','jg','jge','jae','jl','jle','jb','jbe','js','jns','jo','jno','jp','jnp','jc','jnc','loop','loope','loopne'}

# ---- function starts ----
fn_starts = set()
i = 0; n = len(MEM) - 5
while i < n:
    b = MEM[i]
    if b == 0xE8:  # call rel32
        rel = struct.unpack('<i', MEM[i+1:i+5])[0]
        tgt = (BASE + i + 5 + rel) & 0xffffffff
        if CODE_LO <= tgt < CODE_HI:
            fn_starts.add(tgt)
    elif b == 0xC3 or b == 0xC2:  # ret / ret imm
        fn_starts.add(BASE + i + 1)
    elif b == 0xE9:  # jmp rel32 (forward assumed)
        rel = struct.unpack('<i', MEM[i+1:i+5])[0]
        tgt = (BASE + i + 5 + rel) & 0xffffffff
        if tgt > BASE + i and CODE_LO <= tgt < CODE_HI:
            fn_starts.add(tgt)
    i += 1
# standard prologue: 55 89 E5  (push ebp; mov ebp, esp)
k = 0
while True:
    p = MEM.find(b'\x55\x89\xe5', k)
    if p < 0: break
    fn_starts.add(BASE + p)
    k = p + 1

fn_list = sorted(fn_starts)
fn_next = {}
for k in range(len(fn_list)):
    fn_next[fn_list[k]] = fn_list[k+1] if k+1 < len(fn_list) else fn_list[k] + 0x800

def disasm_fn(va, max_bytes):
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

def analyze_fn(insns):
    ctx = False; fire = False
    a_bases = set(); derefs = set(); loads = []; ids = set()
    for idx, ins in enumerate(insns):
        m = ins.mnemonic; ops = ins.operands
        if m == 'call' and ops and ops[0].type == CS_OP_IMM:
            t = ops[0].imm & 0xffffffff
            if t == CALL_CTX: ctx = True
            elif t == CALL_FIRE: fire = True
        for o in ops:
            if o.type == CS_OP_MEM:
                b = md.reg_name(o.mem.base) if o.mem.base else None
                if b: derefs.add((b, o.mem.disp))
        if m == 'cmp' and len(ops) == 2:
            o0, o1 = ops[0], ops[1]
            if o0.type == CS_OP_MEM and o0.mem.index == 0 and o0.mem.disp == 0 and o1.type == CS_OP_IMM:
                b = md.reg_name(o0.mem.base) if o0.mem.base else None
                v = o1.imm & 0xffff
                if b and 0 <= v <= 0x3f and any(insns[k].mnemonic in COND_JMP for k in range(idx+1, min(idx+9, len(insns)))):
                    ids.add(v); a_bases.add(b)
        if m in ('mov','movzx','movsx') and len(ops) == 2:
            o0, o1 = ops[0], ops[1]
            if o0.type == CS_OP_REG and o1.type == CS_OP_MEM and o1.mem.index == 0 and o1.mem.disp == 0:
                b = md.reg_name(o1.mem.base) if o1.mem.base else None
                if b: loads.append((idx, md.reg_name(o0.reg), b))
    # register families: a 16-bit subreg and its 32-bit parent are the *same* id value
    FAM = {}
    for lo, hi in (('ax','eax'),('bx','ebx'),('cx','ecx'),('dx','edx'),
                   ('si','esi'),('di','edi'),('bp','ebp'),('sp','esp')):
        FAM[lo] = {lo, hi}; FAM[hi] = {lo, hi}
    def same_fam(a, b):
        return a in FAM.get(b, set()) or b in FAM.get(a, set()) or a == b

    for (idx, dst, base) in loads:
        for j in range(idx+1, len(insns)):
            ins = insns[j]
            ops = ins.operands
            # arithmetic that overwrites the id register clobbers it (value no longer the id)
            if (ins.mnemonic in ('mov','movzx','movsx','lea','pop','inc','dec','add','sub','shl','shr','sar','neg')
                    and len(ops) >= 1 and ops[0].type == CS_OP_REG and same_fam(md.reg_name(ops[0].reg), dst)):
                # `dec dst` / `sub dst,1` followed by a cond jump => original id was 1
                if ins.mnemonic == 'dec' and len(ops) == 1:
                    if any(insns[k].mnemonic in COND_JMP for k in range(j+1, min(j+6, len(insns)))):
                        ids.add(1); a_bases.add(base)
                elif ins.mnemonic == 'sub' and len(ops) == 2 and ops[1].type == CS_OP_IMM and (ops[1].imm & 0xffff) == 1:
                    if any(insns[k].mnemonic in COND_JMP for k in range(j+1, min(j+6, len(insns)))):
                        ids.add(1); a_bases.add(base)
                break
            if ins.mnemonic in ('cmp','sub','test','xor','and','or') and len(ops) >= 2:
                o0 = ops[0]
                if o0.type == CS_OP_REG and same_fam(md.reg_name(o0.reg), dst):
                    o1 = ops[1]
                    if o1.type == CS_OP_IMM:
                        v = o1.imm & 0xffff
                        if 0 <= v <= 0x3f and any(insns[k].mnemonic in COND_JMP for k in range(j+1, min(j+6, len(insns)))):
                            ids.add(v); a_bases.add(base)
                    elif o1.type == CS_OP_REG and same_fam(md.reg_name(o1.reg), dst) and ins.mnemonic in ('test','or','and'):
                        # self-op on the id register => id == 0  (test/or/and reg,reg)
                        if any(insns[k].mnemonic in COND_JMP for k in range(j+1, min(j+6, len(insns)))):
                            ids.add(0); a_bases.add(base)
    ra = any((b, 8) in derefs for b in a_bases)
    rf = any((b, 0xc) in derefs for b in a_bases)
    # strict: the assertion base must ALSO touch another ctx field (4,6,8,0xc),
    # which distinguishes a real event-context object from a zero/null check
    # (`cmp [eax],0`) or a generic single-field struct compare.
    other = any((b, off) in derefs for b in a_bases for off in (4, 6, 8, 0xc))
    return ids, ctx, fire, ra, rf, other

# boundary ids that are actually province/max-id limits, NOT event ids
BOUNDARY = {0x31, 0x3f}

results = []
for fn in fn_list:
    nxt = fn_next[fn]
    if nxt - fn > 0x800:
        nxt = fn + 0x800
    insns = disasm_fn(fn, nxt - fn)
    if not insns: continue
    ids, ctx, fire, ra, rf, other = analyze_fn(insns)
    ids = sorted(i for i in ids if i not in BOUNDARY)
    if ids and (ctx or fire):
        # confidence: HIGH if calls getCtx/FIRE; MED if reads arg8/flags on id base
        conf = 'HIGH' if (ctx or fire) else ('MED' if (ra or rf) else 'LOW')
        results.append((fn, ids, ctx, fire, ra, rf, conf, len(insns)))

# always keep known handlers for reference (definitely verified)
KNOWN = {0x4e82c0:(13,14),0x4e7e10:(10,),0x4b4b20:(9,),0x44ca90:(9,),
         0x4b3ac0:(15,),0x4499f0:(29,)}
for kf, kd in KNOWN.items():
    if not any(r[0]==kf for r in results):
        results.append((kf, list(kd), None, None, None, None, 'KNOWN', -1))

results.sort(key=lambda r: (r[1], r[0]))
print(f"{'fn':10s} {'ids':26s} {'ctx':5s} {'fire':5s} {'arg8':5s} {'flgC':5s} {'conf':5s} {'insns'}")
for fn, ids, ctx, fire, ra, rf, conf, n in results:
    ctxs = str(ctx) if ctx is not None else '?'
    fires = str(fire) if fire is not None else '?'
    ras = str(ra) if ra is not None else '?'
    rfs = str(rf) if rf is not None else '?'
    print(f"{fn:#010x} {str(ids):26s} {ctxs:5s} {fires:5s} {ras:5s} {rfs:5s} {conf:5s} {n}")

all_ids = set()
for _, ids, *_ in results:
    all_ids.update(ids)
print(f"\nHandlers: {len(results)}  | unique event ids: {sorted(all_ids)}")

from collections import defaultdict
by_id = defaultdict(list)
for fn, ids, *_ in results:
    for i in ids:
        by_id[i].append(fn)
print("\n=== handlers per event id (excluding boundary 0x31/0x3f) ===")
for i in sorted(by_id):
    print(f"id {i:2d}: {[f'0x{f:x}' for f in by_id[i]]}")
