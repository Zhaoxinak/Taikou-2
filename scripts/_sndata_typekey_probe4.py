# -*- coding: utf-8 -*-
"""续227 验证：反汇编 0x462fd0 全函数 + 0x47bed0 剩余 + 0x47be00 真二分。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all, load_image, BASE

MEM = load_image()

def va2off(va):
    return va - BASE

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

print("===== 0x462fd0 全函数 (0x462fd0..0x463090) =====")
data = MEM[va2off(0x462fd0):va2off(0x463090)]
for ins in disasm_all(md, data, 0x462fd0):
    print(f"  {ins.address:#010x}  {ins.bytes.hex():20s} {ins.mnemonic} {ins.op_str}")

print()
print("===== 0x47bed0 剩余 (0x47bf1f..0x47bf80) =====")
data = MEM[va2off(0x47bf1f):va2off(0x47bf80)]
for ins in disasm_all(md, data, 0x47bf1f):
    print(f"  {ins.address:#010x}  {ins.bytes.hex():20s} {ins.mnemonic} {ins.op_str}")

print()
print("===== 0x47be00 真二分 (0x47be00..0x47bed0) =====")
data = MEM[va2off(0x47be00):va2off(0x47bed0)]
for ins in disasm_all(md, data, 0x47be00):
    print(f"  {ins.address:#010x}  {ins.bytes.hex():20s} {ins.mnemonic} {ins.op_str}")
