#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反汇编整个脱壳 EXE，筛选引用 0x522c88 区 或 调用 0x47fc60 的指令，定位 SNDATA 实体结构字段消费者。"""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
mem = open(MEM, "rb").read()
base = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)

# 只扫代码区（估 0x401000..0x4f44b0），逐段反汇编
START, END = 0x401000, 0x4f44b0
out = []
for seg in range(START, END, 0x1000):
    code = mem[seg-base:seg-base+0x1000]
    if not code:
        break
    for ins in md.disasm(code, seg):
        if ins.address > END:
            break
        s = f"{ins.address:08x}  {ins.mnemonic} {ins.op_str}"
        if "522c" in s or "call 0x47fc60" in s or "call 0x47fd10" in s:
            out.append(s)

with open("F:/Games/Taikou 2/scripts/_sndata_consumers.asm", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print(f"matched {len(out)} instructions -> _sndata_consumers.asm")
