#!/usr/bin/env python3
# 有界反汇编器：给定 VA 起点与长度（小快即可，避免 capstone 对超大 buffer 崩溃），
# 线性反汇编并写到 out 文件。支持从函数起点起 dump；若遇连续数据/不可解码则跳过继续。
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()

def off(v): return v - BASE

def disasm_region(start, length, out_path):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
    code = MEM[off(start):off(start)+length]
    lines = []
    for ins in md.disasm(code, start):
        # 还原 MSVC 常见跳转表/数据：遇到 `jmp dword ptr [reg*4+imm]` 之类保留
        lines.append(f"{ins.address:#010x}  {ins.bytes.hex():20s} {ins.mnemonic} {ins.op_str}")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    return len(lines)

if __name__ == '__main__':
    start = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x4c5600
    length = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x400
    out = sys.argv[3] if len(sys.argv) > 3 else 'scripts/_d_envoy_settle.txt'
    n = disasm_region(start, length, out)
    print(f"wrote {n} lines -> {out}")
