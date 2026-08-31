# -*- coding: utf-8 -*-
"""续164 探索②：dump 0x47fb80（看把 3 个记录缓冲传给哪个子函数）与 0x47fc60（看读记录的
哪些偏移 → 头 schema）。"""
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
    print(f'===== {label} @0x{va:06x} (len {n}) =====')
    for i in dis(va, n):
        print(f'  0x{i.address:06x}  {i.mnemonic} {i.op_str}')
    print()


if __name__ == '__main__':
    # 谓词：把 3 缓冲传给谁
    show(0x47FB80, 0x160, '0x47fb80 predicate (find callee of 0x522c..)')
    # 扇出：读记录哪些偏移
    show(0x47FC60, 0x140, '0x47fc60 fanout (record offset reads)')
