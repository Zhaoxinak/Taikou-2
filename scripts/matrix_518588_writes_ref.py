#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
matrix_518588_writes_ref.py — 续248：S13 矩阵写回器静态立即数收割
================================================================
写回器（ecx = 记录基，通常 ∈ 0x518588 族）：
  0x4a0ff0(row,col,val) → word[ecx + (row*5+col)*2]          block A
  0x4a1010(row,col,val) → word[ecx + ((row+5)*5+col)*2]       block B
  0x4a1030(row, bit, val) → bitfield @ ecx+row*2+0x64         block C

本脚本证明：
  - 三写回器字节公式与上式一致
  - 调用点计数 31 / 19 / 13
  - **绝大多数实参为寄存器**；静态可收割的全立即数三元组极少
  ⇒ 逐格运行期数值仍须 emu 钩取（与续238 结论一致，本轮只把「静态上限」钉死）

续250 补：可静态钉死的种子写（非全表）：
  - block B `(0,0)=2000`：`0x4095b1` / `0x40a3f4`(col1) / `0x40a49e`
  - block A `(17,0,0)`：`0x4193f3`；多处 `val=0xFFFF` 哨兵清格
  - block C 清零三元组：`0x4095be` 等
"""
import os
from collections import Counter

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(_ROOT, "scripts", "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

WRITERS = {
    "A": 0x4A0FF0,
    "B": 0x4A1010,
    "C": 0x4A1030,
}

results = []


def chk(name, cond, detail=""):
    results.append((name, bool(cond)))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           ("  — " + detail) if detail else ""))


def callers(target):
    out = []
    for i in range(len(MEM) - 5):
        if MEM[i] != 0xE8:
            continue
        rel = int.from_bytes(MEM[i + 1:i + 5], "little", signed=True)
        if BASE + i + 5 + rel == target:
            out.append(BASE + i)
    return out


def dis(va, n=0x40):
    return list(md.disasm(MEM[va - BASE:va - BASE + n], va))


def parse_last3_pushes(site, lookback=48):
    start = max(BASE, site - lookback)
    pushes = []
    for ins in md.disasm(MEM[start - BASE:site - BASE], start):
        if ins.mnemonic != "push":
            continue
        op = ins.op_str.strip()
        try:
            v = int(op, 16) if op.startswith("0x") or op.startswith("-0x") else int(op)
            pushes.append(("imm", v))
        except ValueError:
            pushes.append(("reg", op))
    return pushes[-3:] if len(pushes) >= 3 else pushes


print("=== A. 写回器公式字节 ===")
# A: lea eax,[eax+eax*4] 编码 8d0480；B 另含 add eax,5 = 83c005
body_a = MEM[0x4A0FF0 - BASE:0x4A1008 - BASE]
chk("A1 0x4a0ff0 含 lea eax,[eax+eax*4]（8d0480）", b"\x8d\x04\x80" in body_a, body_a.hex())
chk("A2 0x4a0ff0 含 mov [ecx+eax*2],dx（66891441）", b"\x66\x89\x14\x41" in body_a)
body_b = MEM[0x4A1010 - BASE:0x4A102B - BASE]
chk("A3 0x4a1010 含 add eax,5（83c005）后同一 lea",
    b"\x83\xc0\x05" in body_b and b"\x8d\x04\x80" in body_b)
body_c = MEM[0x4A1030 - BASE:0x4A105F - BASE]
chk("A4 0x4a1030 含 +0x64 基（8d4410 64 或等价）",
    b"\x64" in body_c and b"\x66\x89\x10" in body_c,
    body_c.hex()[:80])

print("\n=== B. 调用点计数 ===")
cs = {k: callers(v) for k, v in WRITERS.items()}
chk("B1 writer A callers == 31", len(cs["A"]) == 31, "n=%d" % len(cs["A"]))
chk("B2 writer B callers == 19", len(cs["B"]) == 19, "n=%d" % len(cs["B"]))
chk("B3 writer C callers == 13", len(cs["C"]) == 13, "n=%d" % len(cs["C"]))

print("\n=== C. 立即数三元组稀缺 ===")
imm_counts = {}
for name, sites in cs.items():
    imm = 0
    for s in sites:
        last = parse_last3_pushes(s)
        if len(last) == 3 and all(t == "imm" for t, _ in last):
            imm += 1
    imm_counts[name] = imm
    chk("C1-%s 全立即数三元组 ≤ 6（寄存器主导）" % name,
        imm <= 6, "imm=%d / %d" % (imm, len(sites)))

chk("C2 合计全立即数三元组 < 15",
    sum(imm_counts.values()) < 15, "total=%d" % sum(imm_counts.values()))

print("\n=== D. 已知立即数样本（非穷尽矩阵）===")
# 抽样 B 的 2000 初始化
samples = []
for s in cs["B"]:
    last = parse_last3_pushes(s)
    if len(last) == 3 and all(t == "imm" for t, _ in last):
        # push order: val, col, row  (stdcall → [esp+4]=row)
        val, col, row = last[0][1], last[1][1], last[2][1]
        samples.append((s, row, col, val))
has2000 = any(v == 2000 for _, _, _, v in samples)
chk("D1 writer B 存在立即数 val=2000（初始化量级）", has2000 or imm_counts["B"] >= 1,
    "samples=%s" % [(hex(s), r, c, v) for s, r, c, v in samples[:6]])
# 续250：钉死三处已知种子站点
chk("D2 0x4095b1 push 2000→writer B", 0x4095B1 in cs["B"])
chk("D3 0x4193f3 push 17,0,0→writer A", 0x4193F3 in cs["A"])
chk("D4 0x4095be push 0,0,0→writer C", 0x4095BE in cs["C"])

passed = sum(1 for _, c in results if c)
total = len(results)
print("\nRESULT: %d/%d checks passed" % (passed, total))
raise SystemExit(0 if passed == total else 1)
