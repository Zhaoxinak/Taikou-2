#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续227-下一步(B) 续2: 确定 0x478a20 是 insert 还是 erase; 读 0x47be00 跳转表; 反汇编各 case。
"""
import struct
BASE = 0x400000
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"
with open(IMG, "rb") as f:
    MEM = f.read()
def va2off(va): return va - BASE
def disasm_at(va, nbytes):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=False
    return list(md.disasm(MEM[va2off(va):va2off(va)+nbytes], va))
def dump(va, nbytes, label):
    print("="*72); print(f"{label}: {va:#08x}"); print("="*72)
    for ins in disasm_at(va, nbytes):
        print(f"{ins.address:#08x}  {ins.mnemonic} {ins.op_str}")
    print()

dump(0x478a20, 0x1a0, "0x478a20 (map op called in 0x47be00)")
dump(0x478770, 0x100, "0x478770 (map ctor @0x48c3bb)")

# 读跳转表 0x47be94 (14 dword)
print("="*72); print("0x47be00 跳转表 @0x47be94 (14 entries, index = edx-0x82e)"); print("="*72)
jt_off = va2off(0x47be94)
for k in range(14):
    t = struct.unpack("<I", MEM[jt_off+k*4:jt_off+k*4+4])[0]
    print(f"  edx=0x{0x82e+k:#04x} -> {t:#08x}")

# 反汇编每个 case 目标 (它们应是 mov esi,N; jmp 0x47be72)
print()
print("跳转表 case 目标反汇编 (取 esi=class):")
seen=set()
for k in range(14):
    t = struct.unpack("<I", MEM[jt_off+k*4:jt_off+k*4+4])[0]
    if t in seen: continue
    seen.add(t)
    for ins in disasm_at(t, 0x20):
        print(f"  {ins.address:#08x}  {ins.mnemonic} {ins.op_str}")
        if ins.mnemonic=='jmp': break
