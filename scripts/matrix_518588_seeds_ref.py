#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
matrix_518588_seeds_ref.py — S13 矩阵静态种子目录（续251）
================================================================================
全表逐格仍须 emu；本脚本钉死**可静态收割**的立即数写与清零器形态。

已知静态种子（stdcall push 序 = val, col, row → writer）：
  block A: (17,0)=0 @0x4193f3；多处 val=0xFFFF 哨兵清格；0x409650 5×5 清 A=FFFF
  block B: (0,0)=2000 @0x4095b1/0x40a49e；(1,0)=2000 @0x40a3f4；(0,0)=0 清零
  block C: (0,0)=0 清零；0x409650 同步清 C=0

清零器 `0x409650(rec)`：嵌套 5×5，对每格 A←FFFF / B←0 / C←0。

运行：`python scripts/matrix_518588_seeds_ref.py` → RESULT n/n
"""
from __future__ import annotations

import os

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

_HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(_HERE, "_unpacked_mem.bin"), "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
results = []
WRITERS = {"A": 0x4A0FF0, "B": 0x4A1010, "C": 0x4A1030}


def chk(name, cond, detail=""):
    results.append((name, bool(cond)))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           (" — " + detail) if detail else ""))


def callers(target):
    out = []
    for i in range(len(MEM) - 5):
        if MEM[i] != 0xE8:
            continue
        rel = int.from_bytes(MEM[i + 1:i + 5], "little", signed=True)
        if BASE + i + 5 + rel == target:
            out.append(BASE + i)
    return out


def last3(site, lookback=64):
    pushes = []
    for ins in md.disasm(MEM[site - lookback - BASE:site - BASE], site - lookback):
        if ins.mnemonic != "push":
            continue
        op = ins.op_str.strip()
        try:
            v = int(op, 16) if op.startswith("0x") or op.startswith("-0x") else int(op)
            pushes.append(("i", v))
        except ValueError:
            pushes.append(("r", op))
    return pushes[-3:] if len(pushes) >= 3 else pushes


print("=== A. 清零器 0x409650 ===")
body = MEM[0x409650 - BASE:0x409690 - BASE]
chk("A1 调 writer A/B/C",
    all(c in callers(w) for c, w in ((0x409664, 0x4A0FF0), (0x40966F, 0x4A1010), (0x40967A, 0x4A1030))))
chk("A2 循环界 cmp 5 / cmp 5", body.count(b"\x66\x83\xfe\x05") + body.count(b"\x66\x83\xff\x05") >= 1
    or b"\x83\xfe\x05" in body or "0x5" in " ".join(
        i.op_str for i in md.disasm(body, 0x409650)))
# push 0xffff before A
chk("A3 A 格写 0xFFFF", last3(0x409664)[0] == ("i", 0xFFFF))
chk("A4 B/C 格写 0", last3(0x40966F)[0] == ("i", 0) and last3(0x40967A)[0] == ("i", 0))

print("\n=== B. 静态种子站点 ===")
cs = {k: callers(v) for k, v in WRITERS.items()}
chk("B1 0x4095b1 ∈ B callers（2000）", 0x4095B1 in cs["B"])
chk("B2 0x4095b1 三元组 (2000,0,0)", last3(0x4095B1) == [("i", 2000), ("i", 0), ("i", 0)])
chk("B3 0x40a3f4 三元组 (2000,0,1)", last3(0x40A3F4) == [("i", 2000), ("i", 0), ("i", 1)])
chk("B4 0x4193f3 三元组 (17,0,0)→A", last3(0x4193F3) == [("i", 17), ("i", 0), ("i", 0)])
chk("B5 0x4095be 三元组 (0,0,0)→C", last3(0x4095BE) == [("i", 0), ("i", 0), ("i", 0)])

print("\n=== C. 全立即数仍稀缺（全表须 emu）===")
imm = 0
for sites in cs.values():
    for s in sites:
        last = last3(s)
        if len(last) == 3 and all(t == "i" for t, _ in last):
            imm += 1
chk("C1 全立即数三元组 < 15", imm < 15, "imm=%d" % imm)
chk("C2 寄存器主导（A callers≥25）", len(cs["A"]) >= 25)

passed = sum(1 for _, c in results if c)
total = len(results)
print("\nRESULT: %d/%d checks passed" % (passed, total))
raise SystemExit(0 if passed == total else 1)
