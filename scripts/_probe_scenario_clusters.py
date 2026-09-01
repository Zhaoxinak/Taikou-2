#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_probe_scenario_clusters.py -- 续208 探针：
对场景主循环 0x4e8625 调度的 6 个簇 handler（0x492e20/0x493140/0x492ed0/0x4931f0
(簇0/簇1) + 0x491e70/0x4873b0/0x524740 (else)）做短反汇编，抽取它们 push 给
0x4802e0（资源加载器）的「资源表基址 VA」，再把该基址处 stride-16 数组解码成
资源名列表，得出每个 layer 的完整资源表。

同时：反汇编 0x47fc60 体（boot 0x4e8625 崩于 0x47fcad）理解未映射写，评估补桩成本。

依赖：capstone（已挂 skipdata 自动补丁，.pth 在 usersite）。
"""
import os, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_unpacked_mem.bin')
BASE = 0x400000
code = open(BIN, 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def disasm_range(va, n=0x300):
    out = []
    for ins in md.disasm(code[va-BASE:va-BASE+n], va):
        out.append((ins.address, ins.mnemonic, ins.op_str))
    return out

def imm_of(op_str, pat):
    # 找形如 'push 0x506b20' / 'push 0x524978' 的立即数
    import re
    m = re.search(r'0x([0-9a-fA-F]+)', op_str)
    return int(m.group(1), 16) if m else None

def read_cstr(mu_addr):
    raw = code[mu_addr-BASE:mu_addr-BASE+16]
    n = raw.find(0)
    if n < 0: n = 16
    if n == 0: return ""
    try: return bytes(raw[:n]).decode('gbk')
    except Exception: return bytes(raw[:n]).decode('latin-1','replace')

def decode_res_array(base, maxn=12):
    """stride 16，每实体前 14B 是 'X:NAME' 资源名（NUL 终止）。返回名列表。"""
    names = []
    for i in range(maxn):
        va = base + i*16
        if va-BASE+14 > len(code): break
        raw = code[va-BASE:va-BASE+14]
        n = raw.find(0)
        if n < 0: n = 14
        if n == 0: break
        try: s = bytes(raw[:n]).decode('gbk')
        except Exception: s = bytes(raw[:n]).decode('latin-1','replace')
        if not s or ':' not in s: break
        names.append(s)
    return names

# 场景主循环调度的簇 handler
SCENARIO_CLUSTERS = {
    '簇0a 0x492e20': 0x492e20,
    '簇0b 0x493140': 0x493140,
    '簇1a 0x492ed0': 0x492ed0,
    '簇1b 0x4931f0': 0x4931f0,
    'else 0x491e70': 0x491e70,
    'else 0x4873b0': 0x4873b0,
    'else 0x524740': 0x524740,
}

print("="*70)
print("场景簇 handler → 资源表基址 → 资源名列表")
print("="*70)
all_bases = {}
for label, va in SCENARIO_CLUSTERS.items():
    insns = disasm_range(va, 0x300)
    bases = []
    for addr, mn, ops in insns:
        if mn == 'push' and '0x4' in ops:
            imm = imm_of(ops, None)
            if imm and BASE < imm < BASE+len(code):
                # 看后一条是否 call 0x4802e0
                bases.append((addr, imm))
    # 抽取前 8 个 push 立即数（资源表基址候选）
    cand = [imm for _, imm in bases[:8]]
    print(f"\n### {label}  (反汇编 {len(insns)} 条, push<res-base> {len(bases)} 处)")
    for addr, imm in bases[:8]:
        names = decode_res_array(imm)
        print(f"  push 0x{imm:06x}  -> 资源表前{max(len(names),0)}项: {names if names else '(非资源数组/名字表)'}")
    all_bases[label] = cand

print("\n" + "="*70)
print("0x47fc60 体（boot 0x4e8625 崩于 0x47fcad）反汇编")
print("="*70)
for addr, mn, ops in disasm_range(0x47fc60, 0x120):
    mark = "  <<< 崩点" if addr == 0x47fcad else ""
    print(f"  0x{addr:06x}: {mn} {ops}{mark}")
