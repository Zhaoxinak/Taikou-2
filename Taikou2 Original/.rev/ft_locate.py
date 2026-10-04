#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ft_locate.py — 在脱壳镜像里按 GBK 串定位(用于找“武将详细”面板的绘制/命中代码)

用法:
  python .rev/ft_locate.py find 信赖度
  python .rev/ft_locate.py dump 0x504900 0x80
  python .rev/ft_locate.py dis 0x48xxxx 30
  python .rev/ft_locate.py callers 0x48xxxx
  python .rev/ft_locate.py refs 0x50xxxx
"""
import sys, pathlib, functools
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM, X86_OP_IMM

BASE = 0x400000
ROOT = pathlib.Path(__file__).resolve().parents[2]
IMG = ROOT / "scripts" / "_unpacked_mem.bin"
LO, HI = 0x401000, 0x600000


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
    for ins in md.disasm(mem()[off:off + 4096], va):
        print(f"  {ins.address:#08x}  {ins.bytes.hex():<20} {ins.mnemonic} {ins.op_str}")
        cnt += 1
        if cnt >= n:
            break


def hexdump(va, n):
    d = mem()[va - BASE: va - BASE + n]
    for i in range(0, len(d), 16):
        chunk = d[i:i + 16]
        asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)
        print(f"  {va+i:#08x}: {chunk.hex(' '):<48} {asc}")


def find(s):
    b = s.encode('gbk')
    d = mem()
    out = []
    i = d.find(b)
    while i != -1:
        out.append(BASE + i)
        i = d.find(b, i + 1)
    for va in out:
        print(f"  {va:#08x}  (RVA {va-BASE:#08x})  {s}")
    if not out:
        print("  <未找到>")
    return out


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
    if what == "find":
        find(sys.argv[2])
    elif what == "hexdump":
        hexdump(int(sys.argv[2], 16), int(sys.argv[3], 16))
    elif what == "dump":
        # alias: 反汇编
        dump(int(sys.argv[2], 16), int(sys.argv[3]) if len(sys.argv) > 3 else 40)
    elif what == "dis":
        dump(int(sys.argv[2], 16), int(sys.argv[3]) if len(sys.argv) > 3 else 40)
    elif what == "callers":
        callers(int(sys.argv[2], 16))
    elif what == "refs":
        refs(int(sys.argv[2], 16))
