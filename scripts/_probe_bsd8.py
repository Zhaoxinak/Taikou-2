# -*- coding: utf-8 -*-
"""补齐属性跳表 16..19 分支体 + 公共尾 0x4c7e12 + 0x4c7e76。"""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)


def dis(va, maxb, n=26):
    o = va - BASE
    out = []
    for ins in md.disasm(mem[o:o + maxb], va):
        out.append((ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic in ("ret",) or len(out) >= n:
            break
    return out


for va, end, tag in [(0x4C7DB0, 0x4C7E12, "attr16"),
                     (0x4C7DD0, 0x4C7DEA, "attr17"),
                     (0x4C7DEA, 0x4C7DFF, "attr18"),
                     (0x4C7DFF, 0x4C7E12, "attr19"),
                     (0x4C7E12, 0x4C7E76, "公共尾")]:
    print(f"\n===== {tag} {va:#010x} =====")
    for a, m, o in dis(va, end - va):
        print(f"  {a:08x}  {m:<8} {o}")

print("\n===== early-exit 0x4c7e76 =====")
for a, m, o in dis(0x4C7E76, 80, 20):
    print(f"  {a:08x}  {m:<8} {o}")

print("\n===== 0x4c7e84 之后(跳表 20 项 + 后续) =====")
o = 0x4C7E84 - BASE + 80
for a, m, op in dis(0x4C7E84 + 80, 120, 20):
    print(f"  {a:08x}  {m:<8} {op}")
