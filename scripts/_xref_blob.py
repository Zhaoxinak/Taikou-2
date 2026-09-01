#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描全镜像中对 S14 blob 基址 0x51dc60（1176B = 49*24）的立即数引用，
并反汇编上下文，找出矩阵索引算术（乘 49 还是乘 24）。"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
BLOB = 0x51dc60
BLEN = 1176
END = BLOB + BLEN

md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

# 1) 精确基址引用
pat = struct.pack('<I', BLOB)
exact = []
off = 0
while True:
    i = IMG.find(pat, off)
    if i < 0: break
    exact.append(BASE + i); off = i + 1
print(f"=== 精确引用 0x51dc60 : {len(exact)} 处 ===")

# 2) 区间内地址引用 (0x51dc60 .. 0x51e103)
rng = []
for a in range(BLOB, END):
    p = struct.pack('<I', a)
    off = 0
    while True:
        i = IMG.find(p, off)
        if i < 0: break
        rng.append((BASE + i, a)); off = i + 1
print(f"=== 区间内地址引用 : {len(rng)} 处（含基址） ===")
from collections import Counter
cnt = Counter(a for _, a in rng)
print("  各被引用地址计数(前 12):", cnt.most_common(12))

targets = sorted(set(exact) | set(va for va, _ in rng))
print(f"\n=== 命中位置 {len(targets)} 个，反汇编上下文 ===")
for t in targets[:40]:
    o = t - BASE
    # 向前回溯最多 24 字节找一个合理指令起点（逐字节重同步）
    found = None
    for back in range(0, 30):
        st = o - back
        if st < 0: break
        for ins in md.disasm(IMG[st:st + 24], BASE + st):
            if ins.address == t:
                found = ins; start = st; break
            if ins.address > t: break
        if found: break
    if not found:
        print(f"  0x{t:x}: (未能反汇编)  raw={IMG[o:o+8].hex()}")
        continue
    ctx = []
    for ins in md.disasm(IMG[start:start + 64], BASE + start):
        ctx.append(f"0x{ins.address:x} {ins.mnemonic} {ins.op_str}")
        if len(ctx) >= 8: break
    print(f"  --- 0x{t:x} ---")
    for c in ctx: print("     " + c)
