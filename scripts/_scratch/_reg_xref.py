#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Register-aware global-access tracer.
Many globals (0x514995, 0x519548, 0x47ca70, ...) are NOT written via an
immediate `mov [0xADDr], x` but via a register that was loaded with the
absolute address:  mov reg, 0xADDr  /  lea reg, [0xADDr].
This tool:
 1. finds every `mov reg, A` / `lea reg, [A]` (absolute) load site
 2. tracks that reg (and copies of it) forward within a window
 3. reports every STORE through the tracked reg:  mov [r], x / mov [r+d], x
    / inc [r] / dec [r] / add [r], x  -> these are the hidden writers.
Usage: _reg_xref.py 0x514995
"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open("_unpacked_mem.bin", "rb").read()
BASE = 0x400000
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

A = int(sys.argv[1], 16)
WINDOW = int(sys.argv[2]) if len(sys.argv) > 2 else 0x600

# 1. find absolute loads of A
REGMAP = {0:"eax",1:"ecx",2:"edx",3:"ebx",4:"esp",5:"ebp",6:"esi",7:"edi"}
loads = []  # (va, reg_idx)
# mov reg, imm32  -> b8+reg | c7 c0+reg
i = 0
while True:
    k = MEM.find(b"\xb8", i)
    if k < 0:
        break
    off = k
    op = MEM[off]
    if op == 0xb8:
        reg = 0
    elif 0xb9 <= op <= 0xbf:
        reg = op - 0xb8
    else:
        i = k + 1
        continue
    imm = int.from_bytes(MEM[off+1:off+5], "little")
    if imm == A:
        loads.append((BASE + off, reg))
    i = k + 1
# lea reg, [imm32]  -> 8d 0d+reg (only the absolute form, modrm mod=00, rm=101 -> disp32)
k = 0
while True:
    p = MEM.find(b"\x8d", k)
    if p < 0:
        break
    op = MEM[p]
    if op == 0x8d:
        modrm = MEM[p+1]
        # form: 8d /r  with mod=00 rm=101 => [disp32]
        if (modrm & 0xc0) == 0x00 and (modrm & 0x07) == 0x05:
            reg = (modrm >> 3) & 0x07
            disp = int.from_bytes(MEM[p+2:p+6], "little")
            if disp == A:
                loads.append((BASE + p, reg))
    k = p + 1

print("Absolute loads of %08x: %d" % (A, len(loads)))
for va, reg in loads:
    print("  load @%08x  reg=%s" % (va, REGMAP.get(reg, reg)))

# 2/3. for each load, track forward and find stores
def is_store_through(ins, tracked):
    """Return (reg_idx, disp, is_write) if ins stores through a tracked reg."""
    for op in ins.operands:
        if op.type == 3:  # memory
            base = op.mem.base
            if base in tracked and (op.mem.index == 0):
                return (base, op.mem.disp, True)
    return None

for va, reg in loads:
    tracked = set([reg])
    p = va
    end = va + WINDOW
    found = []
    while p < end and p < BASE + SZ - 16:
        try:
            ins = next(md.disasm(MEM[p-BASE:p-BASE+16], p))
        except Exception:
            p += 1
            continue
        # propagate copies: mov r2, r1 (tracked) -> add r2
        if ins.mnemonic == "mov" and len(ins.operands) == 2:
            dst, src = ins.operands
            if dst.type == 1 and src.type == 1 and src.reg in tracked and dst.reg not in tracked:
                tracked.add(dst.reg)
        # detect store through tracked reg
        if ins.mnemonic in ("mov", "inc", "dec", "add", "sub") and len(ins.operands) >= 1:
            hit = is_store_through(ins, tracked)
            if hit and ins.operands[0].type == 3:
                found.append((p, ins.mnemonic, hit[1], REGMAP.get(hit[0], hit[0])))
        # stop heuristics: ret / far jump to outside
        if ins.mnemonic in ("ret", "retn") or ins.mnemonic == "jmp" and ins.operands and ins.operands[0].type == 1:
            break
        p = ins.address + ins.size
    if found:
        print("\n  load @%08x reg=%s  -> STORE sites:" % (va, REGMAP.get(reg, reg)))
        for fva, mn, disp, rg in found:
            print("    %08x  %s [%s%+#x]" % (fva, mn, rg, disp))
