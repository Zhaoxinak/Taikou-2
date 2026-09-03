# -*- coding: utf-8 -*-
"""续227: 对齐反汇编全局 ctor 区 0x48c3b0..0x48c4c0，定位 push 0x5152d0 后的调用目标（map 填充函数），并追其源表。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all, load_image, BASE

MEM = load_image()
def va2off(va): return va - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False

print("===== 0x48c3b0..0x48c4c0 (全局 ctor, 含 push 0x5152d0) =====")
for ins in disasm_all(md, MEM[va2off(0x48c3b0):va2off(0x48c4c0)], 0x48c3b0):
    mark = "   <== 加载/填充 map 0x5152d0" if "5152d0" in ins.op_str else ""
    print(f"  {ins.address:#010x}  {ins.bytes.hex():20s} {ins.mnemonic} {ins.op_str}{mark}")
