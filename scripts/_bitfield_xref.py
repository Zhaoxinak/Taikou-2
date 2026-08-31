# -*- coding: utf-8 -*-
"""
_bitfield_xref.py — 找某表里某偏移字段的「位测试」消费方 (续120 用)
用法: python scripts/_bitfield_xref.py <表基址> <偏移> [位掩码列表,默认 1,2,4...]
对给定表, 找到所有引用它的函数, 符号追踪持有表指针的寄存器,
捕获 `movzx reg2, byte[reg + offset]` (或 word/byte 读), 再在该函数后续指令里
找对 reg2 (或其低字节) 的 `test`/`and` 位测试, 报告命中。
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
    tbl = int(sys.argv[1], 16)
    field = int(sys.argv[2], 16)
    masks = [int(x, 0) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else [1, 2, 4, 8]
    fl, fn_next = build_fn_bounds()

    # 1) 找引用该基址的函数
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
    print(f"表 {tbl:#x}: {len(sites)} 个函数引用; 目标字段 +{field:#x}, 位掩码 {[hex(m) for m in masks]}")

    hits = []
    for fn in sorted(sites):
        nxt = fn_next[fn]
        if nxt - fn > 0x800: nxt = fn + 0x800
        insns = disasm_fn(fn, nxt - fn)
        state = {}  # reg -> [coeff, const]
        def st(r):
            return list(state[r]) if r in state else [1, 0]
        for idx, ins in enumerate(insns):
            m, ops = ins.mnemonic, ins.operands
            # 捕获读字段: movzx/movsx reg2, byte[table_reg + field]
            if m in ('movzx', 'movsx', 'mov') and len(ops) == 2 and ops[0].type == CS_OP_REG and ops[1].type == CS_OP_MEM:
                base = md.reg_name(ops[1].mem.base) if ops[1].mem.base else None
                ix = md.reg_name(ops[1].mem.index) if ops[1].mem.index else None
                disp = ops[1].mem.disp
                if base in state and state[base][1] == tbl and disp == field and ix is None:
                    dst = md.reg_name(ops[0].reg)
                    # 看后续 10 条指令有没有对 dst(或低字节) 做 test/and 位测试
                    for j in range(idx+1, min(idx+11, len(insns))):
                        ji = insns[j]
                        jm, jo = ji.mnemonic, ji.operands
                        if jm in ('test', 'and') and len(jo) == 2:
                            treg = None
                            if jo[0].type == CS_OP_REG:
                                treg = md.reg_name(jo[0].reg)
                            # 匹配 dst 或 dst 低字节 (ax/al)
                            if treg and (isfam(treg, dst)):
                                imm = jo[1].imm if jo[1].type == CS_OP_IMM else None
                                if imm is not None and imm in masks:
                                    hits.append((fn, ins.address, ji.address, m, ins.op_str, jm, ji.op_str, imm))
                                    break
            # 符号状态更新 (同 _field_map)
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

    print(f"\n=== 位测试消费方 ({len(hits)} 命中) ===")
    for fn, rd, ts, rm, ro, tm, to, mask in sorted(set(hits)):
        print(f"  函数 {fn:#x}: 读 {rm} [{ro}] @ {rd:#x}  ->  {tm} [{to}] (mask={mask:#x})")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
