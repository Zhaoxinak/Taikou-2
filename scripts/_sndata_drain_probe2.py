#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续224 探针(B)：从 SNDATA 加载链追 drain consumer。
0x462460 = 队列入口(enqueue)；0x4b9c10/0x451860 = 加载器(读49B→call 0x462460)。
看 0x462460 是否内含 type 分派，或 0x4b9c10 在 enqueue 后调 drain consumer。
"""
import pickle
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

def show(va, n, title):
    print(f"\n===== {title} 0x{va:06x} ({n}B) =====")
    for ins in dis(va, n):
        mark = ""
        if "0x526c50" in ins.op_str or "0x526c58" in ins.op_str:
            mark = "   <== QUEUE"
        if ins.mnemonic == "call":
            mark += f"   (fn {hex(fn_start(int(ins.op_str,16)))})"
        print(f"  0x{ins.address:06x}  {ins.mnemonic:8s} {ins.op_str}{mark}")

show(0x462460, 0x200, "队列入口 0x462460")
show(0x4b9c10, 0x600, "SNDATA 加载器 0x4b9c10")
show(0x451860, 0x400, "加载器 0x451860")
show(0x47ae20, 0x300, "收尾 0x47ae20")
