#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续224 探针(C)：drain consumer 0x47ae20 + type getter 0x462fd0 + pop 0x49f6b0 + 跳转表 0x462584。
目标：确认 0x47ae20 是 pop 队列并逐记录调 0x4624f0 的 drain；0x462fd0 返回 type 范围；跳转表映射 type→handler。
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

# 0x47ae20 是 drain：看它是否 pop 队列并调 0x4624f0
show(0x47ae20, 0x400, "drain 0x47ae20")
show(0x49f6b0, 0x200, "pop/get-record 0x49f6b0")
show(0x462fd0, 0x200, "type-getter 0x462fd0")

# 跳转表 0x462584：6 个 dword（cmp eax,5 => 0..5 共 6 项）
print("\n===== 跳转表 @0x462584 (6 dwords LE) =====")
raw = code[0x462584-BASE:0x462584-BASE+24]
for i in range(6):
    v = struct.unpack("<I", raw[i*4:i*4+4])[0]
    print(f"  case {i}: 0x{v:06x}  (fn {hex(fn_start(v)) if 0x400000<=v<0x500000 else v})")
