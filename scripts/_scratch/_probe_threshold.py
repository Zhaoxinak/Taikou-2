# -*- coding: utf-8 -*-
"""解 0x49fc30（職位→阈值）与 0x49fc90，以及晋升主函数 0x4ab261 所在的完整函数。"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import struct, os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

OUT = []
def emit(s=""):
    OUT.append(s)

def lin(va, n, label=""):
    off = va - BASE
    src = bytes(MEM[off:off + n])
    emit("")
    emit("---- %s  0x%08x .. 0x%08x" % (label or "", va, va + n))
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
    except Exception:
        emit("  (no capstone)")
        return
    for ins in md.disasm(src, va):
        extra = ""
        if ins.mnemonic == "call":
            pass
        emit("  %08x  %-8s %s%s" % (ins.address, ins.mnemonic, ins.op_str, extra))

# 阈值函数
lin(0x49FC00, 0x120, "阈值函数区 (含 0x49fc30 / 0x49fc90)")

# 晋升主函数（含 0x4ab261）
lin(0x4AB180, 0x160, "晋升主函数 (含 call set_rank @0x4ab261)")

# 0x4b9b66 所在函数（同型晋升）
lin(0x4B9AC0, 0x120, "同型晋升点 (0x4b9b66)")

# ---------- 尝试把 0x49fc30 当查表：dump 其数据
emit("")
emit("---- 0x49fc30 机器码 ----")
emit("  " + MEM[0x49FC30 - BASE:0x49FC30 - BASE + 48].hex(" "))
emit("---- 0x49fc90 机器码 ----")
emit("  " + MEM[0x49FC90 - BASE:0x49FC90 - BASE + 48].hex(" "))

open(os.path.join(HERE, "_threshold.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("see _threshold.txt")
