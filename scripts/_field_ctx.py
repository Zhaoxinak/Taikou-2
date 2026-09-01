# -*- coding: utf-8 -*-
"""
_field_ctx.py — 对给定表某偏移的「每次读」打印所在函数 + 后续 N 条指令上下文
用法: python scripts/_field_ctx.py <表基址> <偏移> [后续条数,默认8]
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

def build_fn_bounds():
    fn_starts = set()
    i, n = 0, len(MEM) - 5
    while i < n:
        b = MEM[i]
        if b == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if CODE_LO <= t < CODE_HI: fn_starts.add(t)
        elif b in (0xC3, 0xC2): fn_starts.add(BASE + i + 1)
        elif b == 0xE9:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if t > BASE + i and CODE_LO <= t < CODE_HI: fn_starts.add(t)
        i += 1
    k = 0
    while True:
        p = MEM.find(b'\x55\x89\xe5', k)
        if p < 0: break
        fn_starts.add(BASE + p); k = p + 1
    fl = sorted(fn_starts)
    nxt = {}
    for i2 in range(len(fl)):
        nxt[fl[i2]] = fl[i2+1] if i2+1 < len(fl) else fl[i2] + 0x800
    return fl, nxt

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

def main():
    tbl = int(sys.argv[1], 16)
    field = int(sys.argv[2], 16)
    ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    fl, fn_next = build_fn_bounds()
    sites = set()
    for fn in fl:
        nxt = fn_next[fn]
        if nxt - fn > 0x800: nxt = fn + 0x800
        for ins in disasm_fn(fn, nxt - fn):
            for o in ins.operands:
                v = None
                if o.type == CS_OP_IMM: v = o.imm & 0xffffffff
                elif o.type == CS_OP_MEM and o.mem.disp: v = o.mem.disp & 0xffffffff
                if v == tbl:
                    sites.add(fn); break
            else:
                continue
            break
    print(f"表 {tbl:#x} 引用函数 {len(sites)} 个; 目标 +{field:#x}")
    shown = 0
    for fn in sorted(sites):
        nxt = fn_next[fn]
        if nxt - fn > 0x800: nxt = fn + 0x800
        insns = disasm_fn(fn, nxt - fn)
        state = {}
        def st(r): return list(state[r]) if r in state else [1, 0]
        for idx, ins in enumerate(insns):
            m, ops = ins.mnemonic, ins.operands
            if m in ('movzx','movsx','mov') and len(ops)==2 and ops[0].type==CS_OP_REG and ops[1].type==CS_OP_MEM:
                base = md.reg_name(ops[1].mem.base) if ops[1].mem.base else None
                ix = md.reg_name(ops[1].mem.index) if ops[1].mem.index else None
                if base in state and state[base][1]==tbl and ops[1].mem.disp==field and ix is None:
                    dst = md.reg_name(ops[0].reg)
                    print(f"\n--- 函数 {fn:#x} @ {ins.address:#x}: {m} [{ins.op_str}] -> {dst} ---")
                    for j in range(idx, min(idx+1+ctx, len(insns))):
                        mark = ">>" if j==idx else "  "
                        print(f"   {mark} {insns[j].address:#x}: {insns[j].mnemonic} {insns[j].op_str}")
                    shown += 1
            if m=='lea' and len(ops)==2 and ops[0].type==CS_OP_REG and ops[1].type==CS_OP_MEM:
                b=md.reg_name(ops[1].mem.base) if ops[1].mem.base else None
                ix=md.reg_name(ops[1].mem.index) if ops[1].mem.index else None
                cb,kb=(st(b) if b else (0,0)); ci,ki=(st(ix) if ix else (0,0))
                state[md.reg_name(ops[0].reg)]=[cb+ci*ops[1].mem.scale, kb+ki*ops[1].mem.scale+ops[1].mem.disp] if (cb+ci*ops[1].mem.scale or kb+ki*ops[1].mem.scale+ops[1].mem.disp) else [1,0]
            elif m=='shl' and len(ops)==2 and ops[0].type==CS_OP_REG and ops[1].type==CS_OP_IMM:
                r=md.reg_name(ops[0].reg); c,k=st(r); s=1<<(ops[1].imm&0x1f); state[r]=[c*s,k*s]
            elif m in ('add','sub') and len(ops)==2 and ops[0].type==CS_OP_REG:
                r=md.reg_name(ops[0].reg); c,k=st(r); sg=1 if m=='add' else -1
                if ops[1].type==CS_OP_IMM: state[r]=[c,k+sg*ops[1].imm]
                elif ops[1].type==CS_OP_REG:
                    c2,k2=st(md.reg_name(ops[1].reg)); state[r]=[c+sg*c2,k+sg*k2]
                else: state.pop(r,None)
            elif m in ('mov','movzx','movsx') and len(ops)==2 and ops[0].type==CS_OP_REG:
                d=md.reg_name(ops[0].reg)
                if ops[1].type==CS_OP_REG: state[d]=st(md.reg_name(ops[1].reg))
                elif ops[1].type==CS_OP_IMM: state[d]=[0,ops[1].imm&0xffffffff]
                else: state.pop(d,None)
            elif ops and ops[0].type==CS_OP_REG and m in ('and','or','xor','pop','imul'):
                state.pop(md.reg_name(ops[0].reg),None)
    print(f"\n(共 {shown} 处读点)")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
