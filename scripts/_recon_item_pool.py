#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recon: dump item-pool name tables + disassemble identity methods.
Goal: understand how a pool entry (cat 0..7, level, sub) resolves to an item name,
and whether the 189-item def table binds to the pool via (cat,sub) identity.
"""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
MAPOFF = BASE  # image loaded at BASE; file offset == VA within image


def va2off(va):
    return va - MAPOFF


def get_bytes(va, n):
    o = va2off(va)
    return IMG[o:o + n]


def dump_names(va, stride, count, label):
    print(f"\n=== {label}  va=0x{va:x} stride={stride} count={count} ===")
    names = []
    for i in range(count):
        b = get_bytes(va + i * stride, stride)
        # find terminating 0
        z = b.find(b'\x00')
        raw = b[:z] if z >= 0 else b
        try:
            s = raw.decode('gbk', 'replace')
        except Exception:
            s = repr(raw)
        names.append(s)
        if s and s != '?':
            print(f"  [{i:3d}] {s!r}")
    nonempty = [n for n in names if n and n != '?']
    print(f"  -> nonempty={len(nonempty)}/{count}")
    return names


def disasm(va, n=0x120, label=''):
    print(f"\n=== disasm {label}  0x{va:x} ({n} bytes) ===")
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    code = get_bytes(va, n)
    for ins in md.disasm(code, va):
        # show operands briefly
        print(f"  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}")


# ---- 1. name tables ----
# from item_pool_spec.json: getTypeName table 0x507ea8 stride7
#                          getShortName 0x507ee0
#                          getSecondaryName 0x507a50
dump_names(0x507ea8, 7, 200, "getTypeName table 0x507ea8 stride7")
dump_names(0x507ee0, 12, 60, "getShortName table 0x507ee0 (guess stride12)")
dump_names(0x507a50, 12, 60, "getSecondaryName table 0x507a50 (guess stride12)")

# ---- 2. methods ----
disasm(0x49c010, 0x80, "getTypeName (vtable[1])")
disasm(0x49c1f0, 0x80, "getShortName (vtable[5])")
disasm(0x49c200, 0x80, "getSecondaryName (vtable[6])")
disasm(0x49c030, 0x60, "getPoolIndex (vtable[2])")
disasm(0x49c070, 0x160, "getValue (vtable[0])")
