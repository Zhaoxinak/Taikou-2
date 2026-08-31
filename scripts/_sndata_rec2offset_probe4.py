# -*- coding: utf-8 -*-
"""续163 探索④：精确认证 5 个寄存器派生基址站点（base = 调用前最后一个非 4 的 push 操作数），
并 dump 上下文看 base 是否来自记录缓冲/参数。"""
import os
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

SITES = [0x43379d, 0x47d741, 0x47d7d4, 0x47d821, 0x47fab9]


def dis(va, n):
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))


def show(va, n, label):
    print(f'===== {label} @0x{va:06x} =====')
    for i in dis(va, n):
        print(f'  0x{i.address:06x}  {i.mnemonic} {i.op_str}')
    print()


for s in SITES:
    show(s - 0x50, 0x70, f'site 0x{s:06x}')
