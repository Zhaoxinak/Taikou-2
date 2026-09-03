#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续227-下一步(B) 续3: 反汇编 0x478770(ctor?) 与全局 ctor 链 0x48c3b0..0x48c4c0,
寻找是否从静态表批量写入 map 数组(0x5152d0+0xd6, stride 12, count@+0x72)。
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

dump(0x478770, 0x200, "0x478770 (ctor? @0x48c3bb)")
dump(0x48c3b0, 0x180, "global ctor chain 0x48c3b0..0x48c530")
