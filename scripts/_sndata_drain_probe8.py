#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续224 探针(H)：解码 0x504938 六类名串；确认 0x46e260 从 SNDATA 加载链可达；追 T1 default handler 0x461ed0 的子调用字段读。
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

# 1) 解码 6 类名串
print("===== 0x504938 六类名串 (GBK) =====")
tbl = code[0x504938-BASE:0x504938-BASE+54]
for i in range(6):
    chunk = tbl[i*9:i*9+9]
    name = chunk.split(b'\x00')[0].decode('gbk', errors='replace')
    print(f"  cat[{i}] = {name!r}")

# 2) 0x46e260 调用方（是否从 SNDATA 加载链到达）
print("\n===== callers of 0x46e260 =====")
for c in sorted(calls_of(0x46e260)):
    print(f"   0x{c:06x}  (fn {hex(fn_start(c))})")

# 确认 0x4624f0 是否也由其它路径调用（已知 0x46e260 唯一）
# 3) T1 default 0x461ed0 子调用 0x462140 / 0x49f5e0 字段读（追一层）
for sub in (0x462140, 0x49f5e0):
    print(f"\n===== sub-call 0x{sub:06x} 头部字段读 =====")
    for ins in dis(sub, 0x200):
        s = ins.op_str
        if "ptr" in s and ("[edi" in s or "[eax" in s or "[ecx" in s or "[esi" in s):
            print(f"  *0x{ins.address:06x}  {ins.mnemonic:8s} {s}")
        if ins.mnemonic == "ret" and ins.address > sub + 0x10:
            break
