#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""0x51dc5c 被引用 111 次，紧邻 S14 blob 基址 0x51dc60 之前。
反汇编所有引用点，找出访问 blob 的索引算术（乘 49 还是乘 24）。"""
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

import struct, re
from collections import Counter
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

TARGET = 0x51dc5c
pat = struct.pack('<I', TARGET)
sites = []
off = 0
while True:
    i = IMG.find(pat, off)
    if i < 0: break
    sites.append(BASE + i); off = i + 1
print(f"0x51dc5c 引用点: {len(sites)} 处")

# 寻找含 imul / shl / lea 且操作数含 49(0x31) 或 24(0x18) 的上下文
KEY = re.compile(r'\b(0x31|49|0x18|24)\b')
interesting = []
for t in sites:
    o = t - BASE
    ctx = None
    for back in range(0, 24):
        st = o - back
        if st < 0: break
        seq = []
        for ins in md.disasm(IMG[st:st + 96], BASE + st):
            if ins.address > t: break
            seq.append(ins)
            if ins.address == t:
                ctx = (st, seq); break
        if ctx: break
    if not ctx: continue
    st, seq = ctx
    txt = " | ".join(f"{i.mnemonic} {i.op_str}" for i in seq[-8:])
    if any(i.mnemonic in ('imul', 'shl', 'mul') for i in seq[-8:]) or KEY.search(txt):
        interesting.append((t, txt))

print(f"\n含 imul/shl 或常数 49/24 的上下文: {len(interesting)} 处\n")
for t, txt in interesting[:25]:
    print(f"0x{t:x}: {txt}")

# 统计最常见的上下文形态
forms = Counter()
for t in sites:
    o = t - BASE
    for back in range(0, 24):
        st = o - back
        if st < 0: break
        seq = []
        for ins in md.disasm(IMG[st:st + 96], BASE + st):
            if ins.address > t: break
            seq.append(ins)
            if ins.address == t:
                forms[" | ".join(f"{i.mnemonic} {i.op_str}" for i in seq[-3:])] += 1
                break
print(f"\n最常见三指令形态 (Top 12):")
for f, c in forms.most_common(12):
    print(f"  x{c:<4} {f}")
