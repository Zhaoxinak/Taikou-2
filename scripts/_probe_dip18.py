# -*- coding: utf-8 -*-
"""
_probe_dip18.py — 反汇编 0x4b9250（工作完了结算主函数，跳表 0x4b9824 14 项）
"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

o = 0x4B9250 - BASE
n = 0
for ins in md.disasm(MEM[o:o + 0x5C0], 0x4B9250):
    print(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
    n += 1
    if n >= 200 or ins.mnemonic == "ret":
        break
