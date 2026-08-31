#!/usr/bin/env python3
# 关系值写入定位：在整个映像中追踪「某寄存器被载入 0x5179b8 基址」的污点，
# 然后检测该寄存器（或其派生）是否参与对 [reg + disp] 的写，disp ∈ {0xb,0xc,0xd}
# （即国政治表 stride14 的关系属性字段）。按 16KB 分块并逐块 try/except，避免 capstone 崩溃。
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
def off(v): return v - BASE

TARGET = 0x5179b8
REL_DISPS = tuple(range(0, 0x21))  # 接受 base+0..+0x20 的写，再人工筛 +0xb/+0xc/+0xd
CHUNK = 0x4000
CODE_LO, CODE_HI = 0x400000, 0x600000

def reg_name(md, rid):
    return md.reg_name(rid) if rid else None

def scan():
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
    results = []
    taint = {}   # reg_id -> instr_index when tainted (from 0x5179b8 base load)
    idx = 0
    pos = CODE_LO
    while pos < CODE_HI:
        seg_hi = min(pos + CHUNK, CODE_HI)
        code = MEM[off(pos):off(seg_hi)]
        try:
            insns = list(md.disasm(code, pos))
        except Exception as e:
            pos = seg_hi
            continue
        for ins in insns:
            mnem = ins.mnemonic
            ops = ins.operands
            # 污点建立：add reg, 0x5179b8 / mov reg, 0x5179b8 / lea reg, [...+0x5179b8]
            if len(ops) == 2 and ops[0].type == CS_OP_REG:
                if mnem in ('add', 'mov') and ops[1].type == CS_OP_IMM and (ops[1].imm & 0xffffffff) == TARGET:
                    taint[ops[0].reg] = idx
                if mnem == 'lea' and ops[1].type == CS_OP_MEM and (ops[1].mem.disp & 0xffffffff) == TARGET:
                    taint[ops[0].reg] = idx
            # 写关系字段： mov/and/or/xor/add/sub [reg(+disp)], ... 且 reg 被污点
            if mnem in ('mov', 'add', 'sub', 'and', 'or', 'xor', 'inc', 'dec') and len(ops) >= 2:
                o0 = ops[0]
                if o0.type == CS_OP_MEM:
                    base = o0.mem.base
                    disp = o0.mem.disp
                    if base in taint and (disp & 0xffffffff) in REL_DISPS:
                        # 确认 base 仍是该污点（未被最近的非派生写覆盖）
                        results.append((ins.address, mnem, ins.op_str, md.reg_name(base), disp & 0xffffffff, taint.get(base)))
            # 污点清除：reg 被立即数（非基址）或普通 lea 覆盖
            if len(ops) >= 1 and ops[0].type == CS_OP_REG:
                dst = ops[0].reg
                if mnem == 'mov' and len(ops) == 2 and ops[1].type == CS_OP_IMM and (ops[1].imm & 0xffffffff) != TARGET:
                    taint.pop(dst, None)
                elif mnem == 'lea' and len(ops) == 2 and ops[1].type == CS_OP_MEM and (ops[1].mem.disp & 0xffffffff) != TARGET:
                    taint.pop(dst, None)
            idx += 1
        pos = seg_hi
    return results

if __name__ == '__main__':
    res = scan()
    print(f"候选关系字段写入: {len(res)}")
    for addr, mnem, opstr, rbase, disp, t in res:
        print(f"  @{addr:#010x}  {mnem} {opstr}   (base={rbase}, field+{disp:#x})")
