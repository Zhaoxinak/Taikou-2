# -*- coding: utf-8 -*-
"""续227: 反汇编 0x4624f0（SNDATA 每记录处理器，0x462fd0 的调用者），定位权威 id->class 逻辑。
同时全镜像扫 call 0x462fd0 的所有调用方。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all, load_image, BASE

MEM = load_image()
def va2off(va): return va - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False

print("===== 0x4624f0..0x462fd0 (SNDATA 每记录处理器) =====")
for ins in disasm_all(md, MEM[va2off(0x4624f0):va2off(0x462fd0)], 0x4624f0):
    print(f"  {ins.address:#010x}  {ins.bytes.hex():20s} {ins.mnemonic} {ins.op_str}")
