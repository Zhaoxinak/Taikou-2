#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan_archetype_gate.py — 找原版 exe 里「主角槽(byte[+0x3a]>>4)」的消费者，定位武将选择过滤点。

镜像:scripts/_unpacked_mem.bin(2MB flat @0x400000,脱壳自 TAIK2W95.exe)
线性扫描遇非法字节逐字节重同步(本 exe 代码段内夹数据,单次 disasm 会提前断)。
用法:python .rev/scan_archetype_gate.py [LO] [HI]   (hex VA,默认 0x401000 / 0x500000)
"""
import sys, pathlib
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM, X86_OP_IMM

BASE = 0x400000
ROOT = pathlib.Path(__file__).resolve().parents[2]
IMG = ROOT / "scripts" / "_unpacked_mem.bin"
LO = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x401000
HI = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x500000
BSDATA_BUF = 0x524A20

data = IMG.read_bytes()
code = data[LO - BASE:HI - BASE]
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

insns = []
i = 0
n = len(code)
while i < n:
    ins = None
    for x in md.disasm(code[i:i + 16], LO + i):
        ins = x
        break
    if ins is None:
        i += 1
        continue
    insns.append(ins)
    i += ins.size
print(f"[i] 线性反汇编 {len(insns)} 条 @ {LO:#x}..{HI:#x}")


def mems(ins):
    return [o.mem for o in ins.operands if o.type == X86_OP_MEM]


print("\n=== A) disp=+0x3a 访存点 ===")
hits3a = [ins for ins in insns if any(m.disp == 0x3A for m in mems(ins))]
for ins in hits3a:
    print(f"  {ins.address:#08x}  {ins.bytes.hex():<20} {ins.mnemonic} {ins.op_str}")
print(f"[i] 共 {len(hits3a)} 处")

print("\n=== B) 引用 BSDATA 缓冲 0x524a20 ===")
for ins in insns:
    if any((o.type == X86_OP_IMM and o.imm == BSDATA_BUF) or
           (o.type == X86_OP_MEM and o.mem.disp == BSDATA_BUF) for o in ins.operands):
        print(f"  {ins.address:#08x}  {ins.bytes.hex():<20} {ins.mnemonic} {ins.op_str}")

print("\n=== C) shr *,4 之后 6 条内出现 cmp *,0..8(主角槽判定形状) ===")
for i, ins in enumerate(insns):
    if ins.mnemonic != "shr":
        continue
    ops = ins.operands
    if len(ops) != 2 or ops[1].type != X86_OP_IMM or ops[1].imm != 4:
        continue
    tail = insns[i + 1:i + 7]
    if any(w.mnemonic.startswith("cmp") and
           any(o.type == X86_OP_IMM and 0 <= o.imm <= 8 for o in w.operands) for w in tail):
        print(f"  @{ins.address:#08x}")
        for w in insns[max(0, i - 3):i + 8]:
            print(f"      {w.address:#08x}  {w.bytes.hex():<16} {w.mnemonic} {w.op_str}")
        print()
