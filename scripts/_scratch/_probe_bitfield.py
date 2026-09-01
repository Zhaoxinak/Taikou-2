# -*- coding: utf-8 -*-
"""映射 off = va - 0x400000。
全量反汇编 word[+0x2c] 位域库（0x49a600..0x49a8d0）—— 若有 rank 写回必在此。
另：esi 基址的 word[+0x2c] 写入点 + 剩余 and al,0xF8 点。
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

import os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
SZ = len(MEM)

OUT = []
def emit(s=""):
    OUT.append(s)

def lin(start_va, nbytes):
    off = start_va - BASE
    src = bytes(MEM[off:off + nbytes])
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
    except Exception:
        return ["  (capstone unavailable)"]
    res = []
    for ins in md.disasm(src, start_va):
        res.append("  %08x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
    return res

def prologue(va):
    off = va - BASE
    lo = max(0, off - 0x4000)
    best = None
    for sig in (b"\x55\x8b\xec", b"\x55\x89\xe5", b"\x53\x8b\xdc", b"\x56\x8b\xf1"):
        q = MEM.rfind(sig, lo, off)
        if q > 0 and (best is None or q > best):
            best = q
    return BASE + best if best else None

def window(va, before=0x40, after=0x30, maxins=60):
    start = prologue(va)
    if start is None:
        start = va - before
    off = start - BASE
    src = bytes(MEM[off:off + 0x9000])
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
    except Exception:
        return ["  (none)"]
    res = []
    lo, hi = va - before, va + after
    for ins in md.disasm(src, start):
        if ins.address > hi:
            break
        if ins.address >= lo:
            mk = "   <<<<" if ins.address == va else ""
            res.append("  %08x  %-8s %s%s" % (ins.address, ins.mnemonic, ins.op_str, mk))
        if len(res) >= maxins:
            break
    return res or ["  (none)"]

emit("=== 位域库 0x49a600..0x49a8e0 全量反汇编 ===")
for l in lin(0x49A600, 0x2E0):
    emit(l)

emit("")
emit("=" * 70)
emit("=== 0x474b80..0x474c60 (mov w [esi+0x2c], ax) ===")
for l in lin(0x474B80, 0xE0):
    emit(l)

emit("")
emit("=== 0x479b60..0x479c00 (mov w [esi+0x2c], dx) ===")
for l in lin(0x479B60, 0xA0):
    emit(l)

emit("")
emit("=" * 70)
emit("=== 剩余 and al,0xF8 点上下文 ===")
for va in (0x44C0D8, 0x45D359, 0x4731A7, 0x47FD5A, 0x49CB3C, 0x49CC17, 0x49D8AD):
    st = prologue(va)
    emit("")
    emit("---- 0x%08x  [func @ %s]" % (va, ("0x%08x" % st) if st else "?"))
    for l in window(va):
        emit(l)

open(os.path.join(HERE, "_bitfield.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("see _bitfield.txt")
