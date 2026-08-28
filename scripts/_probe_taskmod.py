# -*- coding: utf-8 -*-
"""会议 / 任务分配 大模块：dump 任务名表 + handler 表 + 分发器。
映射：off = va - 0x400000（平坦内存映像）。
"""
import struct, os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
SZ = len(MEM)

OUT = []
def emit(s=""):
    OUT.append(s)

def cstr(va, maxn=64):
    o = va - BASE
    if o < 0 or o >= SZ:
        return None
    e = MEM.find(b"\x00", o, o + maxn)
    if e < 0:
        e = o + maxn
    return MEM[o:e].decode("gbk", "replace")

def u32(va):
    return struct.unpack_from("<I", MEM, va - BASE)[0]

def lin(va, n, label="", maxb=None):
    off = va - BASE
    src = bytes(MEM[off:off + n])
    emit("")
    emit("---- %s 0x%08x .. 0x%08x" % (label, va, va + n))
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
    except Exception:
        emit("  (no capstone)")
        return
    for ins in md.disasm(src, va):
        emit("  %08x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))

# ---------------------------------------------------------- 任务名表
TNAME = 0x504B28
emit("=== 任务名表 0x%08x（12 项指针表）===" % TNAME)
emit("原始: " + MEM[TNAME - BASE:TNAME - BASE + 0x40].hex(" "))
names = []
for i in range(14):
    ptr = u32(TNAME + 4 * i)
    s = cstr(ptr)
    names.append(s)
    emit("  [%2d] ptr=0x%08x  %r" % (i, ptr, s))

# ---------------------------------------------------------- handler 表
HTAB = 0x504898
emit("")
emit("=== 执行 handler 表 0x%08x（13 项）===" % HTAB)
emit("原始: " + MEM[HTAB - BASE:HTAB - BASE + 0x40].hex(" "))
handlers = []
for i in range(15):
    h = u32(HTAB + 4 * i)
    handlers.append(h)
    emit("  [%2d] handler = 0x%08x" % (i, h))

# ---------------------------------------------------------- 分发器
lin(0x4603F0, 0x180, "任务执行分发器")

# ---------------------------------------------------------- 分发器调用者
def find_callers(target):
    res = []
    p = 0x1000
    while p < SZ - 5:
        if MEM[p] == 0xE8:
            rel = struct.unpack_from("<i", MEM, p + 1)[0]
            if BASE + p + 5 + rel == target:
                res.append(BASE + p)
        p += 1
    return res

def prologue(va):
    off = va - BASE
    lo = max(0, off - 0x8000)
    best = None
    for sig in (b"\x55\x8b\xec", b"\x55\x89\xe5", b"\x56\x8b\xf1"):
        q = MEM.rfind(sig, lo, off)
        if q > 0 and (best is None or q > best):
            best = q
    return BASE + best if best else None

emit("")
emit("=== 0x4603f0 调用者 ===")
cs = find_callers(0x4603F0)
emit("callers: %d" % len(cs))
for c in cs[:20]:
    emit("  0x%08x  [func ~0x%08x]" % (c, prologue(c) or 0))

open(os.path.join(HERE, "_taskmod.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("names=%d handlers=%d callers=%d" % (len(names), len(handlers), len(cs)))
