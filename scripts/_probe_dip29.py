# -*- coding: utf-8 -*-
"""1) 0x4b6095 调用方  2) dump 0x4b5c06 友好外交候选函数  3) dump 0x4ebcd0 (lv 计算)."""
import re, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
N = len(mem)
def rva(p): return p - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def find_e8_calls(target):
    out = []
    i = 0
    while i + 5 <= N:
        if mem[i] == 0xe8:
            rel = struct.unpack("<i", mem[i+1:i+5])[0]
            dst = (BASE + i + 5 + rel) & 0xffffffff
            if dst == target:
                out.append(BASE + i)
        i += 1
    return out

def dump(a, b):
    for ins in md.disasm(mem[rva(a): rva(b)], a):
        mark = ""
        if ins.mnemonic == "call": mark = "  <CALL>"
        print(f"0x{ins.address:05x}: {ins.mnemonic:9} {ins.op_str}{mark}")

print("### 0x4b6095 (高压屈服 set) 调用方:")
for c in find_e8_calls(0x4b6095):
    print(f"  0x{c:x}")
print("  (若为空则经间接派发)")

print("\n### 0x4b5bc0-0x4b5c40 (0x4b5c06 set_diplo(?,?2) 友好外交候选函数):")
dump(0x4b5bc0, 0x4b5c40)

print("\n### 0x4ebcd0-0x4ebd40 (lv 计算函数):")
dump(0x4ebcd0, 0x4ebd40)
