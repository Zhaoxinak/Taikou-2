#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_f350.py -- 续229 step(A) 可行性探针：
   反汇编 0x47f350 主解码器 prologue + 4 个 setter（0x47d910/0x47d930/0x47da80/0x47dac0），
   判定 (1) 0x47f350 形参/前置条件 (2) setter 源字节从哪来（全局记录指针? 入参缓冲?），
   从而决定能否直接 emu 0x47f350 抓 payload 字节 -> 游戏表 字段映射。
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

def show(title, va, n, lines=40):
    print('=' * 72)
    print(f'{title}  @0x{va:06x}  (len={n:#x})')
    print('=' * 72)
    for i in dis(va, n)[:lines]:
        print(f'  0x{i.address:06x}  {i.mnemonic} {i.op_str}')

# 1) 0x47f350 prologue：看形参约定（stdcall? thiscall? 参数来源）
show('0x47f350  MAIN DECODER prologue', 0x47f350, 0x180, lines=70)

# 2) 四个 setter：看源字节读取方式
for va, nm in ((0x47d910,'SET_BYTE_GLOBAL'), (0x47d930,'SET_WORD_GLOBAL'),
               (0x47da80,'SET_BYTE_OBJ'),    (0x47dac0,'SET_WORD_OBJ')):
    show(nm, va, 0x80, lines=24)

# 3) 谁调用 0x47f350（派生源，判断可否 standalone 调）
print('=' * 72)
print('xref -> 0x47f350 (call 0x47f350 / jmp 0x47f350)')
print('=' * 72)
cnt = 0
va = BASE
while va < 0x5A0000:
    for i in md.disasm(MEM[va - BASE: va - BASE + 0x2000], va):
        if i.mnemonic in ('call', 'jmp') and '0x47f350' in i.op_str:
            print(f'  0x{i.address:06x}  {i.mnemonic} {i.op_str}')
            cnt += 1
    va += 0x2000
print(f'  total xrefs = {cnt}')
