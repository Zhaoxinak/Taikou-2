# -*- coding: utf-8 -*-
"""找 word[+0x2c] setter 的调用者 —— 晋升逻辑应在调用方。
同时复查唯一的 byte[+0x2d] 写入点 0x43de0c 的 al 来源。
"""
import struct, os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()

e_lfanew = struct.unpack_from("<I", MEM, 0x3C)[0]
nsec = struct.unpack_from("<H", MEM, e_lfanew + 6)[0]
optsz = struct.unpack_from("<H", MEM, e_lfanew + 20)[0]
sect_off = e_lfanew + 24 + optsz
CODE = []
for i in range(nsec):
    o = sect_off + 40 * i
    name = MEM[o:o + 8].rstrip(b"\x00").decode("latin1")
    vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", MEM, o + 8)
    chars = struct.unpack_from("<I", MEM, o + 36)[0]
    if chars & 0x20000000:
        CODE.append((name, vaddr, rawptr, min(rawsize, vsize)))

def off2va(off):
    for (n, vaddr, rawptr, size) in CODE:
        if rawptr <= off < rawptr + size:
            return BASE + vaddr + (off - rawptr)
    return None

def va2off(va):
    rva = va - BASE
    for (n, vaddr, rawptr, size) in CODE:
        if vaddr <= rva < vaddr + size:
            return rawptr + (rva - vaddr)
    return None

OUT = []
def emit(s=""):
    OUT.append(s)

def prologue(va):
    off = va2off(va)
    if off is None:
        return None
    lo = max(0, off - 0x3000)
    best = None
    for sig in (b"\x55\x8b\xec", b"\x55\x89\xe5", b"\x53\x8b\xdc"):
        q = MEM.rfind(sig, lo, off)
        if q > 0 and (best is None or q > best):
            best = q
    return off2va(best) if best else None

def window(va, before=0x70, after=0x10, maxins=120):
    start = prologue(va)
    if start is None:
        start = va - before
    off = va2off(start)
    if off is None:
        return ["  (bad addr)"]
    src = bytes(MEM[off:off + 0x6000])
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
                res.append("    %08x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
            if len(res) >= maxins:
                break
    except Exception:
        pass
    return res or ["  (none)"]

def find_callers(target):
    """E8 rel32 调用 target 的所有位置"""
    res = []
    for (name, vaddr, rawptr, size) in CODE:
        p = rawptr
        end = rawptr + size - 5
        while p < end:
            if MEM[p] == 0xE8:
                rel = struct.unpack_from("<i", MEM, p + 1)[0]
                ins_end_va = off2va(p + 5)
                if ins_end_va is not None and (ins_end_va + rel) == target:
                    res.append(off2va(p))
            p += 1
    return res

TARGETS = [
    (0x4E3670, "setter: +0x2c(w) +0x2e(w) +0x30(w) +0x32(b), ret 0x10"),
    (0x4EF020, "setter: +0x2c(w) +0x2e(w) then call 0x576400, ret 0x1c"),
]
for tgt, desc in TARGETS:
    callers = find_callers(tgt)
    emit("=" * 78)
    emit("调用 0x%08x  (%s)" % (tgt, desc))
    emit("callers: %d" % len(callers))
    for c in callers:
        st = prologue(c)
        emit("")
        emit("---- call @ 0x%08x   [func @ %s]" % (c, ("0x%08x" % st) if st else "?"))
        for line in window(c):
            emit(line)
    emit("")

# ------------------------------------------------- byte[+0x2d] 唯一写入点
emit("=" * 78)
emit("唯一 byte[+0x2d] 写入点 0x43de0c 所在函数上下文")
for line in window(0x43DE0C, before=0x90, after=0x10, maxins=160):
    emit(line)

open(os.path.join(HERE, "_rankcallers.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("see _rankcallers.txt")
