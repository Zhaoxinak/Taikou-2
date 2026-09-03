#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续224 探针(E)：consumer 0x46e260 全貌（pop 0x526c50 + 循环调 0x4624f0）。
确认它是 SNDATA 记录的 per-record 处理 drain；并找它的调用方（是否从加载链 0x4b9c10 到达）。
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

def show(va, n, title):
    print(f"\n===== {title} 0x{va:06x} ({n}B) =====")
    for ins in dis(va, n):
        mark = ""
        if "0x526c50" in ins.op_str or "0x526c58" in ins.op_str:
            mark = "   <== QUEUE"
        if ins.mnemonic == "call":
            try:
                t = int(ins.op_str, 16)
                mark += f"   (fn {hex(fn_start(t))})"
            except: pass
        print(f"  0x{ins.address:06x}  {ins.mnemonic:8s} {ins.op_str}{mark}")

show(0x46e260, 0x300, "consumer 0x46e260")

cs = calls_of(0x46e260)
print(f"\n[callers of 0x46e260] {len(cs)} 处: {[hex(fn_start(c)) for c in sorted(cs)]}")

# 确认 0x46e260 是否从 SNDATA 加载链到达：callers 的 callers（一层）
print("\n[callers-of-callers of 0x46e260]:")
for c in sorted(cs):
    fn = fn_start(c)
    for cc in calls_of(fn):
        print(f"   0x{cc:06x} (fn {hex(fn_start(cc))}) -> calls {hex(fn)}")
