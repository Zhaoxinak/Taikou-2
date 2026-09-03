# -*- coding: utf-8 -*-
"""续227 探针2：反汇编 0x49f6b0(队列pop·看是否设全局记录指针) + 0x47be00(真二分·看搜索键来源)。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import load_image, BASE

MEM = load_image()

def off(va):
    return va - BASE

def dump(va, size, label):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    data = MEM[off(va):off(va)+size]
    print(f"\n===== {label} @ {hex(va)} (size {hex(size)}) =====")
    pos = 0
    while pos < len(data):
        got = 0
        for ins in md.disasm(data[pos:], va + pos):
            ops = (" " + ins.op_str) if ins.op_str else ""
            print(f"  {hex(ins.address)}: {ins.mnemonic}{ops}")
            pos = ins.address - va + ins.size
            got += 1
        if got == 0:
            pos += 1

if __name__ == "__main__":
    dump(0x49f6b0, 0x60, "queue pop 0x49f6b0")
    dump(0x47be00, 0xf0, "real binary search 0x47be00")
