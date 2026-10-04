#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xref.py — 脱壳镜像的 xref / 反汇编小工具(本会话临时用)

镜像:scripts/_unpacked_mem.bin(2MB flat @0x400000)
用法:
  python .rev/xref.py callers 0x488030      # 找 call/jmp 到该 VA 的点
  python .rev/xref.py dis 0x487f9a 60       # 从对齐点反汇编 n 条
  python .rev/xref.py refs 0x50c680         # 任何立即数/位移引用该 VA
"""
import sys, pathlib, functools
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM, X86_OP_IMM

BASE = 0x400000
ROOT = pathlib.Path(__file__).resolve().parents[2]
IMG = ROOT / "scripts" / "_unpacked_mem.bin"
LO, HI = 0x401000, 0x520000


@functools.lru_cache(maxsize=None)
def mem():
    return IMG.read_bytes()


@functools.lru_cache(maxsize=None)
def insns():
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    code = mem()[LO - BASE:HI - BASE]
    out = []
    i, n = 0, len(code)
    while i < n:
        x = None
        for z in md.disasm(code[i:i + 16], LO + i):
            x = z
            break
        if x is None:
            i += 1
            continue
        out.append((x.address, x.bytes, x.mnemonic, x.op_str, x.size,
                    [(o.type, getattr(o, "imm", None), getattr(o, "mem", None)) for o in x.operands]))
        i += x.size
    return out


def dump(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    off = va - BASE
    cnt = 0
    for ins in md.disasm(mem()[off:off + n * 16], va):
        print(f"  {ins.address:#08x}  {ins.bytes.hex():<18} {ins.mnemonic} {ins.op_str}")
        cnt += 1
        if cnt >= n:
            break


def callers(target):
    for addr, by, mn, ops, size, ol in insns():
        if mn in ("call", "jmp") and any(t == X86_OP_IMM and imm == target for t, imm, _m in ol):
            print(f"  {addr:#08x}  {by.hex():<12} {mn} {ops}")


def refs(target):
    for addr, by, mn, ops, size, ol in insns():
        for t, imm, mm in ol:
            if (t == X86_OP_IMM and imm == target) or (t == X86_OP_MEM and mm and mm.disp == target):
                print(f"  {addr:#08x}  {by.hex():<12} {mn} {ops}")
                break


if __name__ == "__main__":
    what = sys.argv[1]
    a = int(sys.argv[2], 16)
    if what == "callers":
        callers(a)
    elif what == "refs":
        refs(a)
    else:
        dump(a, int(sys.argv[3]) if len(sys.argv) > 3 else 60)
