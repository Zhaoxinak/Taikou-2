#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
MEM="F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
mem=open(MEM,'rb').read()
base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)

def disasm(va, size):
    off=va-base
    return [(i.address,i.mnemonic,i.op_str) for i in md.disasm(mem[off:off+size], va)]

print("="*72)
print("0x47f5b0 SNDATA 记录解包函数 (在 49B 读入 0x519640 之后)")
print("="*72)
for addr,mn,op in disasm(0x47f5b0, 400):
    mark=""
    # 标记涉及 0x519640 或 ecx 写入的指令
    if "519640" in op: mark=" <== RECORD SRC"
    if re.search(r'mov .*\[ecx \+ 0x', op): mark+=" <== OBJ WRITE"
    print(f"0x{addr:08x}  {mn} {op}{mark}")

# 抓取 "mov [ecx+0xOBJ], <reg>" 后跟从 0x519640 读取的配对
print("\n\n=== 推断 record_byte(0x519640+K) -> object[0xOBJ] 配对 ===")
asm=disasm(0x47f5b0, 600)
src_reg=None
for addr,mn,op in asm:
    # 找从 0x519640(或等价)读
    m=re.search(r'mov (e[a-z]x|al|ax|cl|cx), (byte|word) ptr \[(e[a-z]+|0x519640)\s*(\+ 0x([0-9a-f]+))?\]', op)
    if m:
        print(f"  READ  @0x{addr:08x}: {mn} {op}")
    m2=re.search(r'mov (byte |word )?ptr \[ecx \+ 0x([0-9a-f]+)\], (e[a-z]x|al|ax|cl|cx)', op)
    if m2:
        print(f"  WRITE @0x{addr:08x}: obj_off=0x{int(m2.group(2),16):x} <- {m2.group(3)}")
