# -*- coding: utf-8 -*-
"""① 能力 setter 0x49a2b0..0x49a350 的 disp  ② 0x513b14 的赋值来源(对象身份)。"""
import re, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

print("=" * 82)
print("A. 能力 setter 区 0x49a2a0..0x49a350")
print("=" * 82)
o = 0x49A2A0 - BASE
for ins in md.disasm(mem[o:o + 0xB0], 0x49A2A0):
    print(f"  {ins.address:08x}  {ins.mnemonic:<8} {ins.op_str}")

print("\n" + "=" * 82)
print("B. 0x513b14 的写入点 (谁是赋值方)")
print("=" * 82)
pat = struct.pack("<I", 0x513B14)
hits = [m.start() for m in re.finditer(re.escape(pat), mem)]
print(f"  立即数 0x513b14 命中 {len(hits)} 处")
for h in hits[:24]:
    va = BASE + h
    o2 = max(0, h - 26)
    seq = []
    for ins in md.disasm(mem[o2:h + 8], BASE + o2):
        seq.append((ins.address, ins.mnemonic, ins.op_str))
        if len(seq) > 7:
            break
    txt = " ; ".join(f"{m} {p}" for _, m, p in seq)
    print(f"    {va:08x}: {txt[:118]}")

print("\n" + "=" * 82)
print("C. 0x513b14 附近全局块 (0x513ae0..0x513b40) 速览")
print("=" * 82)
for i in range(0x513AE0, 0x513B40, 16):
    print(f"  {i:08x}: " + " ".join(f"{x:02x}" for x in mem[i - BASE:i - BASE + 16]))
