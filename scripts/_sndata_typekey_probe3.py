# -*- coding: utf-8 -*-
"""续227 验证：反汇编 0x462fd0 尾部 + 0x47bed0 二分搜索，确认 EAX@0x4630b7 = class。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all, load_image, BASE

MEM = load_image()
N = len(MEM)

def va2off(va):
    return va - BASE

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

print("===== 0x462fd0 尾部 (0x463050..0x4630c0) =====")
data = MEM[va2off(0x463050):va2off(0x4630c0)]
for ins in disasm_all(md, data, 0x463050):
    print(f"  {ins.address:#010x}  {ins.bytes.hex():20s} {ins.mnemonic} {ins.op_str}")

print()
print("===== 0x47bed0 全函数 (0x47bed0..0x47bf20) =====")
data = MEM[va2off(0x47bed0):va2off(0x47bf20)]
for ins in disasm_all(md, data, 0x47bed0):
    print(f"  {ins.address:#010x}  {ins.bytes.hex():20s} {ins.mnemonic} {ins.op_str}")
