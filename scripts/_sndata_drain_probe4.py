#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续224 探针(D)：找 0x4624f0(per-record type dispatch) 与 0x49f6b0(pop) 的调用方。
同时看 0x462fd0(type getter) 返回什么（确认 type 范围）。
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

def calls_of(tgt):
    out = set(); off = 0
    while True:
        idx = code.find(b'\xe8', off)
        if idx < 0: break
        rel = struct.unpack("<i", code[idx+1:idx+5])[0]
        va = BASE + idx + 5 + rel
        if va == tgt: out.add(BASE + idx)
        off = idx + 1
    return out

def dis(va, n):
    md = new_md(detail=True)
    return list(md.disasm(code[va-BASE:va-BASE+n], va))

for tgt in (0x4624f0, 0x49f6b0, 0x462fd0, 0x47ae20, 0x47ae40):
    cs = calls_of(tgt)
    print(f"\n[callers of 0x{tgt:06x}] {len(cs)} 处:")
    for c in sorted(cs):
        print(f"   0x{c:06x}  (fn {hex(fn_start(c))})")

# type-getter 0x462fd0 细节
print("\n===== 0x462fd0 (type getter) =====")
for ins in dis(0x462fd0, 0x200):
    print(f"  0x{ins.address:06x}  {ins.mnemonic:8s} {ins.op_str}")

# 看 0x4624f0 的 caller 是否 pop 队列再分派 —— 取首个 caller 反汇编头部
cs = sorted(calls_of(0x4624f0))
if cs:
    fn = fn_start(cs[0])
    print(f"\n===== caller fn {hex(fn)} 头部 (含 0x4624f0 调用) =====")
    for ins in dis(fn, 0x300):
        mark = "   <== DISPATCH" if ins.op_str == "0x4624f0" else ""
        if "0x526c50" in ins.op_str or "0x526c58" in ins.op_str:
            mark += "   <== QUEUE"
        print(f"  0x{ins.address:06x}  {ins.mnemonic:8s} {ins.op_str}{mark}")
