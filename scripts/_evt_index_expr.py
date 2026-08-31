# -*- coding: utf-8 -*-
"""Symbolic index-expression extractor for event handlers (续107).

For every handler, track each register symbolically as (coeff*X + const)
through shl/lea/imul/add/sub, and report every moment a register becomes
`coeff*X + GLOBAL`. This reveals WHICH runtime table the handler indexes and
WITH WHICH STRIDE -- i.e. the [ctx+8] (arg) predicate.

Known tables (from MEMORY.md):
    0x519548  国情表          stride 5  (49 provinces)
    0x5179b8  49国政治/关系表  stride 14 (49 provinces)
    0x51eb88  城/町表          stride 31 (200 entries)
    0x519868  武将实体表       stride 47 (370 entries)
    0x51dc60  外交关系矩阵     (triangular)
    0x516a28  S7 运行时表      stride 16 (200)
    0x5197b0  S5 武将槽        stride 30 (6)
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
GLOB_LO, GLOB_HI = 0x4f0000, 0x540000

FAM = {}
for lo, hi in (('ax','eax'),('bx','ebx'),('cx','ecx'),('dx','edx'),('si','esi'),('di','edi'),('bp','ebp'),('sp','esp')):
    FAM[lo] = {lo, hi}; FAM[hi] = {lo, hi}
def isfam(a, b): return a in FAM.get(b, set()) or b in FAM.get(a, set()) or a == b

fn_starts = set()
i = 0; n = len(MEM) - 5
while i < n:
    b = MEM[i]
    if b == 0xE8:
        rel = struct.unpack('<i', MEM[i+1:i+5])[0]
        tgt = (BASE + i + 5 + rel) & 0xffffffff
        if CODE_LO <= tgt < CODE_HI: fn_starts.add(tgt)
    elif b in (0xC3, 0xC2): fn_starts.add(BASE + i + 1)
    elif b == 0xE9:
        rel = struct.unpack('<i', MEM[i+1:i+5])[0]
        tgt = (BASE + i + 5 + rel) & 0xffffffff
        if tgt > BASE + i and CODE_LO <= tgt < CODE_HI: fn_starts.add(tgt)
    i += 1
k = 0
while True:
    p = MEM.find(b'\x55\x89\xe5', k)
    if p < 0: break
    fn_starts.add(BASE + p); k = p + 1
fn_list = sorted(fn_starts)
fn_next = {}
for kk in range(len(fn_list)):
    fn_next[fn_list[kk]] = fn_list[kk+1] if kk+1 < len(fn_list) else fn_list[kk] + 0x800

def disasm_fn(va, max_bytes):
    end = va + max_bytes; cur = va; out = []
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

def sym(fn):
    nxt = fn_next[fn]
    if nxt - fn > 0x800: nxt = fn + 0x800
    insns = disasm_fn(fn, nxt - fn)
    state = {}   # reg -> [coeff, const]  representing coeff*X + const
    hits = []
    for ins in insns:
        m = ins.mnemonic; ops = ins.operands
        def dst():
            return md.reg_name(ops[0].reg) if ops and ops[0].type == CS_OP_REG else None
        # an untracked register is treated as [1,0] (i.e. 1*X + 0)
        def st(r):
            return list(state[r]) if r in state else [1, 0]

        if m == 'lea' and len(ops) == 2 and ops[0].type == CS_OP_REG and ops[1].type == CS_OP_MEM:
            o0, o1 = ops[0], ops[1]
            b = md.reg_name(o1.mem.base) if o1.mem.base else None
            ix = md.reg_name(o1.mem.index) if o1.mem.index else None
            d = md.reg_name(o0.reg)
            cb, kb = (st(b) if b else (0, 0))
            ci, ki = (st(ix) if ix else (0, 0))
            coeff = cb + ci * o1.mem.scale
            const = kb + ki * o1.mem.scale + o1.mem.disp
            if coeff != 0 or const != 0:
                state[d] = [coeff, const]
            else:
                state.pop(d, None)
        elif m == 'shl' and len(ops) == 2 and ops[0].type == CS_OP_REG and ops[1].type == CS_OP_IMM:
            d = dst(); c, k = st(d)
            state[d] = [c * (1 << (ops[1].imm & 0x1f)), k * (1 << (ops[1].imm & 0x1f))]
        elif m == 'imul' and len(ops) >= 2 and ops[0].type == CS_OP_REG:
            d = dst()
            if len(ops) == 3 and ops[2].type == CS_OP_IMM:
                c, k = st(d); f = ops[2].imm & 0xffff
                state[d] = [c * f, k * f]
            else:
                state.pop(d, None)
        elif m in ('add', 'sub') and len(ops) == 2 and ops[0].type == CS_OP_REG:
            d = dst(); c, k = st(d); sgn = 1 if m == 'add' else -1
            if ops[1].type == CS_OP_IMM:
                state[d] = [c, k + sgn * ops[1].imm]
            elif ops[1].type == CS_OP_REG:
                c2, k2 = st(md.reg_name(ops[1].reg))
                state[d] = [c + sgn * c2, k + sgn * k2]
            else:
                state.pop(d, None)
        elif m in ('mov','movzx','movsx','xor','and','or','pop'):
            d = dst()
            if m == 'xor' and len(ops) == 2 and ops[0].type == CS_OP_REG and ops[1].type == CS_OP_REG and isfam(md.reg_name(ops[0].reg), md.reg_name(ops[1].reg)):
                state[d] = [0, 0]
            elif m in ('mov','movzx','movsx') and len(ops) == 2 and ops[1].type == CS_OP_REG:
                s = md.reg_name(ops[1].reg)
                state[d] = st(s) if d != s else st(d)
            else:
                state.pop(d, None)
        # record hits: coeff*X + GLOBAL
        for r, (coeff, const) in state.items():
            if GLOB_LO <= const < GLOB_HI and coeff > 0:
                hits.append((ins.address, r, coeff, const))
        # dedupe consecutive identical hits
    return hits, insns

import sys as _s
sys.path.insert(0, 'scripts')
from event_handlers_full_ref import HANDLERS
allh = sorted({h for v in HANDLERS.values() for h in v})

# id lookup per handler
hid = {}
for k, v in HANDLERS.items():
    for h in v: hid.setdefault(h, []).append(k)

print(f"{'handler':10s} {'ids':12s} index expressions (coeff*X + GLOBAL)")
for h in allh:
    hits, insns = sym(h)
    seen = set(); out = []
    for (addr, r, coeff, const) in hits:
        key = (r, coeff, const)
        if key in seen: continue
        seen.add(key)
        out.append(f"{r}={coeff}*X+0x{const:x}")
    ids = ','.join(str(x) for x in hid.get(h, []))
    if out:
        print(f"0x{h:x} {ids:12s} {'; '.join(out)}")
