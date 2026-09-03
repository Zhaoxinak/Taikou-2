#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续227-下一步(B) 续4: 反汇编 0x4789d0(值计算/insert 值) + 0x49f6b0(当前记录ptr getter)
+ 0x49f5e0(实体 getter) + 0x49f430 + 0x49f610, 以设计 emu 桩。
"""
import struct
BASE = 0x400000
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"
with open(IMG, "rb") as f:
    MEM = f.read()
def va2off(va): return va - BASE
def disasm_at(va, nbytes):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=False
    return list(md.disasm(MEM[va2off(va):va2off(va)+nbytes], va))
def dump(va, nbytes, label):
    print("="*72); print(f"{label}: {va:#08x}"); print("="*72)
    for ins in disasm_at(va, nbytes):
        print(f"{ins.address:#08x}  {ins.mnemonic} {ins.op_str}")
    print()

dump(0x4789d0, 0x120, "0x4789d0 (find-or-insert value computer)")
dump(0x49f6b0, 0x60,  "0x49f6b0 (current record ptr getter)")
dump(0x49f5e0, 0x60,  "0x49f5e0 (entity getter)")
dump(0x49f430, 0x60,  "0x49f430 (callee in 0x46e2ea)")
dump(0x49f610, 0x60,  "0x49f610 (callee in 0x4630c0)")
