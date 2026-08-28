# -*- coding: utf-8 -*-
"""評定/任务分配模块 全区域反汇编补齐。"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()

OUT = []
def emit(s=""):
    OUT.append(s)

def lin(va, n, label=""):
    emit("")
    emit("=" * 74)
    emit("---- %s  0x%08x..0x%08x" % (label, va, va + n))
    off = va - BASE
    src = bytes(MEM[off:off + n + 0x40])
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
    except Exception:
        emit("  (no capstone)")
        return
    for ins in md.disasm(src, va):
        if ins.address >= va + n:
            break
        emit("  %08x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))

lin(0x4601B0, 0x110, "評定模块 开头（任务槽初始化）")
lin(0x460680, 0x290, "評定模块 后半（分配/结算）")
lin(0x463300, 0x120, "任务名表 0x504b28 使用处（菜单构建）")

open(os.path.join(HERE, "_council.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("see _council.txt")
