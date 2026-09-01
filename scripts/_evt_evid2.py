# -*- coding: utf-8 -*-
"""Evidence dumper for event-handler self-assertions (v2).

For each candidate function, dump:
  * getCtx / FIRE call sites
  * id-load sites  (mov R, [ctx_base+0])
  * each assertion on the id register (cmp imm / test reg,reg / dec; jz)
    with its byte offset, the asserted id value, the idiom, and the
    conditional-jump TARGET + whether that target is a `ret` (=> top-level
    self-assertion that skips the body when id mismatches).
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
COND_JMP = {'je','jne','jz','jnz','jg','jge','jae','jl','jle','jb','jbe','js','jns','jo','jno','jp','jnp','jc','jnc','loop','loope','loopne'}

FAM = {}
for lo, hi in (('ax','eax'),('bx','ebx'),('cx','ecx'),('dx','edx'),('si','esi'),('di','edi'),('bp','ebp'),('sp','esp')):
    FAM[lo] = {lo, hi}; FAM[hi] = {lo, hi}
def same_fam(a, b):
    return a in FAM.get(b, set()) or b in FAM.get(a, set()) or a == b

# function starts (hybrid) -- same as scan
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
    end = va + max_bytes
    cur = va; out = []
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

def dump(fn):
    nxt = fn_next[fn]
    if nxt - fn > 0x800: nxt = fn + 0x800
    insns = disasm_fn(fn, nxt - fn)
    if not insns:
        print(f"0x{fn:x}: <no disasm>"); return
    fn_end = insns[-1].address + insns[-1].size
    rets = {ins.address for ins in insns if ins.mnemonic == 'ret'}
    # also treat a short tail (last 8 bytes) as "exit"
    print(f"\n{'='*70}\n0x{fn:x}  ({len(insns)} insns, end=0x{fn_end:x})")
    # collect ctx base reg from getCtx
    ctx_reg = None
    for idx, ins in enumerate(insns):
        if ins.mnemonic == 'call' and ins.operands and ins.operands[0].type == CS_OP_IMM:
            t = ins.operands[0].imm & 0xffffffff
            if t == CALL_CTX:
                print(f"  0x{ins.address:x}: call getCtx (0x{CALL_CTX:x})")
            elif t == CALL_FIRE:
                print(f"  0x{ins.address:x}: call FIRE  (0x{CALL_FIRE:x})")
    # find id loads and assertions
    loads = []
    for idx, ins in enumerate(insns):
        if ins.mnemonic in ('mov','movzx','movsx') and len(ins.operands)==2:
            o0,o1 = ins.operands[0], ins.operands[1]
            if o0.type==CS_OP_REG and o1.type==CS_OP_MEM and o1.mem.index==0 and o1.mem.disp==0:
                b = md.reg_name(o1.mem.base) if o1.mem.base else None
                if b: loads.append((idx, md.reg_name(o0.reg), b, ins.address))
    for (idx, dst, base, lad) in loads:
        print(f"  -- id load: 0x{lad:x}: {dst} = [{base}+0]")
        for j in range(idx+1, len(insns)):
            ins = insns[j]; ops = ins.operands
            if ins.mnemonic in ('mov','movzx','movsx','lea','pop','inc','dec','add','sub','shl','shr','sar','neg') and len(ops)>=1 and ops[0].type==CS_OP_REG and same_fam(md.reg_name(ops[0].reg), dst):
                break
            if ins.mnemonic in ('cmp','sub','test','xor','and','or') and len(ops)>=2:
                o0 = ops[0]
                if o0.type==CS_OP_REG and same_fam(md.reg_name(o0.reg), dst):
                    o1 = ops[1]
                    val=None; idiom=None
                    if o1.type==CS_OP_IMM:
                        val = o1.imm & 0xffff; idiom='cmp imm'
                    elif o1.type==CS_OP_REG and same_fam(md.reg_name(o1.reg), dst) and ins.mnemonic in ('test','or','and'):
                        val = 0; idiom='test self'
                    # look for following cond jump
                    tgt = None; is_exit = False
                    for kk in range(j+1, min(j+6, len(insns))):
                        jin = insns[kk]
                        if jin.mnemonic in COND_JMP:
                            # decode jump target
                            if jin.operands and jin.operands[0].type==CS_OP_IMM:
                                tgt = jin.operands[0].imm & 0xffffffff
                            if tgt in rets or (tgt is not None and tgt >= fn_end-8):
                                is_exit = True
                            print(f"     0x{ins.address:x}: {ins.mnemonic} {dst},..  => id {val}  [{idiom}]  jump@0x{jin.address:x} -> 0x{tgt:x} {'EXIT/ret' if is_exit else ''}")
                            break
                    else:
                        print(f"     0x{ins.address:x}: {ins.mnemonic} {dst},..  => id {val}  [{idiom}]  (no cond jmp in window)")
            # dec id-reg ; cond-jump  => original id was 1
            if ins.mnemonic == 'dec' and len(ops)==1 and ops[0].type==CS_OP_REG and same_fam(md.reg_name(ops[0].reg), dst):
                tgt=None; is_exit=False
                for kk in range(j+1, min(j+6, len(insns))):
                    jin = insns[kk]
                    if jin.mnemonic in COND_JMP:
                        if jin.operands and jin.operands[0].type==CS_OP_IMM:
                            tgt = jin.operands[0].imm & 0xffffffff
                        if tgt in rets or (tgt is not None and tgt >= fn_end-8):
                            is_exit = True
                        print(f"     0x{ins.address:x}: dec {dst}  => id 1  jump@0x{jin.address:x} -> 0x{tgt:x} {'EXIT/ret' if is_exit else ''}")
                        break
                else:
                    print(f"     0x{ins.address:x}: dec {dst}  => id 1  (no cond jmp)")

if __name__ == '__main__':
    import sys as _s
    targets = [int(x,16) for x in _s.argv[1:]] if len(_s.argv)>1 else [
        0x4a3df3, 0x4c2d5b, 0x45f020, 0x4accb0, 0x4da170, 0x4daf20,  # id 0 cands
        0x484f34,  # id 1 cand
        0x4499f0,  # id 29 (known)
    ]
    for t in targets:
        dump(t)
