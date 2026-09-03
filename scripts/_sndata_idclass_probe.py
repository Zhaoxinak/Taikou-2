#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续227-下一步(B): 数据侧取 id->class。
1) 反汇编 0x462fd0 全函数：弄清它向 map 查什么、返回什么(class 还是 name_base)。
2) 反汇编 find 包装链 0x4787c0/0x47be00/0x47bed0。
3) 全镜像扫描 map 对象 0x5152d0 的立即数引用(xref)，定位 map 的填充/插入代码。
4) 反汇编加载器 0x46e2ea / 0x46e2a5 / 0x46e260 / 0x462460(入队)。
"""
import struct, sys

BASE = 0x400000
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"

with open(IMG, "rb") as f:
    MEM = f.read()
assert len(MEM) == 2 * 1024 * 1024, len(MEM)

def va2off(va):
    return va - BASE

def disasm_at(va, nbytes, maxins=400):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    off = va2off(va)
    data = MEM[off:off+nbytes]
    out = []
    for ins in md.disasm(data, va):
        out.append(ins)
        if len(out) >= maxins:
            break
    return out

def dump(va, nbytes, label):
    print("="*72)
    print(f"{label}: {va:#08x} (+{nbytes} bytes)")
    print("="*72)
    for ins in disasm_at(va, nbytes):
        print(f"{ins.address:#08x}  {ins.mnemonic} {ins.op_str}")
    print()

def scan_xref_imm(imm_le):
    """扫描全代码段所有 4 字节立即数 == imm_le (little-endian)。返回 (va, 上下文字节)。"""
    pat = struct.pack("<I", imm_le)
    hits = []
    # 代码段大致 0x401000..0x4fxxxx；直接全镜像扫立即数（含数据，标记即可）
    start = va2off(0x401000)
    end   = len(MEM) - 4
    i = MEM.find(pat, start)
    while i != -1 and i < end:
        va = i + BASE
        hits.append(va)
        i = MEM.find(pat, i + 1)
    return hits

# ---------- 1) 0x462fd0 全函数 ----------
dump(0x462fd0, 0x200, "0x462fd0 (六类解析器 entry)")

# ---------- 2) find 包装链 ----------
dump(0x4787c0, 0x120, "0x4787c0 (map.find wrapper?)")
dump(0x47be00, 0x120, "0x47be00")
dump(0x47bed0, 0x120, "0x47bed0")

# ---------- 3) map 对象 0x5152d0 xref ----------
print("="*72)
print("xref scan: map object 0x5152d0 (4-byte imm)")
print("="*72)
hits = scan_xref_imm(0x5152d0)
print(f"hits = {len(hits)}")
for h in hits:
    # 反汇编命中点周围，看是 mov ecx,0x5152d0 (thiscall this) 还是 lea/算术
    print(f"  {h:#08x}")

# 同时也扫 0x5152d0 附近的偏移访问: 0x5152d0..0x5152e0
print()
print("xref scan: 0x5152d4 / 0x5152d8 (可能存 size 或别的)")
for off in (0x5152d4, 0x5152d8, 0x5152dc, 0x5152e0):
    h2 = scan_xref_imm(off)
    print(f"  0x{off:#x}: {len(h2)} hits -> {[hex(x) for x in h2[:12]]}")

# ---------- 4) 加载器 ----------
dump(0x46e2ea, 0x200, "0x46e2ea (SNDATA 加载器?)")
dump(0x46e2a5, 0x120, "0x46e2a5 (caller of 0x4624f0)")
dump(0x46e260, 0x160, "0x46e260 (事件派发 0x7dc)")
dump(0x462460, 0x120, "0x462460 (队列入口 enqueue)")
