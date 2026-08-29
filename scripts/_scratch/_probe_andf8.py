# -*- coding: utf-8 -*-
"""映射已修正（off = va - 0x400000）。
检查 10 处 and al,0xF8 的上下文 —— 找 rank 的 read-modify-write；
另查 4 处 esi/ecx 基址的 word[+0x2c] 整体写入。
"""
import struct, os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
SZ = len(MEM)

def off2va(o):
    return BASE + o

def va2off(va):
    return va - BASE

OUT = []
def emit(s=""):
    OUT.append(s)

def prologue(va):
    off = va2off(va)
    lo = max(0, off - 0x4000)
    best = None
    for sig in (b"\x55\x8b\xec", b"\x55\x89\xe5", b"\x53\x8b\xdc", b"\x56\x8b\xf1"):
        q = MEM.rfind(sig, lo, off)
        if q > 0 and (best is None or q > best):
            best = q
    return off2va(best) if best else None

def window(va, before=0x50, after=0x40, maxins=60):
    start = prologue(va)
    if start is None:
        start = va - before
    off = va2off(start)
    if off < 0 or off >= SZ:
        return ["  (bad addr)"]
    src = bytes(MEM[off:off + 0x9000])
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
    except Exception:
        return ["  (capstone unavailable)"]
    res = []
    lo, hi = va - before, va + after
    try:
        for ins in md.disasm(src, start):
            if ins.address > hi:
                break
            if ins.address >= lo:
                mk = "  <<<<" if ins.address == va else ""
                res.append("    %08x  %-8s %s%s" % (ins.address, ins.mnemonic, ins.op_str, mk))
            if len(res) >= maxins:
                break
    except Exception:
        pass
    return res or ["  (none)"]

emit("=== and al,0xF8 各点上下文 ===")
off = MEM.find(b"\x24\xf8")
sites = []
while off >= 0:
    if off >= 0x1000:
        sites.append(off2va(off))
    off = MEM.find(b"\x24\xf8", off + 1)
for va in sites:
    st = prologue(va)
    emit("")
    emit("---- 0x%08x   [func @ %s]" % (va, ("0x%08x" % st) if st else "?"))
    for line in window(va):
        emit(line)

emit("")
emit("=" * 70)
emit("=== word[+0x2c] 整体写入（esi/ecx 基址，非 UI）上下文 ===")
for va in (0x474C29, 0x479BCF, 0x49A7F1, 0x49A859):
    st = prologue(va)
    emit("")
    emit("---- 0x%08x   [func @ %s]" % (va, ("0x%08x" % st) if st else "?"))
    for line in window(va):
        emit(line)

open(os.path.join(HERE, "_andf8.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("sites=%d  see _andf8.txt" % len(sites))
