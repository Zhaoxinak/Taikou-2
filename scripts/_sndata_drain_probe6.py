#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续224 探针(F)：跳转表 0x462584 + type-getter 0x462fd0 + 各 per-type handler 的 payload 字节读点。
目标：建 type(0..5) -> handler -> 字段偏移 schema。
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

# 跳转表 0x462584 (6 dwords)
print("===== 跳转表 @0x462584 (type 0..5 -> handler) =====")
raw = code[0x462584-BASE:0x462584-BASE+24]
tbl = []
for i in range(6):
    v = struct.unpack("<I", raw[i*4:i*4+4])[0]
    tbl.append(v)
    print(f"  type {i}: 0x{v:06x}  (fn {hex(fn_start(v))})")

print("\n===== type-getter 0x462fd0 =====")
for ins in dis(0x462fd0, 0x200):
    print(f"  0x{ins.address:06x}  {ins.mnemonic:8s} {ins.op_str}")

# 每个 handler 提取 [edi+X] / [ebp+X] 读点（record 指针在 edi）
HANDLERS = {
    "case0": 0x4625a0,
    "case1_sub_id8": 0x4632e0,
    "case1_sub_id3": 0x4630c0,
    "case1_sub_def": 0x461ed0,
    "case2": 0x462670,
    "case3": 0x462a80,
    "case4": 0x462bc0,
    "case5": 0x462d40,
}
for name, va in HANDLERS.items():
    print(f"\n===== handler {name} @0x{va:06x} =====")
    # 反汇编到下一个 ret 或 0x200B
    last = va
    body = dis(va, 0x300)
    for ins in body:
        s = ins.op_str
        # 高亮 record 字段读
        if ("[edi" in s or "[ebp" in s or "[esi" in s) and ("ptr" in s):
            print(f"  *0x{ins.address:06x}  {ins.mnemonic:8s} {s}")
        # 也显示 call 目标（理解 handler 调谁）
        if ins.mnemonic == "call":
            try:
                t = int(s, 16)
                print(f"   0x{ins.address:06x}  call 0x{t:06x}  (fn {hex(fn_start(t))})")
            except: pass
        if ins.mnemonic == "ret":
            break
