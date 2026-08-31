# -*- coding: utf-8 -*-
"""Extract per-handler [ctx+8] (arg) predicates for event handlers (续107).

For each handler:
  1. infer the CTX base register (the register dereferenced at ctx offsets
     0 / 4 / 6 / 8 / 0xc most often)
  2. find the ARG register loaded from [ctx+8]
  3. dump every instruction that touches ARG (the data-flow of the argument)
  4. collect: call targets, global immediates (0x4f0000..0x540000),
     whether [ctx+0xc] (flags) is read
Then group handlers by a "signature" so shared predicate patterns show up.
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
CTX_OFFS = (0, 4, 6, 8, 0xc)
GLOB_LO, GLOB_HI = 0x4f0000, 0x540000

FAM = {}
for lo, hi in (('ax','eax'),('bx','ebx'),('cx','ecx'),('dx','edx'),('si','esi'),('di','edi'),('bp','ebp'),('sp','esp')):
    FAM[lo] = {lo, hi}; FAM[hi] = {lo, hi}
def fam(r): return FAM.get(r, {r})

# ---- function starts (hybrid, same as _evt_scan_wide) ----
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

def analyze(fn):
    nxt = fn_next[fn]
    if nxt - fn > 0x800: nxt = fn + 0x800
    insns = disasm_fn(fn, nxt - fn)
    if not insns: return None
    # 1. infer ctx base: register dereferenced at the most ctx offsets
    score = {}
    for ins in insns:
        for o in ins.operands:
            if o.type == CS_OP_MEM and o.mem.base:
                b = md.reg_name(o.mem.base)
                if o.mem.disp in CTX_OFFS:
                    score.setdefault(b, set()).add(o.mem.disp)
    ctxbase = max(score, key=lambda r: len(score[r])) if score else None
    # 2. arg register: loaded from [ctx+8]
    argreg = None; argaddr = None
    reads_flags = False
    if ctxbase:
        for ins in insns:
            if ins.mnemonic in ('mov','movzx','movsx') and len(ins.operands)==2:
                o0,o1 = ins.operands[0], ins.operands[1]
                if (o0.type==CS_OP_REG and o1.type==CS_OP_MEM and o1.mem.base
                        and md.reg_name(o1.mem.base)==ctxbase and o1.mem.disp==8 and o1.mem.index==0):
                    argreg = md.reg_name(o0.reg); argaddr = ins.address; break
            for o in ins.operands:
                if o.type == CS_OP_MEM and o.mem.base and md.reg_name(o.mem.base)==ctxbase and o.mem.disp==0xc:
                    reads_flags = True
    # 3. data-flow of arg + calls + globals
    calls = []; globals_ = set(); argflow = []; argf = fam(argreg) if argreg else set()
    for ins in insns:
        if ins.mnemonic == 'call' and ins.operands and ins.operands[0].type==CS_OP_IMM:
            calls.append(ins.operands[0].imm & 0xffffffff)
        for o in ins.operands:
            if o.type == CS_OP_IMM and GLOB_LO <= (o.imm & 0xffffffff) < GLOB_HI:
                globals_.add(o.imm & 0xffffffff)
        if argreg:
            txt = f"{ins.mnemonic} {ins.op_str}"
            uses = False
            for o in ins.operands:
                if o.type == CS_OP_REG and md.reg_name(o.reg) in argf: uses = True
                if o.type == CS_OP_MEM and o.mem.base and md.reg_name(o.mem.base) in argf: uses = True
                if o.type == CS_OP_MEM and o.mem.index and md.reg_name(o.mem.index) in argf: uses = True
            if uses:
                argflow.append((ins.address, txt))
    return dict(fn=fn, nins=len(insns), ctx=ctxbase, argreg=argreg, argaddr=argaddr,
                flags=reads_flags, calls=sorted(set(calls)), globals=sorted(globals_),
                argflow=argflow, insns=insns)

# handlers to analyse: the PENDING set from event_handlers_full_ref
TARGETS = [
    0x45dc50, 0x461510, 0x488993, 0x447520, 0x450b90, 0x4608b7, 0x461da0, 0x44d950,
    0x41ddd5, 0x4c9db0, 0x4a7000, 0x45cc40, 0x4d1080, 0x44a120,
    0x441750, 0x45e78c, 0x460420, 0x46e2e0, 0x470260, 0x4b4d10,
    0x4d34cb, 0x4146c0, 0x415b70, 0x41adb0, 0x4c34cf, 0x4c3610,
    0x4d5560, 0x4d83e0, 0x41d980, 0x444220, 0x460660, 0x4b3890, 0x4b3b58,
    0x4d5a20, 0x441cf0, 0x4a7160,
    0x4a3df3, 0x4c2d5b, 0x45f020, 0x4accb0, 0x4da170, 0x4daf20, 0x484f34,
    # reference: already-decoded handlers, for calibration
    0x4e82c0, 0x4e7e10, 0x4b4b20, 0x44ca90, 0x4b3ac0, 0x4499f0,
]

VERBOSE = '-v' in sys.argv
rows = {}
for t in TARGETS:
    a = analyze(t)
    if a: rows[t] = a

print(f"{'handler':10s} {'ctx':5s} {'arg':5s} {'flg':4s} {'calls':38s} {'globals'}")
for t in TARGETS:
    a = rows.get(t)
    if not a:
        print(f"0x{t:x}  <none>"); continue
    cs = ','.join(f'{c&0xffffff:x}' for c in a['calls'] if c not in (CALL_CTX, CALL_FIRE))
    gs = ','.join(f'0x{g:x}' for g in a['globals'])
    print(f"0x{t:x} {str(a['ctx']):5s} {str(a['argreg']):5s} {str(a['flags']):4s} {cs:38s} {gs}")

print("\n=== signature groups (calls+globals) ===")
from collections import defaultdict
groups = defaultdict(list)
for t, a in rows.items():
    key = (tuple(c for c in a['calls'] if c not in (CALL_CTX, CALL_FIRE)), tuple(a['globals']))
    groups[key].append(t)
for key, v in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    cs = ','.join(f'{c&0xffffff:x}' for c in key[0])
    gs = ','.join(f'0x{g:x}' for g in key[1])
    print(f"\n[{len(v)}] calls=({cs}) globals=({gs})\n    {[f'0x{x:x}' for x in sorted(v)]}")

if VERBOSE:
    for t in TARGETS:
        a = rows.get(t)
        if not a or not a['argflow']: continue
        print(f"\n===== 0x{t:x} ctx={a['ctx']} arg={a['argreg']} (loaded @0x{a['argaddr']:x} if any) flags={a['flags']} =====")
        for ad, txt in a['argflow'][:40]:
            print(f"   0x{ad:x}: {txt}")
