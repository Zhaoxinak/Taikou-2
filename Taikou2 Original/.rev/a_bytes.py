#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a_bytes.py — 按十六进制字节模式(含 ?? 通配)搜 clean_dump.bin
用法: python a_bytes.py "66 8b ?? 60" "0f b7 ?? 62"
"""
import sys, pathlib, capstone
D = pathlib.Path(r'F:\Games\Taikou 2\Taikou2 Original\.rev\clean_dump.bin').read_bytes()
BASE = 0x400000
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)


def compile_pat(s):
    toks = s.split()
    seq = []
    for t in toks:
        seq.append(None if t in ('??', '?') else int(t, 16))
    return seq


def scan(seq, limit=0x134000):
    n = len(seq)
    first = next((i for i, v in enumerate(seq) if v is not None), 0)
    out = []
    i = first
    while True:
        k = D.find(bytes([seq[first]]), i, limit)
        if k < 0:
            break
        i = k + 1
        st = k - first
        if st < 0:
            continue
        ok = True
        for j, v in enumerate(seq):
            if v is not None and D[st + j] != v:
                ok = False
                break
        if ok:
            out.append(st)
    return out


for pat in sys.argv[1:]:
    seq = compile_pat(pat)
    print('=== pattern %s ===' % pat)
    for st in scan(seq):
        va = BASE + st
        s = ''
        for ins in md.disasm(D[st:st + 24], va):
            s = '%08X  %-24s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
            break
        print('  hit %08X -> %s' % (va, s))
