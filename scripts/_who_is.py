#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给未名全局量定名：dump 所有引用点的上下文，按「和谁一起被读/写」聚类。"""
import struct, pickle, re, sys
from collections import Counter
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False


def build():
    try:
        return pickle.load(open('scripts/_insn_addrs.pkl', 'rb'))
    except Exception:
        pass
    starts = set(); n = len(IMG)
    for i in range(n - 5):
        if IMG[i] == 0xE8:
            rel = struct.unpack('<i', IMG[i + 1:i + 5])[0]
            t = i + 5 + rel
            if 0 <= t < n: starts.add(t)
    insn = {}
    for s in sorted(starts):
        off = s; end = min(s + 0x4000, n)
        for ins in md.disasm(IMG[off:end], BASE + off):
            insn[off] = (ins.size, f'{ins.mnemonic} {ins.op_str}')
            off += ins.size
            if ins.mnemonic in ('ret', 'retn', 'retf', 'hlt', 'ud2', 'int3'): break
            if off >= end: break
    pickle.dump(insn, open('scripts/_insn_addrs.pkl', 'wb'))
    return insn


INSN = build()
ORDER = sorted(INSN)


def xref(imm):
    pat = struct.pack('<I', imm); out = []; off = 0
    while True:
        i = IMG.find(pat, off)
        if i < 0: break
        for j in range(max(0, i - 7), i + 1):
            if j in INSN:
                sz, txt = INSN[j]
                if j < i < j + sz or (j == i and sz >= 4):
                    out.append(j); break
        off = i + 1
    return sorted(set(out))


def ctx(j, n_before=4, n_after=6):
    """取 j 所在指令前后各若干条"""
    idx = None
    for k, s in enumerate(ORDER):
        if s == j:
            idx = k; break
    if idx is None: return [], []
    before = [INSN[s][1] for s in ORDER[max(0, idx - n_before):idx]]
    after = [INSN[s][1] for s in ORDER[idx + 1:idx + 1 + n_after]]
    return before, after


def caller_of(j):
    """回溯：该函数被谁 call（近似：找最近的前一个 call 指令的目标范围）"""
    return None


def report(name, imm, limit=18):
    sites = xref(imm)
    print(f'\n########## {name}  0x{imm:x}  -> {len(sites)} 处 ##########')
    forms = Counter()
    for j in sites:
        forms[INSN[j][1]] += 1
    print('  形态统计:', forms.most_common(6))
    seen = 0
    for j in sites:
        if seen >= limit: break
        b, a = ctx(j)
        print(f'\n  0x{BASE+j:x}: {INSN[j][1]}')
        if b: print(f'     前: {" | ".join(b[-3:])}')
        if a: print(f'     后: {" | ".join(a[:5])}')
        seen += 1


if __name__ == '__main__':
    targets = [('0x51dc5c (108次 movsx 热标量)', 0x51dc5c)]
    if len(sys.argv) > 1:
        targets = [('arg', int(a, 16)) for a in sys.argv[1:]]
    for nm, a in targets:
        report(nm, a)
