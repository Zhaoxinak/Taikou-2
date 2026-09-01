# -*- coding: utf-8 -*-
"""定位「晋升写回」：word[+0x2c] 的写入点（rank 在位 8..10）。

修正：VA 需加 image base。扩展：覆盖 disp8 与 disp32 两种形式。
对每处写入点，回溯函数序言并从序言对齐反汇编，打印命中点周边窗口。
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

# ---------------------------------------------------------------- PE sections
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
    """file offset -> VA"""
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

R16 = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
R32 = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]
GRP1 = ["add", "or", "adc", "sbb", "and", "sub", "xor", "cmp"]

OUT = []
def emit(s=""):
    OUT.append(s)

# ------------------------------------------------- 扫 word[reg+0x2c] 写入
writes = []
for (name, vaddr, rawptr, size) in CODE:
    p = rawptr
    end = rawptr + size - 8
    while p < end:
        if MEM[p] != 0x66:
            p += 1
            continue
        op = MEM[p + 1]
        modrm = MEM[p + 2]
        reg = (modrm >> 3) & 7
        rm = modrm & 7
        mod = (modrm >> 6) & 3
        if mod == 1 and rm != 4:                       # [reg+disp8]
            disp = MEM[p + 3]
            nxt = p + 4
        elif mod == 2 and rm != 4:                     # [reg+disp32]
            disp = struct.unpack_from("<i", MEM, p + 3)[0]
            nxt = p + 7
        else:
            p += 1
            continue
        if disp != 0x2C:
            p += 1
            continue
        va = off2va(p)
        if op == 0x89:                                  # mov [..], r16
            writes.append((va, "mov w [%s+0x2c], %s" % (R32[rm], R16[reg])))
        elif op == 0xC7 and reg == 0:                   # mov [..], imm16
            imm = struct.unpack_from("<H", MEM, nxt)[0]
            writes.append((va, "mov w [%s+0x2c], 0x%x" % (R32[rm], imm)))
        elif op in (0x01, 0x09, 0x11, 0x19, 0x21, 0x29, 0x31):
            m = {0x01: "add", 0x09: "or", 0x11: "adc", 0x19: "sbb",
                 0x21: "and", 0x29: "sub", 0x31: "xor"}[op]
            writes.append((va, "%s w [%s+0x2c], %s" % (m, R32[rm], R16[reg])))
        elif op == 0x81:                                # grp1 imm16
            imm = struct.unpack_from("<H", MEM, nxt)[0]
            writes.append((va, "%s w [%s+0x2c], 0x%x" % (GRP1[reg], R32[rm], imm)))
        elif op == 0x83:
            imm = struct.unpack_from("<b", MEM, nxt)[0]
            writes.append((va, "%s w [%s+0x2c], %d" % (GRP1[reg], R32[rm], imm)))
        p += 1

emit("=== word[reg+0x2c] 写入点（rank 位于 bit8..10）===")
emit("total: %d" % len(writes))
for va, d in writes:
    emit("  %08x  %s" % (va, d))

# ------------------------------------------------- 全局立即数签名
emit("")
emit("=== 全局签名扫描 ===")
SIGS = [
    (b"\x66\x25\xff\xf8", "and ax, 0xF8FF   (清 rank 位8..10)"),
    (b"\x25\xff\xf8\x00\x00", "and eax, 0xF8FF"),
    (b"\x66\xc1\xe8\x08", "shr ax, 8        (取 rank)"),
    (b"\xc1\xe8\x08", "shr eax, 8       (取 rank)"),
    (b"\x66\xc1\xe0\x08", "shl ax, 8        (rank 复位到 bit8..10)"),
    (b"\xc1\xe0\x08", "shl eax, 8"),
]
for pat, desc in SIGS:
    off = MEM.find(pat)
    n = 0
    locs = []
    while off >= 0 and n < 40:
        va = off2va(off)
        if va:
            locs.append("0x%08x" % va)
            n += 1
        off = MEM.find(pat, off + 1)
    emit("  %-34s : %d 处  %s" % (desc, n, " ".join(locs[:14])))

# ------------------------------------------------- 上下文反汇编
def prologue(va):
    off = va2off(va)
    if off is None:
        return None
    lo = max(0, off - 0x2000)
    best = None
    for sig in (b"\x55\x8b\xec", b"\x55\x89\xe5", b"\x53\x8b\xdc"):
        q = MEM.rfind(sig, lo, off)
        if q > 0 and (best is None or q > best):
            best = q
    return off2va(best) if best else None

def window(va, before=0x60, after=0x30, maxins=90):
    start = prologue(va)
    if start is None:
        start = va - before
    off = va2off(start)
    if off is None:
        return ["  (bad addr)"]
    src = bytes(MEM[off:off + 0x4000])
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        md = Cs(CS_ARCH_X86, CS_MODE_32)
        md.detail = False
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

emit("")
emit("=== 各写入点上下文（自函数序言对齐反汇编）===")
for va, d in writes:
    st = prologue(va)
    emit("")
    emit("---- %08x  %s      [func @ %s]" % (va, d, ("0x%08x" % st) if st else "?"))
    for line in window(va):
        emit(line)

open(os.path.join(HERE, "_rank2c.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("word-writes=%d  see _rank2c.txt" % len(writes))
