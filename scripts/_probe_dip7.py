# -*- coding: utf-8 -*-
"""
_probe_dip7.py —
  A) 反汇编 0x49fd60（外交関係 8 级取值）
  B) 0x51dc60 的两处引用 0x47f056 / 0x47f076 所属函数 —— ★关系写入端
  C) dump 0x503e68 / 0x503e78 字表
"""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def rd(va, n):
    o = va - BASE
    return MEM[o:o + n] if 0 <= o else b""


def word(va):
    return struct.unpack("<H", rd(va, 2))[0]


def dis(va, maxins=140):
    o = va - BASE
    out = []
    for ins in md.disasm(MEM[o:o + maxins * 8], va):
        out.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        if len(out) >= maxins or ins.mnemonic == "ret":
            break
    return "\n".join(out)


def func_start(va):
    o = va - BASE
    lim = max(0, o - 0x600)
    i = o
    while i > lim:
        b = MEM[i]
        if b == 0xC3:
            return BASE + i + 1
        if b == 0xC2 and i + 2 < SZ:
            return BASE + i + 3
        i -= 1
    return BASE + lim


print("=" * 78)
print("### A) 0x49fd60 —— 外交関係 8 级取值")
print("=" * 78)
print(dis(0x49FD60, 140))

print()
print("=" * 78)
print("### C) 颜色/属性字表")
print("=" * 78)
for base, n, nm in [(0x503E68, 8, "外交8级"), (0x503E78, 4, "主从4级")]:
    print(f"  {nm} {base:#x}: " +
          ", ".join(f"[{i}]={word(base + i*2):#06x}" for i in range(n)))

print()
print("=" * 78)
print("### B) 关系矩阵写入端 (0x47f056 / 0x47f076)")
print("=" * 78)
fs = func_start(0x47F056)
print(f"  函数入口 {fs:#x}")
print(dis(fs, 160))
