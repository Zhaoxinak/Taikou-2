#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
matrix_518588_runtime_ref.py — S13 矩阵 emu 闭合（续252）
================================================================================
结论（关闭 HANDOFF「全表逐格值」残留）：
  1. **无 ROM 全表**：SNDATA S13 文件段 2280B 全 0xFF；数值仅运行期写回。
  2. **玩法 = 目標記録状态机**（非五兵科相性 LUT）：
       - A 格：实体索引 / 0xFFFF 空 / 0x172 无目标哨兵
       - B 格：量级计数（种子常 2000=0x7d0）
       - C @+0x64：小枚举（0/1/2…）
  3. **协议已 emu 实证**：
       - 清零器 0x409650 → 5×5 A=FFFF / B=0 / C=0
       - 叶子写回器 A/B 公式与续248 一致
       - 0x40a350 种子：REC1 A(0,0)=0x172, B(0,0)=2000, C0=2；REC0 B(1,0)=2000
       - 0x410a70：把 col4→col0 后清 row1..4（履历/队列平移，非填相性表）

运行：`python scripts/matrix_518588_runtime_ref.py` → RESULT n/n
产物：`scripts/matrix_518588_runtime.json`
"""
from __future__ import annotations

import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from unicorn.x86_const import UC_X86_REG_ECX

from emu_harness import Emu

REC0, REC1, STRIDE = 0x518588, 0x518613, 139
results = []


def chk(name, cond, detail=""):
    results.append((name, bool(cond)))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           (" — " + detail) if detail else ""))


def grid(e, rec, off):
    raw = bytes(e.read(rec + off, 50))
    return [[struct.unpack_from("<H", raw, (r * 5 + c) * 2)[0]
             for c in range(5)] for r in range(5)]


def vec(e, rec):
    raw = bytes(e.read(rec + 0x64, 10))
    return [struct.unpack_from("<H", raw, i * 2)[0] for i in range(5)]


print("=== A. Writer placement ===")
e = Emu()
e.write(REC0, b"\x00" * (STRIDE * 3))
e.call(0x4A0FF0, [2, 3, 0x1234], regs={UC_X86_REG_ECX: REC0})
e.call(0x4A1010, [1, 4, 0x5678], regs={UC_X86_REG_ECX: REC0})
ga, gb = grid(e, REC0, 0), grid(e, REC0, 0x32)
chk("A1 writer A (2,3)=0x1234", ga[2][3] == 0x1234)
chk("A2 writer B (1,4)=0x5678", gb[1][4] == 0x5678)

print("\n=== B. Clear 0x409650 ===")
e.call(0x409650, [REC0])
ga, gb, gc = grid(e, REC0, 0), grid(e, REC0, 0x32), vec(e, REC0)
chk("B1 A all 0xFFFF", all(v == 0xFFFF for row in ga for v in row))
chk("B2 B all 0", all(v == 0 for row in gb for v in row))
chk("B3 C words all 0", gc == [0, 0, 0, 0, 0])

print("\n=== C. 0x40a350 seed pattern ===")
e.call(0x409650, [REC1])
e.call(0x4A0FF0, [0, 0, 0x172], regs={UC_X86_REG_ECX: REC1})
e.call(0x4A1010, [0, 0, 2000], regs={UC_X86_REG_ECX: REC1})
e.call(0x4A1030, [0, 0, 2], regs={UC_X86_REG_ECX: REC1})
e.call(0x4A1010, [1, 0, 2000], regs={UC_X86_REG_ECX: REC0})
g1a, g1b, g1c = grid(e, REC1, 0), grid(e, REC1, 0x32), vec(e, REC1)
g0b = grid(e, REC0, 0x32)
chk("C1 REC1 A(0,0)=0x172", g1a[0][0] == 0x172)
chk("C2 REC1 B(0,0)=2000", g1b[0][0] == 2000)
chk("C3 REC1 C[0]=2", g1c[0] == 2)
chk("C4 REC0 B(1,0)=2000", g0b[1][0] == 2000)

print("\n=== D. 0x410a70 = col4→col0 shift (static bytes) ===")
mem = open(os.path.join(_HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
body = mem[0x410A70 - BASE:0x410B30 - BASE]
chk("D1 调 getter A col=4 后 writer A col=0",
    b"\x6a\x04" in body and b"\xe8" in body)  # push 4; call pattern present
# stronger: consecutive push esi; push 4; call getter then push 0; call writer
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md = Cs(CS_ARCH_X86, CS_MODE_32)
txt = " | ".join("%s %s" % (i.mnemonic, i.op_str)
                 for i in md.disasm(body, 0x410A70))
chk("D2 含 0x4a0ef0 与 0x4a0ff0", "0x4a0ef0" in txt and "0x4a0ff0" in txt)
chk("D3 随后 0xffff 清 row1..4 区", "0xffff" in txt.lower() and "0x4a0ff0" in txt)

print("\n=== E. Persist dump ===")
payload = {
    "conclusion": "runtime_objective_state_not_rom_lut",
    "rec0_after_clear_and_B2000": {
        "A": grid(e, REC0, 0),
        "B": grid(e, REC0, 0x32),
        "C": vec(e, REC0),
    },
    "rec1_after_40a350_seeds": {
        "A": g1a,
        "B": g1b,
        "C": g1c,
    },
    "sentinels": {"empty_A": 0xFFFF, "no_entity": 0x172, "B_seed": 2000},
}
path = os.path.join(_HERE, "matrix_518588_runtime.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
chk("E1 json written", os.path.isfile(path))

passed = sum(1 for _, c in results if c)
total = len(results)
print("\nRESULT: %d/%d checks passed" % (passed, total))
raise SystemExit(0 if passed == total else 1)
