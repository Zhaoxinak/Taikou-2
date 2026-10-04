#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a_call.py — 暴力找 E8/E9 rel32 指向目标 VA 的点 (无需正确反汇编对齐)
用法: python a_call.py 0x4b12b0 0x4b12d0
"""
import sys, struct, pathlib
D = pathlib.Path(r'F:\Games\Taikou 2\Taikou2 Original\.rev\clean_dump.bin').read_bytes()
BASE = 0x400000
for a in sys.argv[1:]:
    tgt = int(a, 16)
    print('=== call/jmp -> %06X ===' % tgt)
    for i in range(0x1000, min(len(D) - 5, 0x134000)):
        op = D[i]
        if op not in (0xE8, 0xE9):
            continue
        rel, = struct.unpack('<i', D[i + 1:i + 5])
        if BASE + i + 5 + rel == tgt:
            print('  %08X  %s' % (BASE + i, 'call' if op == 0xE8 else 'jmp'))
