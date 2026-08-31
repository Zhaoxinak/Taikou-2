# -*- coding: utf-8 -*-
"""续165 探索②：dump 0x480000 区域（3 视图缓冲作为实参传入的函数），找调用方与对视图的逐字节读。"""
import os
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def dis(va, n):
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))


def show(va, n, label):
    print(f'===== {label} @0x{va:06x} =====')
    for i in dis(va, n):
        print(f'  0x{i.address:06x}  {i.mnemonic} {i.op_str}')
    print()


if __name__ == '__main__':
    show(0x480000, 0x200, '0x480000 region (3 views passed as args)')
