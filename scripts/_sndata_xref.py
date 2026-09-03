# -*- coding: utf-8 -*-
"""续227: 全镜像扫 call 目标，定位 0x4624f0 / 0x462fd0 / 0x4787c0 的所有调用方。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all, load_image, BASE

MEM = load_image()
def va2off(va): return va - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False

targets = {0x4624f0, 0x462fd0, 0x4787c0}
hits = {t: [] for t in targets}

for ins in disasm_all(md, MEM, BASE):
    if ins.mnemonic == "call":
        try:
            t = int(ins.op_str, 16)
        except ValueError:
            continue
        if t in targets:
            hits[t].append(ins.address)

for t in sorted(targets):
    print(f"===== call 0x{t:x} 的调用方 ({len(hits[t])} 处) =====")
    for a in hits[t][:60]:
        print(f"    0x{a:x}")
    if len(hits[t]) > 60:
        print(f"    ... 共 {len(hits[t])} 处")
    print()
