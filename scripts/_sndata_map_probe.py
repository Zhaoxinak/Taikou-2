# -*- coding: utf-8 -*-
"""续227: 反汇编 std::map 机制 0x4787c0 / 0x4eefa0，以及疑似填充点 0x48c3b7 / 0x478b41。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all, load_image, BASE

MEM = load_image()
def va2off(va): return va - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False

def disasm(va, end, label):
    print(f"===== {label} (0x{va:x}..0x{end:x}) =====")
    for ins in disasm_all(md, MEM[va2off(va):va2off(end)], va):
        print(f"  {ins.address:#010x}  {ins.bytes.hex():20s} {ins.mnemonic} {ins.op_str}")
    print()

disasm(0x4787c0, 0x478860, "0x4787c0 (0x47be00 内调用1)")
disasm(0x4eefa0, 0x4eef80+0x80, "0x4eefa0 (0x47be00 内调用2)")
disasm(0x48c3b7, 0x48c4a0, "0x48c3b7 (疑似 map 填充点)")
disasm(0x478b41, 0x478bc0, "0x478b41 (xref 2)")
