# -*- coding: utf-8 -*-
"""会议/任务分配：反查谁引用任务名表与运行时任务槽表；解执行驱动与特例。
映射 off = va - 0x400000。
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

def insns(start, hi, maxb=0x400):
    off = start - BASE
    src = bytes(MEM[off:off + maxb])
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
    except Exception:
        return []
    res = []
    for ins in md.disasm(src, start):
        if ins.address > hi:
            break
        res.append((ins.address, ins.size, ins.mnemonic, ins.op_str))
    return res

def ctx(va, span=0xC0):
    """取「末条指令正好结束于 va」的对齐序列"""
    best = []
    for off in range(va - span, va):
        seq = insns(off, va - 1)
        if seq and seq[-1][0] + seq[-1][1] == va:
            if len(seq) > len(best):
                best = seq
    return best

def prologue(va):
    off = va - BASE
    lo = max(0, off - 0x8000)
    best = None
    for sig in (b"\x55\x8b\xec", b"\x55\x89\xe5", b"\x56\x8b\xf1"):
        q = MEM.rfind(sig, lo, off)
        if q > 0 and (best is None or q > best):
            best = q
    return BASE + best if best else None

def lin(va, n, label=""):
    emit("")
    emit("---- %s  0x%08x..0x%08x" % (label, va, va + n))
    for (a, s, m, o) in insns(va, va + n, n + 0x40):
        emit("  %08x  %-8s %s" % (a, m, o))

def find_imm(value):
    """全文件搜 4 字节立即数引用"""
    pat = struct.pack("<I", value)
    res = []
    off = MEM.find(pat)
    while off >= 0:
        if off >= 0x1000:
            res.append(BASE + off)
        off = MEM.find(pat, off + 1)
    return res

TARGETS = [
    (0x504B28, "任务名表（12 项指针）"),
    (0x504898, "handler 表（13 项）"),
    (0x513FCC, "任务/家臣 计数"),
    (0x513FD4, "家臣表（stride 2）"),
    (0x513FE0, "任务槽表（13 word）"),
]
for val, tag in TARGETS:
    hits = find_imm(val)
    emit("=" * 76)
    emit("引用 0x%08x  %s  -> %d 处" % (val, tag, len(hits)))
    for h in hits[:60]:
        emit("  0x%08x   [func ~0x%08x]" % (h, prologue(h) or 0))
    emit("")

# 关键函数反汇编
lin(0x4602C0, 0x120, "任务执行驱动（含 call 0x4603f0 @0x4602f8）")
lin(0x460550, 0x130, "任务 0x16 特例 handler")
lin(0x45E700, 0xC0, "handler[0] 贩卖军粮")
lin(0x45E870, 0xC0, "handler[2] 军马")

open(os.path.join(HERE, "_taskmod2.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("see _taskmod2.txt")
