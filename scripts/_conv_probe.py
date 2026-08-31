# -*- coding: utf-8 -*-
"""Dump prologue + epilogue of the memcpy-family helpers to learn the real
calling convention (cdecl vs stdcall, reg vs stack args)."""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

FUNCS = [0x4ebfe0, 0x4ec010, 0x4ebe60, 0x49f120, 0x49f0b0, 0x4ebfc0]

def dis(va, n=40):
    code = IMG[va-BASE: va-BASE+400]
    out = []
    for i in md.disasm(code, va):
        out.append(i)
        if len(out) >= n:
            break
    return out

for f in FUNCS:
    print("="*60)
    print("FUNC %s  (file off 0x%x)" % (hex(f), f-BASE))
    insns = dis(f, 24)
    for i in insns:
        print("  %s  %s" % (hex(i.address), i.mnemonic + " " + i.op_str))
    # find first ret / ret imm16 in linear disasm (epilogue convention)
    retn = 0
    for i in insns:
        if i.mnemonic == 'ret':
            retn = 0
            break
        if i.mnemonic == 'ret' and i.op_str:
            retn = int(i.op_str, 0)
            break
        if i.bytes[:1] == b'\xc2':  # ret imm16
            retn = int.from_bytes(i.bytes[1:3], 'little')
            break
    print("  -> epilogue ret operand = %d (0x%x)" % (retn, retn))
