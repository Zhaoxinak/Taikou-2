#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速 hexdump（GBK 解读）：python scripts/_dmp.py 0x5099c0 0x509a20 [label] ..."""
import os
import sys

BASE = 0x400000
mem = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '_unpacked_mem.bin'), 'rb').read()


def dump(lo, hi, label=''):
    print(f'--- {label} {lo:#x}..{hi:#x} ---')
    va = lo
    while va < hi:
        row = mem[va - BASE: va - BASE + 16]
        hexs = ' '.join(f'{b:02x}' for b in row)
        txt = row.decode('gbk', 'replace')
        txt = ''.join(c if c.isprintable() else '.' for c in txt)
        print(f'{va:#08x}  {hexs:<48s}  {txt}')
        va += 16


def strings_at(va, stride, n, label=''):
    print(f'--- {label} table {va:#x} stride={stride} n={n} ---')
    for i in range(n):
        raw = mem[va - BASE + i * stride: va - BASE + i * stride + stride]
        s = raw.split(b'\x00')[0]
        try:
            t = s.decode('gbk')
        except UnicodeDecodeError:
            t = repr(s)
        print(f'  [{i:2d}] {va + i * stride:#08x}  {t!r:<16s} raw={raw.hex()}')


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == '-t':
        strings_at(int(a[1], 0), int(a[2], 0), int(a[3], 0), a[4] if len(a) > 4 else '')
    else:
        i = 0
        while i + 1 < len(a):
            lo, hi = int(a[i], 0), int(a[i + 1], 0)
            lbl = a[i + 2] if i + 2 < len(a) and not a[i + 2].startswith('0x') else ''
            dump(lo, hi, lbl)
            print()
            i += 3 if lbl else 2
