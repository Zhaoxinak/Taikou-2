#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S6 (0x516610..0x51663d) 立即数 xref —— 复用 _insn_addrs.pkl 指令边界集。
4 字节立即数落在指令**中间**（操作数区）是常态，必须按「指令区间包含」判定。
"""
import struct, pickle, sys, collections
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
S6 = 0x516610
SIZE = 0x2e
_p = pickle.load(open('scripts/_insn_addrs.pkl', 'rb'))
if isinstance(_p, tuple):
    insn, starts = _p[0], sorted(_p[1])
else:
    insn = _p
    starts = sorted(insn.keys())
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True


def owner(off):
    import bisect
    i = bisect.bisect_right(starts, off) - 1
    return BASE + starts[i] if i >= 0 else 0


rows = collections.defaultdict(list)
for d in range(SIZE):
    imm = S6 + d
    pat = struct.pack('<I', imm)
    off = 0
    while True:
        i = IMG.find(pat, off)
        if i < 0:
            break
        off = i + 1
        hit = None
        for j in range(max(0, i - 8), i + 1):
            if j in insn:
                size, _ = insn[j]
                if j <= i < j + size:
                    hit = j
                    break
        if hit is None:
            continue
        inst = list(md.disasm(IMG[hit:hit + size], BASE + hit))
        if not inst:
            continue
        b = inst[0]
        rows[d].append((BASE + hit, f'{b.mnemonic} {b.op_str}', owner(hit)))

print('S6 绝对地址立即数 xref（0x516610 + N）\n')
for d in range(SIZE):
    rs = rows.get(d, [])
    if not rs:
        print(f'+{d:02x}  (0x{S6+d:x})  --')
        continue
    print(f'+{d:02x}  (0x{S6+d:x})  {len(rs)} 处')
    seen = set()
    for va, txt, fn in rs[:14]:
        print(f'       0x{va:06x} [fn 0x{fn:06x}]  {txt}')
