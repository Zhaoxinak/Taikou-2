# -*- coding: utf-8 -*-
"""
_probe_dip5.py —
  A) GBK 解码 0x5080d0 关系等级名称表 (stride 5, 12 项)
  B) 反汇编 0x49fd80 —— 关系记录查找（关系矩阵本体）
  C) 全映像搜 0x5080d0 的引用（找显示/写入侧）
  D) 验证 stride-14 魔数 0x92492493
"""
import struct, re
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


def dis(va, maxins=140):
    o = va - BASE
    out = []
    for ins in md.disasm(MEM[o:o + maxins * 8], va):
        out.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        if len(out) >= maxins or ins.mnemonic == "ret":
            break
    return "\n".join(out)


def s32(v):
    return v - (1 << 32) if v & 0x80000000 else v


print("=" * 78)
print("### A) 0x5080d0 关系等级名称表 (stride 5)")
print("=" * 78)
for i in range(14):
    va = 0x5080D0 + i * 5
    b = rd(va, 5)
    try:
        s = b.split(b"\x00")[0].decode("gbk")
    except Exception:
        s = "<err>"
    print(f"  [{i:2}] {va:#x}  {' '.join(f'{x:02x}' for x in b)}  {s!r}")

print()
print("=" * 78)
print("### D) stride 魔数验证  0x92492493 (sar 3, add edx,r)")
print("=" * 78)
M = s32(0x92492493)


def f(x):
    prod = M * x
    hi = (prod >> 32) & 0xFFFFFFFF
    v = s32((hi + x) & 0xFFFFFFFF)
    return v >> 3


for dv in range(2, 200):
    if all(f(dv * k) == k for k in range(1, 80)):
        print(f"  divisor = {dv}  (k=1..79 全对)")
        break
else:
    print("  未精确匹配; 抽样:", [(k, f(k)) for k in (14, 28, 42)])

M2 = s32(0x84210843)


def f2(x):
    prod = M2 * x
    hi = (prod >> 32) & 0xFFFFFFFF
    v = s32((hi + x) & 0xFFFFFFFF)
    return v >> 4


print("  0x84210843 (sar 4, base 0x51eb88) 抽样:",
      [(k, f2(k)) for k in (28, 31, 32, 47, 56, 62, 64)])
for dv in range(2, 400):
    if all(f2(dv * k) == k for k in range(1, 80)):
        print(f"  divisor2 = {dv}  (k=1..79 全对)")
        break

print()
print("=" * 78)
print("### B) 0x49fd80 —— 关系记录查找")
print("=" * 78)
print(dis(0x49FD80, 140))

print()
print("=" * 78)
print("### C) 0x5080d0 的引用点")
print("=" * 78)
pat = struct.pack("<I", 0x5080D0)
i = MEM.find(pat)
while i != -1:
    print(f"  at {BASE + i:#x}  (bytes {' '.join(f'{x:02x}' for x in MEM[i:i+4])})")
    i = MEM.find(pat, i + 1)
# 也扫 0x5080cc
pat2 = struct.pack("<I", 0x5080CC)
i = MEM.find(pat2)
print("  --- 0x5080cc ---")
while i != -1:
    print(f"  at {BASE + i:#x}")
    i = MEM.find(pat2, i + 1)
