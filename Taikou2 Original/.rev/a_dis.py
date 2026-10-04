#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a_dis.py — 用 clean_dump.bin (offset==RVA) 反汇编任意 VA
用法: python a_dis.py 0x4b1e60 [n]
"""
import sys, capstone, pathlib
D = pathlib.Path(r'F:\Games\Taikou 2\Taikou2 Original\.rev\clean_dump.bin').read_bytes()
BASE = 0x400000
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True


def dis(va, n=60, follow=True):
    off = va - BASE
    cnt = 0
    for ins in md.disasm(D[off:off + n * 12], va):
        print('  %08X  %-22s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        cnt += 1
        if follow and ins.mnemonic == 'ret' and cnt > 2:
            break
        if cnt >= n:
            break


if __name__ == '__main__':
    for a in sys.argv[1:]:
        print('===== %s =====' % a)
        dis(int(a, 16), 90)
