#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在脱壳 EXE 中定位 "TAIKOU2_SCENARIO" 引用，反汇编 SNDATA 读取代码以权威映射字段。"""
import os, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM="F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
mem=open(MEM,'rb').read()
base=0x400000

sig=b"TAIKOU2_SCENARIO"
idx=mem.find(sig)
assert idx>=0, "signature not found"
va=base+idx
print(f"'TAIKOU2_SCENARIO' 文件偏移=0x{idx:x}  VA=0x{va:08x}")

# 搜索代码中对 VA 的引用: lea reg,[VA] / mov reg,VA / push VA 等
# 常见编码: lea eax,[0x4xxxxx] -> 8d 05 <4字节LE VA> (if [disp32]) 或 8d 80/81...
# 也尝试直接搜 4字节LE(VA) 和可能的 2字节节区相对
target_le=struct.pack("<I", va)
hits=[]
pos=0
while True:
    p=mem.find(target_le, pos)
    if p<0: break
    hits.append(p)
    pos=p+1
print(f"直接 4字节LE(VA) 命中: {len(hits)} 处")
for h in hits[:12]:
    print(f"  偏移 0x{h:x} (VA 0x{base+h:08x})")

# 反汇编每个命中周围
md=Cs(CS_ARCH_X86, CS_MODE_32)
md.detail=True
def disasm_around(off, before=64, after=256):
    start=max(0, off-before)
    code=mem[start:off+after]
    print(f"\n--- disasm @ file 0x{off:x} (VA 0x{base+off:08x}), showing -{before}/+{after} ---")
    for ins in md.disasm(code, base+start):
        mark=" >>>" if ins.address==base+off else "    "
        print(f"  0x{ins.address:08x}{mark} {ins.mnemonic} {ins.op_str}")

for h in hits[:6]:
    disasm_around(h)

# 也搜 "SCENARIO" 子串引用 (可能只引用后半部分)
print("\n=== 也尝试搜 'SCENARIO' 0xSCENARIO 相关 ===")
for sub in [b"SCENARIO", b"SCEN"]:
    s=mem.find(sub)
    if s>=0:
        print(f"  '{sub.decode()}' @ 0x{s:x}")
