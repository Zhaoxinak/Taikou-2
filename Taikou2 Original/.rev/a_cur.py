#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a_cur.py — 当前 TAIK2W95_family.exe 洞区反汇编体检
用法: python a_cur.py [va_hex] [count]
无参: 依次 dump ft_btn_draw / ft_click / nav_click
"""
import sys, struct, capstone, pathlib

EXE = pathlib.Path(r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_family.exe')
DELTA = 0xC00
BASE = 0x400000
F = EXE.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True


def rd(va, n):
    return F[va - BASE - DELTA: va - BASE - DELTA + n]


def dis(va, n=60, stop_ret=True):
    off = va - BASE - DELTA
    cnt = 0
    for ins in md.disasm(F[off:off + n * 12], va):
        print('  %08X  %-20s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        cnt += 1
        if stop_ret and ins.mnemonic == 'ret':
            break
        if cnt >= n:
            break


if len(sys.argv) > 1:
    dis(int(sys.argv[1], 16), int(sys.argv[2]) if len(sys.argv) > 2 else 60)
else:
    for name, va in (('nav_click', 0x5352C0), ('ft_click', 0x535300),
                     ('ft_btn_draw', 0x535C40), ('ft_latch@55A0', 0x5355A0),
                     ('ft_latch@55C0', 0x5355C0)):
        print('===== %s @ %06X =====' % (name, va))
        dis(va, 200)
