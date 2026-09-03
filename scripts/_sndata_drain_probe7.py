#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续224 探针(G)：解码 0x504938 (6x9B 类型解析表) + 各 handler 的 payload 字段读点([reg+off])。
"""
import struct, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import load_image, new_md

BASE = 0x400000
code = load_image()
pkl = pickle.load(open("scripts/_insn_addrs.pkl", "rb"))
FUNCS_S = sorted(pkl[1])

def fn_start(va):
    fo = va - BASE
    lo, hi = 0, len(FUNCS_S) - 1
    best = None
    while lo <= hi:
        m = (lo + hi) // 2
        if FUNCS_S[m] <= fo:
            best = FUNCS_S[m]; lo = m + 1
        else:
            hi = m - 1
    return (BASE + best) if best is not None else None

def dis(va, n):
    md = new_md(detail=True)
    return list(md.disasm(code[va-BASE:va-BASE+n], va))

# 解码 0x504938 表：6 项 × 9 字节
print("===== 类型解析表 @0x504938 (6 x 9B) =====")
tbl = code[0x504938-BASE:0x504938-BASE+54]
for i in range(6):
    chunk = tbl[i*9:i*9+9]
    print(f"  entry[{i}] bytes: {chunk.hex(' ')}")

# 各 handler：提取 record 字段读（[edi+X]/[ebp+X]/[esi+X] 带 ptr）
HANDLERS = {
    "T0  0x4625a0": 0x4625a0,
    "T1d 0x461ed0": 0x461ed0,
    "T1_3 0x4630c0": 0x4630c0,
    "T1_8 0x4632e0": 0x4632e0,
    "T2  0x462670": 0x462670,
    "T3  0x462a80": 0x462a80,
    "T4  0x462bc0": 0x462bc0,
    "T5  0x462d40": 0x462d40,
}
REGS = ("edi", "ebp", "esi", "eax", "ecx", "edx")
for name, va in HANDLERS.items():
    print(f"\n===== {name} =====")
    reads = []
    calls = []
    for ins in dis(va, 0x400):
        s = ins.op_str
        if "ptr" in s:
            for r in REGS:
                # 形如 [edi+0x10] / [edi+ecx*2+0x10] / [ebp-0x4]
                if ("[" + r) in s:
                    reads.append((ins.address, ins.mnemonic, s))
                    break
        if ins.mnemonic == "call":
            try:
                t = int(s, 16)
                calls.append((ins.address, t, fn_start(t)))
            except: pass
        if ins.mnemonic == "ret":
            break
    print(f"  [字段读点 {len(reads)}]:")
    for a, m, s in reads[:40]:
        print(f"    0x{a:06x}  {m:8s} {s}")
    if len(reads) > 40:
        print(f"    ... ({len(reads)-40} more)")
    print(f"  [calls {len(calls)}]:")
    for a, t, fn in calls[:30]:
        print(f"    0x{a:06x} -> 0x{t:06x} (fn {hex(fn) if fn else t})")
