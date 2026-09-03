#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续227-下一步(B) 续: 通过反汇编收集 map 相关方法的调用者(call/jmp 目标)。
目标: 0x478990(internal)/0x478a20(0x47be00内 map op)/0x478770(ctor)/
      0x4787c0(find wrapper)/0x47be00(dispatch+find+enqueue)/0x478a20.
"""
BASE = 0x400000
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"
with open(IMG, "rb") as f:
    MEM = f.read()

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

TARGETS = {0x478990, 0x478a20, 0x478770, 0x4787c0, 0x47be00, 0x478a20}
callers = {t: [] for t in TARGETS}

# 代码段大致范围; 线性反汇编(含 skipdata)穿过数据与空洞
START = 0x401000
END   = 0x4f5000
off = START - BASE
data = MEM[off:END-BASE]
code_va = START
import capstone
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False

count = 0
for ins in md.disasm(data, code_va):
    count += 1
    if count > 4000000:
        break
    mn = ins.mnemonic
    if mn in ("call", "jmp"):
        os_ = ins.op_str.strip()
        if os_.startswith("0x"):
            try:
                t = int(os_, 16)
            except ValueError:
                continue
            if t in TARGETS:
                callers[t].append(ins.address)
    # 也捕捉 'call dword ptr [reg+x]' 形式(间接)vtable —— 本统计跳过

for t in sorted(TARGETS):
    print(f"--- callers of {t:#08x} ({len(callers[t])}):")
    for c in callers[t]:
        print(f"    {c:#08x}")
print("total insns scanned:", count)
