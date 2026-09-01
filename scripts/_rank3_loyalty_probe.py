# -*- coding: utf-8 -*-
"""_rank3_loyalty_probe.py
探测 +0x2d 低3位(身分码) 与 +0x29(忠诚) 的消费方式：
  - +0x2d 是否被 `and reg,7` 后喂入 跳转表(jmp [reg*scale+table]) → 身分码语义
  - +0x29 是否被 `cmp` 到常量阈值 → 忠诚阈值语义
全镜像扫描（不限实体引用函数）。
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

def disasm_fn(va, nxt):
    end = min(nxt, va + 0x800)
    cur = va; out = []
    while cur < end:
        chunk = MEM[off(cur):off(end)]
        got = list(md.disasm(chunk, cur))
        if not got: cur += 1; continue
        for ins in got:
            if ins.address >= end: break
            out.append(ins)
        last = out[-1]; nxt2 = last.address + last.size
        cur = nxt2 if nxt2 > cur else cur + 1
    return out

def reg_name(rid):
    return md.reg_name(rid) if rid else ''

def main():
    fl, fn_next = build_fn_bounds()
    # 收集：
    #  (A) 读 byte[base+0x2d] 或 byte[base+0x29] 的指令，及其目标寄存器
    #  (B) and reg,7 / and reg,0x7
    #  (C) cmp 到 +0x29 的常量比较
    #  (D) 跳转表 jmp [reg*scale+disp]
    rank3_loads = []   # (fn, addr, dst_reg_str, size_byte)
    loyalty_cmp = []   # (fn, addr, op_str, imm)
    d29_any = []       # 任何对 +0x2d 的访问(读/写)
    d29_spec = []      # +0x2d 被 and 7 后接跳转表
    jmptab = []        # (fn, addr, table_va, idx_reg, scale)

    for fn in fl:
        nxt = fn_next[fn]
        insns = disasm_fn(fn, nxt)
        # 先建 读+0x2d / +0x29 的映射： 该寄存器在后续 and 7
        for idx, ins in enumerate(insns):
            # 内存操作数
            for o in ins.operands:
                if o.type == CS_OP_MEM and o.mem.base and o.mem.index == 0:
                    d = o.mem.disp & 0xfff
                    if d in (0x2d, 0x29):
                        # 记录访问
                        if ins.mnemonic in ('mov','movzx') and ins.operands[0].type == CS_OP_REG:
                            dst = reg_name(ins.operands[0].reg)
                            if d == 0x2d:
                                rank3_loads.append((fn, ins.address, dst))
                            # 读动作登记
                        # cmp 比较 +0x29
                        if d == 0x29 and ins.mnemonic == 'cmp':
                            imm = None
                            for o2 in ins.operands:
                                if o2.type == CS_OP_IMM: imm = o2.imm & 0xff
                            loyalty_cmp.append((fn, ins.address, ins.op_str, imm))
                        d29_any.append((fn, ins.address, ins.mnemonic, ins.op_str, d))
            # and reg, 7 ?
            if ins.mnemonic == 'and' and len(ins.operands) == 2:
                op0 = ins.operands[0]; op1 = ins.operands[1]
                if op0.type == CS_OP_REG and op1.type == CS_OP_IMM and (op1.imm & 0xff) == 7:
                    r = reg_name(op0.reg)
                    # 前几条是否刚从 +0x2d 载入
                    for j in range(max(0,idx-4), idx):
                        p = insns[j]
                        for o in p.operands:
                            if o.type == CS_OP_MEM and o.mem.disp & 0xfff == 0x2d and \
                               p.mnemonic in ('mov','movzx') and p.operands[0].type==CS_OP_REG and \
                               reg_name(p.operands[0].reg)==r:
                                d29_spec.append((fn, ins.address, r, p.address))
            # 跳转表: jmp [reg*scale+disp]
            if ins.mnemonic in ('jmp',) and len(ins.operands) == 1:
                o = ins.operands[0]
                if o.type == CS_OP_MEM and o.mem.index and o.mem.disp:
                    tbl = o.mem.disp & 0xffffffff
                    idx_reg = reg_name(o.mem.index)
                    scale = o.mem.scale
                    jmptab.append((fn, ins.address, tbl, idx_reg, scale))

    print(f"=== +0x2d 低3位相关 ===")
    print(f"读 +0x2d → reg 的载入点: {len(rank3_loads)}")
    # 打印 and 7 点（已追溯来源为 +0x2d）
    print(f"\n--- 载入+0x2d 后 and 7 的点 ({len(d29_spec)}) ---")
    for fn, a, r, la in sorted(d29_spec):
        print(f"  fn~0x{fn:x}: and @0x{a:x} reg={r}  (源自 0x{la:x} 读+0x2d)")

    # 对 d29_spec 的 and 点，向下找跳转表(同函数内，且 跳转表索引寄存器 == r)
    print(f"\n--- and7 后，同函数内是否存在 jmp [r*scale+table] (跳转表调度) ---")
    for fn, a, r, la in sorted(d29_spec):
        insns = disasm_fn(fn, fn_next[fn])
        for ins in insns:
            if ins.address <= a: continue
            if ins.mnemonic == 'jmp' and len(ins.operands)==1:
                o = ins.operands[0]
                if o.type == CS_OP_MEM and o.mem.index and reg_name(o.mem.index)==r:
                    tbl = o.mem.disp & 0xffffffff
                    scale = o.mem.scale
                    # 读跳转表项
                    cnt = 0; entries=[]
                    p = off(tbl)
                    while cnt < 16 and p+4 <= len(MEM):
                        t = struct.unpack('<i', MEM[p:p+4])[0] & 0xffffffff
                        entries.append(t); p+=4; cnt+=1
                    print(f"  fn~0x{fn:x} and@0x{a:x}: 发现跳转表 jmp [0x{tbl:x}] 索引={r} scale={scale}")
                    for kk,tt in enumerate(entries):
                        print(f"       case {kk}: 0x{tt:x}")

    print(f"\n=== +0x29 忠诚 的 cmp 阈值比较 ({len(loyalty_cmp)}) ===")
    seen=set()
    for fn, a, ops, imm in sorted(loyalty_cmp):
        key=(a,imm)
        if key in seen: continue
        seen.add(key)
        print(f"  0x{a:x} ({fn:#x}): cmp {ops}   imm={imm}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
