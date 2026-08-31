# -*- coding: utf-8 -*-
"""
_duel_hp_init.py — 找把「角色体力」写入决斗对象 HP 字段 (this+0x19d=0x514995, this+0x3d=0x514835) 的初始化函数
用法: python scripts/_duel_hp_init.py
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

DUEL_OBJ = 0x5147f8
HP_A_OFF = 0x19d   # 0x5147f8 + 0x19d = 0x514995
HP_B_OFF = 0x3d    # 0x5147f8 + 0x3d  = 0x514835

FAM = {}
for lo, hi in (('ax','eax'),('bx','ebx'),('cx','ecx'),('dx','edx'),('si','esi'),
               ('di','edi'),('bp','ebp'),('sp','esp')):
    FAM[lo] = {lo, hi}; FAM[hi] = {lo, hi}
def isfam(a, b): return a == b or a in FAM.get(b, set()) or b in FAM.get(a, set())


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
    fl, fn_next = build_fn_bounds()
    hits = []
    for fn in fl:
        nxt = fn_next[fn]
        if nxt - fn > 0x800: nxt = fn + 0x800
        insns = disasm_fn(fn, nxt - fn)
        state = {}
        def st(r):
            return list(state[r]) if r in state else [1, 0]
        for ins in insns:
            m, ops = ins.mnemonic, ins.operands
            # 捕获写 this+HP_OFF: mov word[reg+off], src  (reg 指向 0x5147f8)
            if m in ('mov','movzx','movsx','add','sub','or','and','xor') and len(ops) == 2 \
               and ops[0].type == CS_OP_MEM and ops[0].mem.base and ops[0].mem.index == 0:
                b = md.reg_name(ops[0].mem.base)
                disp = ops[0].mem.disp & 0xffffffff
                if b in state and state[b][1] == DUEL_OBJ and disp in (HP_A_OFF, HP_B_OFF):
                    hits.append((fn, ins.address, m, ins.op_str, disp))
            # 符号状态更新
            if m == 'lea' and len(ops) == 2 and ops[0].type == CS_OP_REG and ops[1].type == CS_OP_MEM:
                b = md.reg_name(ops[1].mem.base) if ops[1].mem.base else None
                ix = md.reg_name(ops[1].mem.index) if ops[1].mem.index else None
                cb, kb = (st(b) if b else (0, 0))
                ci, ki = (st(ix) if ix else (0, 0))
                coeff = cb + ci * ops[1].mem.scale
                const = kb + ki * ops[1].mem.scale + ops[1].mem.disp
                state[md.reg_name(ops[0].reg)] = [coeff, const] if (coeff or const) else [1, 0]
            elif m == 'shl' and len(ops) == 2 and ops[0].type == CS_OP_REG and ops[1].type == CS_OP_IMM:
                r = md.reg_name(ops[0].reg); c, k = st(r); s = 1 << (ops[1].imm & 0x1f)
                state[r] = [c * s, k * s]
            elif m in ('add','sub') and len(ops) == 2 and ops[0].type == CS_OP_REG:
                r = md.reg_name(ops[0].reg); c, k = st(r); sg = 1 if m == 'add' else -1
                if ops[1].type == CS_OP_IMM: state[r] = [c, k + sg * ops[1].imm]
                elif ops[1].type == CS_OP_REG:
                    c2, k2 = st(md.reg_name(ops[1].reg)); state[r] = [c + sg * c2, k + sg * k2]
                else: state.pop(r, None)
            elif m in ('mov','movzx','movsx') and len(ops) == 2 and ops[0].type == CS_OP_REG:
                d = md.reg_name(ops[0].reg)
                if ops[1].type == CS_OP_REG:
                    s = md.reg_name(ops[1].reg); state[d] = st(s)
                elif ops[1].type == CS_OP_IMM:
                    state[d] = [0, ops[1].imm & 0xffffffff]
                else: state.pop(d, None)
            elif ops and ops[0].type == CS_OP_REG and m in ('and','or','xor','pop','imul'):
                state.pop(md.reg_name(ops[0].reg), None)
    # 去重函数级
    fns = sorted({h[0] for h in hits})
    print(f"=== 决斗 HP 初始化写入命中 {len(hits)} 处, 函数 {len(fns)} 个 ===")
    for fn in fns:
        print(f"\n函数 {fn:#x}:")
        for h in [x for x in hits if x[0] == fn]:
            print(f"   {h[1]:#x}: {h[2]} [{h[3]}]  (HP字段偏移 {h[4]:#x})")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
