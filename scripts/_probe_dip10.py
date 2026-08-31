# -*- coding: utf-8 -*-
"""
_probe_dip10.py —
  A) 全映像 e8 扫描 0x49fe37 / 0x49ff0d（放宽到 0x401000..0x5fffff）
  B) dword 数据引用扫描（函数指针表 / vtable）
  C) 补完 0x49ff0d 尾部
  D) 附近邻居函数一览（0x49fd50..0x4a0100）——找同簇 API
"""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
print(f"  image size = {SZ:#x}  VA max = {BASE + SZ:#x}")


def dis(va, maxins=200):
    o = va - BASE
    out = []
    for ins in md.disasm(MEM[o:o + maxins * 8], va):
        out.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        if len(out) >= maxins or ins.mnemonic == "ret":
            break
    return "\n".join(out)


def e8_callers(va, lo=0x401000, hi=None):
    hi = hi or (BASE + SZ)
    out = []
    i = lo - BASE
    end = hi - BASE - 5
    while i < end:
        if MEM[i] == 0xE8:
            rel = struct.unpack("<i", MEM[i + 1:i + 5])[0]
            if BASE + i + 5 + rel == va:
                out.append(BASE + i)
        i += 1
    return out


def find_abs(va):
    pat = struct.pack("<I", va)
    r = []
    i = MEM.find(pat)
    while i != -1:
        r.append(BASE + i)
        i = MEM.find(pat, i + 1)
    return r


print("=" * 78)
print("### A) 全映像 e8 扫描")
print("=" * 78)
for va, nm in [(0x49FE37, "set外交8级(对齐入口)"), (0x49FE40, "set外交8级(实际代码)"),
               (0x49FF0D, "set主从4级(对齐入口)"), (0x49FF10, "set主从4级(实际代码)")]:
    cs = e8_callers(va)
    print(f"  {nm} {va:#x}: {len(cs)} -> {[hex(c) for c in cs][:12]}")

print()
print("=" * 78)
print("### B) dword 数据引用")
print("=" * 78)
for va, nm in [(0x49FE37, "set外交8级"), (0x49FE40, "  (代码入口)"),
               (0x49FF0D, "set主从4级"), (0x49FF10, "  (代码入口)"),
               (0x49FD60, "get外交8级"), (0x49FE70, "get主从4级"),
               (0x49FD80, "关系记录查找")]:
    hs = find_abs(va)
    print(f"  {nm:<16} {va:#x}: {len(hs)} -> {[hex(h) for h in hs][:16]}")

print()
print("=" * 78)
print("### C) 0x49ff0d 尾部补完（从 0x49ffb5 起）")
print("=" * 78)
print(dis(0x49FFB5, 40))

print()
print("=" * 78)
print("### D) 0x49fd50..0x4a0120 区域函数簇（对齐入口探测）")
print("=" * 78)
o = 0x49FD50 - BASE
end = 0x4A0120 - BASE
funcs = []
i = o
while i < end:
    # nop 滑橇后接 push/pattern 视为入口
    if MEM[i] == 0x90 and MEM[i + 1] == 0x90:
        j = i
        while j < end and MEM[j] == 0x90:
            j += 1
        if j < end and MEM[j] in (0x55, 0x53, 0x56, 0x57, 0x51, 0x8B, 0x8A, 0xA1, 0xB8):
            funcs.append(BASE + j)
            i = j
    i += 1
for f in funcs:
    print(f"  {f:#x}")
