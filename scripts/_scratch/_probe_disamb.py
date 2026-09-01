# -*- coding: utf-8 -*-
"""判定 0x504898 的 13 个 handler 究竟是「任务执行」还是「情报报告」。
附：0x504888 / 0x504890 字符串、0x49c2b0(报告目标取名) 反汇编。
"""
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
SZ = len(MEM)

OUT = []
def emit(s=""):
    OUT.append(s)

def cstr(va, maxn=80):
    o = va - BASE
    if o < 0 or o >= SZ:
        return None
    e = MEM.find(b"\x00", o, o + maxn)
    if e < 0:
        e = o + maxn
    return MEM[o:e].decode("gbk", "replace")

def lin(va, n, label=""):
    emit("")
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
        extra = ""
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            try:
                t = int(ins.op_str, 16)
                extra = "   ; -> 0x%08x" % t
            except ValueError:
                pass
        emit("  %08x  %-8s %s%s" % (ins.address, ins.mnemonic, ins.op_str, extra))

emit("=== 0x504888 / 0x504890 附近字符串 ===")
for v in (0x504880, 0x504888, 0x504890, 0x504894):
    emit("  0x%08x  %r" % (v, cstr(v)))

emit("")
emit("=== 任务名表 0x504b28 前后 ===")
for v in range(0x504B20, 0x504B30, 4):
    emit("  0x%08x  %r" % (v, cstr(v)))

lin(0x45E700, 0x90, "handler[0] 0x45e700")
lin(0x45E790, 0xE0, "handler[1] 0x45e790")
lin(0x49C2B0, 0x80, "0x49c2b0（报告目标取名，被 0x460369 调用）")

open(os.path.join(HERE, "_disamb.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("see _disamb.txt")
