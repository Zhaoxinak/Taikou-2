#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续224 探针(A)：定位队列抽干端 consumer。
enqueue 0x4eefa0 内部以 `0x526c50` 为容器 this；0x526c58 是容器数据字段(0x526c50+8)间接读，故全镜像无字面 0x526c58 立即数。
本探针扫描全镜像所有含 0x526c50 的指令，按 enclosing fn 分组，定位 drain consumer。
"""
import pickle
from _disasm_all import disasm_all, load_image, new_md

BASE = 0x400000
code = load_image()
pkl = pickle.load(open("scripts/_insn_addrs.pkl", "rb"))
FUNCS_S = sorted(pkl[1])

def enclosing(va):
    fo = va - BASE
    lo, hi = 0, len(FUNCS_S) - 1
    best = None
    while lo <= hi:
        m = (lo + hi) // 2
        if FUNCS_S[m] <= fo:
            best = FUNCS_S[m]; lo = m + 1
        else:
            hi = m - 1
    return best

def fn_start(va):
    s = enclosing(va)
    return (BASE + s) if s is not None else None

Q_CTL = 0x526c50
need = f"0x{Q_CTL:06x}"

md = new_md(detail=False)
hits = []
for ins in disasm_all(md, code[0x1000:], 0x401000):
    if need in ins.op_str:
        hits.append((ins.address, ins.mnemonic, ins.op_str, fn_start(ins.address)))

# 按函数分组
byfn = {}
for a, m, o, fn in hits:
    byfn.setdefault(fn, []).append((a, m, o))

print(f"[含 0x{Q_CTL:06x} 的指令] 共 {len(hits)} 处，分布 {len(byfn)} 个函数\n")
# 只列出「真正使用容器」的函数（排除纯数据区误命中）：函数体在代码段 < 0x500000
code_fns = {fn: lst for fn, lst in byfn.items() if fn is not None and fn < 0x500000}
for fn in sorted(code_fns):
    lst = code_fns[fn]
    print(f"fn {hex(fn)} : {len(lst)} 处引用")
    for a, m, o in lst[:12]:
        print(f"    0x{a:06x}  {m:8s} {o}")
    if len(lst) > 12:
        print(f"    ... ({len(lst)-12} more)")
