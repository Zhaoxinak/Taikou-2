# -*- coding: utf-8 -*-
"""续227: 读 0x462584 跳转表(6 个 class handler)，并完整反汇编 0x4787c0(map-find)看搜索键来源。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all, load_image, BASE
import struct

MEM = load_image()
def va2off(va): return va - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False

# (1) 读跳转表 0x462584 (6 dwords)
print("===== 跳转表 @0x462584 (class 0..5 handler 地址) =====")
for i in range(6):
    off = va2off(0x462584) + i*4
    (addr,) = struct.unpack("<I", MEM[off:off+4])
    print(f"  class {i}: handler = 0x{addr:x}")

# (2) 完整反汇编 0x4787c0
print()
print("===== 0x4787c0 完整 (map-find) =====")
for ins in disasm_all(md, MEM[va2off(0x4787c0):va2off(0x4789e0)], 0x4787c0):
    # 高亮对 0x516610 / 0x516624 的引用（当前记录指针）
    mark = ""
    if "516610" in ins.op_str or "516624" in ins.op_str or "516638" in ins.op_str:
        mark = "   <== 引用全局记录区"
    print(f"  {ins.address:#010x}  {ins.bytes.hex():20s} {ins.mnemonic} {ins.op_str}{mark}")
