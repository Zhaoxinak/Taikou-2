#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续227-下一步(B) 续: 定位 map @0x5152d0 的 insert/填充代码。
1) 反汇编 map 方法簇 0x478770..0x479100 枚举方法(ctor/find/insert/erase/begin/end)。
2) 扫描全镜像 xref 到 0x478990(内部树操作, find/insert 共用) -> 找 insert 调用者。
3) 扫描 xref 到 0x478a20(0x47be00 内调用的另一 map op) 与 0x478770(ctor)。
"""
import struct
BASE = 0x400000
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"
with open(IMG, "rb") as f:
    MEM = f.read()

def va2off(va): return va - BASE
def disasm_at(va, nbytes):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
    return list(md.disasm(MEM[va2off(va):va2off(va)+nbytes], va))

def dump(va, nbytes, label):
    print("="*72); print(f"{label}: {va:#08x} (+{nbytes})"); print("="*72)
    for ins in disasm_at(va, nbytes):
        print(f"{ins.address:#08x}  {ins.mnemonic} {ins.op_str}")
    print()

def scan_xref_imm(imm):
    pat = struct.pack("<I", imm)
    hits=[]; i=MEM.find(pat, va2off(0x401000))
    while i!=-1 and i < len(MEM)-4:
        hits.append(i+BASE); i=MEM.find(pat, i+1)
    return hits

# 1) map 方法簇
dump(0x478770, 0x3a0, "map method cluster 0x478770..0x478b10")

# 2) xref to internal ops
print("="*72); print("xref scan: 0x478990 (internal tree op)"); print("="*72)
for h in scan_xref_imm(0x478990):
    print(f"  {h:#08x}")
print()
print("xref scan: 0x478a20 (map op in 0x47be00)"); 
for h in scan_xref_imm(0x478a20):
    print(f"  {h:#08x}")
print()
print("xref scan: 0x478770 (map ctor)")
for h in scan_xref_imm(0x478770):
    print(f"  {h:#08x}")
print()
print("xref scan: 0x4787c0 (map.find wrapper)")
for h in scan_xref_imm(0x4787c0):
    print(f"  {h:#08x}")
