#!/usr/bin/env python3
# 整段线性反汇编 + 逐指令检查 mem/imm 操作数，定位对目标全局地址的 读/写/取地址 引用。
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()

def off(v): return v - BASE

CODE_LO, CODE_HI = 0x400000, 0x600000

def scan(va, lo=CODE_LO, hi=CODE_HI, chunk=0x10000):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
    reads, writes, leas, imms = [], [], [], []
    # 整段扫描按 64KB 分块（capstone 对超大 buffer 的 disasm 生成器会空转）
    pos = lo
    while pos < hi:
        seg_hi = min(pos + chunk, hi)
        code = MEM[off(pos):off(seg_hi)]
        for ins in md.disasm(code, pos):
            a = ins.address
        mnem = ins.mnemonic
        for op in ins.operands:
            if op.type == CS_OP_MEM:
                base = op.mem.base
                disp = op.mem.disp
                # 绝对地址形式：base/index 为 None（capstone 对绝对寻址报 None 而非 0），disp==va
                if base in (0, None) and op.mem.index in (0, None) and (disp & 0xffffffff) == va:
                    if mnem == 'lea':
                        leas.append(a)
                    elif len(ins.operands) >= 2 and ins.operands[0].type == CS_OP_MEM:
                        writes.append(a)
                    elif len(ins.operands) >= 2 and ins.operands[1].type == CS_OP_MEM:
                        reads.append(a)
                    else:
                        reads.append(a)
            if op.type == CS_OP_IMM and (op.imm & 0xffffffff) == va:
                imms.append(a)
    return reads, writes, leas, imms

if __name__ == '__main__':
    import sys
    targets = [int(x, 16) for x in sys.argv[1:]] if len(sys.argv) > 1 else [0x525ea4]
    for tgt in targets:
        r, w, l, i = scan(tgt)
        print(f"=== 0x{tgt:08x} ===")
        print(f"  READ ({len(r)}):  " + ", ".join(f"{x:#010x}" for x in r))
        print(f"  WRITE({len(w)}):  " + ", ".join(f"{x:#010x}" for x in w))
        print(f"  LEA  ({len(l)}):  " + ", ".join(f"{x:#010x}" for x in l))
        print(f"  IMM  ({len(i)}):  " + ", ".join(f"{x:#010x}" for x in i))
