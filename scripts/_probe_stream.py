#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_stream.py -- 续229 step(A) 探针2：
   反汇编流读取原语 0x47da10(读字节)/0x47da50(读字)/0x4411b0(批量读) 与守卫 0x47f5b0，
   判定 scenario object(ecx) 的流布局：源指针在哪、如何前进、[ecx+0x8c] 语义。
"""
import os
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dis(va, n):
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))

def show(title, va, n, lines=36):
    print('=' * 72)
    print(f'{title}  @0x{va:06x}')
    print('=' * 72)
    for i in dis(va, n)[:lines]:
        print(f'  0x{i.address:06x}  {i.mnemonic} {i.op_str}')

for va, nm in (
    (0x47da10, 'READ_BYTE  (0x47d910 SET_BYTE_GLOBAL 内部调用)'),
    (0x47da50, 'READ_WORD  (0x47d930 SET_WORD_GLOBAL 内部调用)'),
    (0x4411b0, 'BULK_READ  (0x47f350 prologue 调用, ecx=stream)'),
    (0x47f5b0, 'GUARD      (0x47f350 守卫, 头部校验失败返)'),
    (0x47d9b0, 'FLUSH?     (SET_BYTE_OBJ 计数满 0x2000 调用)'),
):
    show(nm, va, 0x120, lines=44)
