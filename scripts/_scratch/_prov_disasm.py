#!/usr/bin/env python3
# 精确反汇编国政治表 LOAD(0x47e440) 与 SAVE(0x47e4e0)，并解码真实流做交叉验证。
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

BIN = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
DEC = "F:/Games/Taikou 2/scripts/_dec_SNDATA1.TR2.bin"
BASE = 0x400000

data = open(BIN, "rb").read()
def off(va): return va - BASE

cs = Cs(CS_ARCH_X86, CS_MODE_32)
cs.detail = True

def disasm(va_start, va_end, label):
    print(f"\n===== {label}: {va_start:#x} - {va_end:#x} =====")
    o = off(va_start)
    end = off(va_end)
    code = data[o:end]
    for ins in cs.disasm(code, va_start):
        # 提取目标偏移（针对 mov [esi+X]/[esi-X], ... 或 mov ..., [esi+X]）
        line = f"{ins.address:#08x}  {ins.mnemonic} {ins.op_str}"
        print(line)

# LOAD 与 SAVE 都在 0x47e440..0x47e600 区间
disasm(0x47e440, 0x47e600, "PROV LOAD/SAVE")
