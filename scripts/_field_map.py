# -*- coding: utf-8 -*-
"""
_field_map.py — 表字段访问图（续114 通用工具）

用法: python scripts/_field_map.py <表基址> [字段名提示]

对给定表基址：
  1. 全镜像立即数 xref 找出所有引用它的函数
  2. 符号追踪（shl/lea/imul/add/sub/mov）找出「const == base」的寄存器
     ⇒ 这些寄存器持有指向该表的指针
  3. 扫描这些寄存器作为内存基址的所有 [reg + disp] 访问
  4. 按 disp 汇总：读/写次数、访问宽度、所在函数

产出：字段使用直方图 + 每个 disp 的调用点样例 ⇒ 用于给未命名字段定名。
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
from collections import defaultdict

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
CODE_LO, CODE_HI = 0x400000, 0x600000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE

# 8/16 位子寄存器 -> 32 位父寄存器
FAM = {}
for lo, hi in (('ax','eax'),('bx','ebx'),('cx','ecx'),('dx','edx'),('si','esi'),
               ('di','edi'),('bp','ebp'),('sp','esp')):
    FAM[lo] = {lo, hi}; FAM[hi] = {lo, hi}
def isfam(a, b): return a == b or a in FAM.get(b, set()) or b in FAM.get(a, set())

# 写操作助记符
WRITES = {'mov','movzx','movsx','add','sub','or','and','xor','inc','dec','shl','shr','imul','lea'}


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


def width_of(op):
    """从操作数大小猜访问宽度（粗判）"""
    return op.size if op.size else 4


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 1
    tbl = int(sys.argv[1], 16)
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
    print(f"表 {tbl:#x}: {len(sites)} 个函数引用")

    # 2+3) 符号追踪找指针寄存器，收集 [reg+disp]
    fields = defaultdict(lambda: dict(read=0, write=0, widths=set(), sites=[]))
    for fn in sorted(sites):
        nxt = fn_next[fn]
        if nxt - fn > 0x800: nxt = fn + 0x800
        state = {}   # reg -> (coeff, const)

        def st(r):
            return list(state[r]) if r in state else [1, 0]

        for ins in disasm_fn(fn, nxt - fn):
            m, ops = ins.mnemonic, ins.operands
            # 先记录访问：任何以「持有表指针的寄存器」为基址的内存操作数
            for o in ins.operands:
                if o.type == CS_OP_MEM and o.mem.base and o.mem.index == 0:
                    b = md.reg_name(o.mem.base)
                    if b in state and state[b][1] == tbl:
                        disp = o.mem.disp
                        is_w = (m in ('mov','movzx','movsx','add','sub','or','and','xor',
                                      'inc','dec','shl','shr','imul')
                                and ops and ops[0].type == CS_OP_MEM) or m == 'mov' and ops and ops[0].type == CS_OP_MEM
                        f = fields[disp]
                        if is_w: f['write'] += 1
                        else: f['read'] += 1
                        f['widths'].add(width_of(o))
                        if len(f['sites']) < 4:
                            f['sites'].append((ins.address, m, ins.op_str))
            # 更新符号状态
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

    print(f"\n=== 字段访问图（disp: 读/写, 宽度）===")
    for disp in sorted(fields):
        f = fields[disp]
        w = '/'.join(str(x) for x in sorted(f['widths']))
        print(f"  +{disp:#05x} ({disp:3d})  读{f['read']:4d} 写{f['write']:4d}  w={w:5s}  "
              f"{f['sites'][0][0]:#x}: {f['sites'][0][1]} {f['sites'][0][2]}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
