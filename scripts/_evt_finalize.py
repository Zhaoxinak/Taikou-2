# -*- coding: utf-8 -*-
"""Finalize event id->handler map (v1).

Re-derives the map like _evt_scan_wide.py but ALSO:
  * records assertion KIND (direct / via_cmp / via_test0 / via_dec1)
  * records whether the assertion's conditional jump targets a ret/exit
    (canonical top-level self-assertion)
  * detects DISPATCHERS: a candidate that CALLS another candidate handler
    (likely a sub-dispatcher, not a leaf handler)
Outputs a clean per-id map with confidence + dispatcher flags.
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

FAM = {}
for lo, hi in (('ax','eax'),('bx','ebx'),('cx','ecx'),('dx','edx'),('si','esi'),('di','edi'),('bp','ebp'),('sp','esp')):
    FAM[lo] = {lo, hi}; FAM[hi] = {lo, hi}
def same_fam(a, b):
    return a in FAM.get(b, set()) or b in FAM.get(a, set()) or a == b

# ---- function starts (hybrid) ----
fn_starts = set()
i = 0; n = len(MEM) - 5
while i < n:
    b = MEM[i]
    if b == 0xE8:
        rel = struct.unpack('<i', MEM[i+1:i+5])[0]
        tgt = (BASE + i + 5 + rel) & 0xffffffff
        if CODE_LO <= tgt < CODE_HI: fn_starts.add(tgt)
    elif b == 0xC3 or b == 0xC2:
        fn_starts.add(BASE + i + 1)
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
    fn_end = insns[-1].address + insns[-1].size
    rets = {ins.address for ins in insns if ins.mnemonic == 'ret'}
    ctx = fire = False
    callees = set()
    # direct assertions: cmp [base+0], imm  (idiom A)
    direct = set()
    for ins in insns:
        m = ins.mnemonic; ops = ins.operands
        if m == 'call' and ops and ops[0].type == CS_OP_IMM:
            t = ops[0].imm & 0xffffffff
            if t == CALL_CTX: ctx = True
            elif t == CALL_FIRE: fire = True
            callees.add(t)
        if m == 'cmp' and len(ops) == 2:
            o0, o1 = ops[0], ops[1]
            if o0.type == CS_OP_MEM and o0.mem.index == 0 and o0.mem.disp == 0 and o1.type == CS_OP_IMM:
                b = md.reg_name(o0.mem.base) if o0.mem.base else None
                if b:
                    v = o1.imm & 0xffff
                    idx = insns.index(ins)
                    if 0 <= v <= 0x3f and any(insns[k].mnemonic in COND_JMP for k in range(idx+1, min(idx+9, len(insns)))):
                        direct.add(v)
    # via-load assertions (idiom B)
    loads = []
    for idx, ins in enumerate(insns):
        if ins.mnemonic in ('mov','movzx','movsx') and len(ins.operands)==2:
            o0,o1 = ins.operands[0], ins.operands[1]
            if o0.type==CS_OP_REG and o1.type==CS_OP_MEM and o1.mem.index==0 and o1.mem.disp==0:
                b = md.reg_name(o1.mem.base) if o1.mem.base else None
                if b: loads.append((idx, md.reg_name(o0.reg), b))
    via = set(); via_test0 = set(); via_dec1 = set()
    for (idx, dst, base) in loads:
        for j in range(idx+1, len(insns)):
            ins = insns[j]; ops = ins.operands
            if ins.mnemonic in ('mov','movzx','movsx','lea','pop','inc','dec','add','sub','shl','shr','sar','neg') and len(ops)>=1 and ops[0].type==CS_OP_REG and same_fam(md.reg_name(ops[0].reg), dst):
                if ins.mnemonic == 'dec' and len(ops)==1:
                    if any(insns[k].mnemonic in COND_JMP for k in range(j+1, min(j+6, len(insns)))):
                        via_dec1.add(1)
                elif ins.mnemonic == 'sub' and len(ops)==2 and ops[1].type==CS_OP_IMM and (ops[1].imm&0xffff)==1:
                    if any(insns[k].mnemonic in COND_JMP for k in range(j+1, min(j+6, len(insns)))):
                        via_dec1.add(1)
                break
            if ins.mnemonic in ('cmp','sub','test','xor','and','or') and len(ops)>=2:
                o0 = ops[0]
                if o0.type==CS_OP_REG and same_fam(md.reg_name(o0.reg), dst):
                    o1 = ops[1]
                    if o1.type==CS_OP_IMM:
                        v = o1.imm & 0xffff
                        if 0 <= v <= 0x3f and any(insns[k].mnemonic in COND_JMP for k in range(j+1, min(j+6, len(insns)))):
                            via.add(v)
                    elif o1.type==CS_OP_REG and same_fam(md.reg_name(o1.reg), dst) and ins.mnemonic in ('test','or','and'):
                        if any(insns[k].mnemonic in COND_JMP for k in range(j+1, min(j+6, len(insns)))):
                            via_test0.add(0)
    allids = set()
    for v in direct: allids.add(v)
    for v in via: allids.add(v)
    for v in via_test0: allids.add(v)
    for v in via_dec1: allids.add(v)
    return dict(fn=fn, ctx=ctx, fire=fire, callees=callees, direct=direct, via=via,
               via_test0=via_test0, via_dec1=via_dec1, ids=allids, end=fn_end)

BOUNDARY = {0x31, 0x3f}
cands = []
for fn in fn_list:
    a = analyze(fn)
    if not a: continue
    ids = sorted(i for i in a['ids'] if i not in BOUNDARY)
    if ids and (a['ctx'] or a['fire']):
        a['ids_filtered'] = ids
        cands.append(a)

# dispatcher detection: does this candidate call another candidate?
cand_fns = {c['fn'] for c in cands}
for c in cands:
    c['calls_other'] = sorted(f for f in c['callees'] if f in cand_fns and f != c['fn'])

# confidence per id-edge:
#  strong = direct or via_cmp ; medium = via_test0/via_dec1
def conf_of(c, vid):
    if vid in c['direct'] or vid in c['via']: return 'strong'
    if vid in c['via_test0'] or vid in c['via_dec1']: return 'medium'
    return '?'

by_id = {}
for c in cands:
    for vid in c['ids_filtered']:
        by_id.setdefault(vid, []).append(c)

print(f"Candidates: {len(cands)}  ids: {sorted(by_id)}")
print("\n=== per-handler ===")
for c in sorted(cands, key=lambda x: x['fn']):
    disp = " DISPATCHER->"+','.join(f'0x{f:x}' for f in c['calls_other']) if c['calls_other'] else ''
    print(f"0x{c['fn']:x} ctx={c['ctx']} fire={c['fire']}{disp}  ids={c['ids_filtered']} "
          f"direct={sorted(c['direct'])} via={sorted(c['via'])} t0={sorted(c['via_test0'])} d1={sorted(c['via_dec1'])}")

print("\n=== per-id map (confidence: strong=direct/via_cmp, medium=test0/dec1) ===")
for vid in sorted(by_id):
    parts = []
    for c in by_id[vid]:
        parts.append(f"0x{c['fn']:x}:{conf_of(c,vid)}")
    print(f"id {vid:2d}: {parts}")
