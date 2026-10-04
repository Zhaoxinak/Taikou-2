#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a_win.py — 固定窗口反汇编 (不因 ret 停止)
用法: python a_win.py 0x462d40 140
"""
import sys, capstone, pathlib
D = pathlib.Path(r'F:\Games\Taikou 2\Taikou2 Original\.rev\clean_dump.bin').read_bytes()
BASE = 0x400000
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True


def win(va, n):
    off = va - BASE
    cnt = 0
    for ins in md.disasm(D[off:off + n * 16], va):
        print('  %08X  %-22s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        cnt += 1
        if cnt >= n:
            break


if __name__ == '__main__':
    win(int(sys.argv[1], 16), int(sys.argv[2]) if len(sys.argv) > 2 else 100)
