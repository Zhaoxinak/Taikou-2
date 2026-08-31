#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan the unpacked image for `call rel32` targets and dump caller VA + a few
context lines. Also dumps xrefs to a literal base address (for table populators)."""
import sys
from capstone import *

MEM = open("scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)

def va_to_off(va):
    return va - BASE

def off_to_va(off):
    return off + BASE

def disassemble_at(va, size=0x120):
    off = va_to_off(va)
    code = MEM[off:off+size]
    out = []
    for ins in md.disasm(code, va):
        out.append(ins)
    return out

def find_callers(targets):
    """targets: iterable of absolute VA. Return dict va->list of caller VAs."""
    res = {t: [] for t in targets}
    # scan whole image for e8
    off = 0
    n = len(MEM)
    while off + 5 <= n:
        if MEM[off] == 0xe8:
            rel = int.from_bytes(MEM[off+1:off+5], "little", signed=True)
            callee = (BASE + off + 5) + rel
            if callee in res:
                caller = BASE + off
                res[callee].append(caller)
        off += 1
    return res

def find_literal_xref(literal_va, span=0x40):
    """Find instructions that reference `literal_va` via any addressing mode
    (displacement bytes). Capstone gives ins.op_str with hex; we scan disasm
    context for the address text."""
    hits = []
    off = 0
    n = len(MEM)
    while off + span <= n:
        # quick reject: literal not present as 4-byte LE in window
        lb = literal_va.to_bytes(4, "little")
        if lb not in MEM[off:off+span]:
            off += 1
            continue
        code = MEM[off:off+span]
        for ins in md.disasm(code, BASE+off):
            if ("%x" % literal_va) in ins.op_str.lower() or ("%08x" % literal_va) in ins.op_str.lower():
                hits.append((BASE+off, ins.address, ins.mnemonic + " " + ins.op_str))
        off += 1
    return hits

if __name__ == "__main__":
    targets = [int(x, 16) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else []
    if targets:
        callers = find_callers(targets)
        for t in targets:
            cs = callers[t]
            print("\n########## callers of 0x%x : %d 处 ##########" % (t, len(cs)))
            for c in sorted(cs):
                # print 1-line context: the call
                ins = disassemble_at(c, 0x10)
                call_line = next((i for i in ins if i.address == c), None)
                print("  0x%x : %s" % (c, (call_line.mnemonic + " " + call_line.op_str) if call_line else "??"))
    # optional literal xref
    if len(sys.argv) > 2:
        lit = int(sys.argv[2], 16)
        print("\n########## literal xref 0x%x ##########" % lit)
        for va, addr, s in find_literal_xref(lit):
            print("  0x%x : %s" % (addr, s))
