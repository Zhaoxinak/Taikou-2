# -*- coding: utf-8 -*-
"""太阁2 — 可靠 raw-capstone 线性反汇编器（从已知函数起点 disasm 到 ret 或上限）。
用法：
  python _dis_raw.py 0x45e700            # 从 0x45e700 线性 disasm 到 ret（最多 400 条）
  python _dis_raw.py 0x45e700 0x45e800   # 固定 VA 区间
  python _dis_raw.py 0x45e700 60         # 指定最大指令数
依赖：capstone（from capstone.x86 import *）
"""
import sys, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
SZ = len(MEM)

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def va_to_off(va):
    return va - BASE

def disasm_range(va_start, va_stop=None, max_ins=400):
    off = va_to_off(va_start)
    if off < 0 or off >= SZ:
        print("va out of range: %#x" % va_start); return
    code = MEM[off:]
    out = []
    n = 0
    for ins in md.disasm(code, va_start):
        out.append((ins.address, ins.bytes, ins.mnemonic, ins.op_str))
        n += 1
        if va_stop and ins.address >= va_stop:
            break
        if ins.mnemonic == "ret" or ins.mnemonic == "retf":
            break
        if n >= max_ins:
            break
    for addr, b, m, o in out:
        bs = " ".join("%02x" % x for x in b)
        print("%08x  %-18s %-9s %s" % (addr, bs, m, o))
    print("--- %d instrs ---" % n)

if __name__ == "__main__":
    a = sys.argv[1]
    va_start = int(a, 16) if a.lower().startswith("0x") else int(a)
    va_stop = None
    max_ins = 400
    if len(sys.argv) > 2:
        b = sys.argv[2]
        if b.lower().startswith("0x"):
            va_stop = int(b, 16)
        else:
            max_ins = int(b)
    if len(sys.argv) > 3:
        max_ins = int(sys.argv[3])
    disasm_range(va_start, va_stop, max_ins)
