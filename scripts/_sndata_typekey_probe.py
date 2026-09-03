# -*- coding: utf-8 -*-
"""续227 探针：反汇编 0x462fd0(六类解析器) + 0x47bed0(二分搜索)，定位 id->type 二分键数组。
纯静态，不 boot。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import load_image, BASE

MEM = load_image()
N = len(MEM)

def off(va):
    return va - BASE

def disasm_func(va, size=0x200, detail=True):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = detail
    data = MEM[off(va):off(va)+size]
    out = []
    pos = 0
    while pos < len(data):
        got = 0
        for ins in md.disasm(data[pos:], va + pos):
            out.append(ins)
            pos = ins.address - va + ins.size
            got += 1
        if got == 0:
            pos += 1
    return out

def dump(va, size, label):
    print(f"\n===== {label} @ {hex(va)} (size {hex(size)}) =====")
    for ins in disasm_func(va, size):
        ops = ""
        if ins.op_str:
            ops = " " + ins.op_str
        print(f"  {hex(ins.address)}: {ins.mnemonic}{ops}")

if __name__ == "__main__":
    dump(0x462fd0, 0x200, "type resolver 0x462fd0")
    dump(0x47bed0, 0x140, "binary search 0x47bed0")
