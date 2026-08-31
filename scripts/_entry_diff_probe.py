#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续172 下一步(A)：0x4a5010 vs 0x4a5370 两个相性入口的 callee 判据差异分析。
输出：各自独有 callee、忠诚/相性阈值判定、bit7/bit15 setter 调用、set_lord_idx 调用点。
"""
import os, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()

def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off+n]), va))

# 已知语义的锚点函数
ANCHOR = {
    0x49a730: "bit7 setter (不在/非存活·低字节0x80)",
    0x49a860: "bit15 setter (不在/主家脱离·高字节0x80)",
    0x49a7d0: "set_lord_idx (主君索引; 0xffff=浪人)",
    0x49ffc0: "affinity_score (相性スコア, 阈值2)",
    0x49f5d0: "get_player (玩家武将号)",
    0x49f5e0: "get_player_entity",
    0x4a0540: "RNG?",
    0x49fc90: "RNG?",
    0x4ba350: "?",
    0x4ba380: "?",
    0x4ba410: "?",
}

TARGETS = {"0x4a5010": 0x4a5010, "0x4a5370": 0x4a5370}
res = {}
for name, va in TARGETS.items():
    code = dis(va, 0xa00)
    calls = {}
    for ins in code:
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            t = int(ins.op_str, 16)
            calls.setdefault(t, []).append(ins.address)
    res[name] = (calls, code)

c5010 = set(res["0x4a5010"][0])
c5370 = set(res["0x4a5370"][0])
print("=== callee 集合 ===")
print(f"  0x4a5010: {len(c5010)} 个")
print(f"  0x4a5370: {len(c5370)} 个")
print(f"  共有: {len(c5010 & c5370)} 个")
print("\n### 0x4a5010 独有 callee")
for t in sorted(c5010 - c5370):
    site = res["0x4a5010"][0][t]
    print(f"  0x{t:06x}  x{len(site)} @{[hex(a) for a in site]}  {ANCHOR.get(t,'')}")
print("\n### 0x4a5370 独有 callee")
for t in sorted(c5370 - c5010):
    site = res["0x4a5370"][0][t]
    print(f"  0x{t:06x}  x{len(site)} @{[hex(a) for a in site]}  {ANCHOR.get(t,'')}")
print("\n### 共有 callee")
for t in sorted(c5010 & c5370):
    print(f"  0x{t:06x}  0x4a5010 x{len(res['0x4a5010'][0][t])} / 0x4a5370 x{len(res['0x4a5370'][0][t])}  {ANCHOR.get(t,'')}")

# 阈值判定：cmp byte/word [reg+0x29], imm  (忠诚) ; cmp 与 affinity 返回值
print("\n=== 忠诚/相性 阈值判定 (cmp ... imm) ===")
for name, va in TARGETS.items():
    calls, code = res[name]
    ths = []
    for ins in code:
        if ins.mnemonic == "cmp" and re.search(r'\[[^]]+\+?\s*0x29\]', ins.op_str):
            ths.append((ins.address, ins.op_str))
        if ins.mnemonic == "cmp" and re.search(r'\[[^]]+\+?\s*0x2a\]', ins.op_str):
            ths.append((ins.address, ins.op_str))
    print(f"\n  ## {name}  (+0x29 忠诚 / +0x2a 主君索引 比较)")
    for a, o in ths:
        print(f"    @0x{a:06x} cmp {o}")
