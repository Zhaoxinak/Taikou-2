# -*- coding: utf-8 -*-
"""1) 校验 PE 分区覆盖（0x43de0c 为何 bad addr）
   2) 全量扫 byte 写入 [..+0x2d]（含 SIB / disp32 形式）
   3) 扫 and al,0xF8 并给上下文 —— 晋升的 read-modify-write 候选
   4) 反汇编 0x43dd50（唯一 byte[+0x2d] 写入所在函数）
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

e_lfanew = struct.unpack_from("<I", MEM, 0x3C)[0]
nsec = struct.unpack_from("<H", MEM, e_lfanew + 6)[0]
optsz = struct.unpack_from("<H", MEM, e_lfanew + 20)[0]
sect_off = e_lfanew + 24 + optsz
ALL = []
for i in range(nsec):
    o = sect_off + 40 * i
    name = MEM[o:o + 8].rstrip(b"\x00").decode("latin1")
    vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", MEM, o + 8)
    chars = struct.unpack_from("<I", MEM, o + 36)[0]
    ALL.append((name, vaddr, vsize, rawptr, rawsize, chars))
CODE = [(n, vaddr, rawptr, min(rawsize, vsize)) for (n, vaddr, vsize, rawptr, rawsize, ch) in ALL if ch & 0x20000000]

OUT = []
def emit(s=""):
    OUT.append(s)

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

# ---------------------------------------------------------------- 1) 分区
emit("=== PE 分区 ===")
emit("%-10s %-10s %-10s %-10s %-10s %s" % ("name", "vaddr", "vsize", "rawptr", "rawsize", "chars"))
for (n, vaddr, vsize, rawptr, rawsize, ch) in ALL:
    exe = "EXEC" if ch & 0x20000000 else "    "
    emit("%-10s 0x%08x 0x%08x 0x%08x 0x%08x 0x%08x %s" % (n, vaddr, vsize, rawptr, rawsize, ch, exe))
emit("")
emit("coverage test (via EXEC sections):")
for t in (0x43DE0C, 0x4E3681, 0x4E87E0, 0x49A808, 0x43DD50):
    off = va2off(t)
    emit("  0x%08x -> file off %s" % (t, ("0x%x" % off) if off is not None else "NOT MAPPED"))

# ---------------------------------------------------------------- 2) byte 写入 +0x2d
R8 = ["al", "cl", "dl", "bl", "ah", "ch", "dh", "bh"]
R32 = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]
GRP1 = ["add", "or", "adc", "sbb", "and", "sub", "xor", "cmp"]

def base_str(modrm, disp_pos_end):
    """返回 ([base描述], 是否SIB)"""
    rm = modrm & 7
    return rm

writes = []
for (name, vaddr, rawptr, size) in CODE:
    p = rawptr
    end = rawptr + size - 8
    while p < end:
        op = MEM[p]
        modrm = MEM[p + 1]
        mod = (modrm >> 6) & 3
        reg = (modrm >> 3) & 7
        rm = modrm & 7
        if mod not in (1, 2):
            p += 1
            continue
        dpos = p + 2 + (1 if rm == 4 else 0)
        if mod == 1:
            disp = struct.unpack_from("<b", MEM, dpos)[0]
            nxt = dpos + 1
        else:
            disp = struct.unpack_from("<i", MEM, dpos)[0]
            nxt = dpos + 4
        if disp != 0x2D:
            p += 1
            continue
        va = off2va(p)
        sib = "SIB" if rm == 4 else ""
        desc = None
        if op == 0x88:
            desc = "mov b [%s%s+0x2d], %s" % (R32[rm], sib, R8[reg])
        elif op == 0xC6 and reg == 0:
            desc = "mov b [%s%s+0x2d], 0x%02x" % (R32[rm], sib, MEM[nxt])
        elif op == 0x80:
            desc = "%s b [%s%s+0x2d], 0x%02x" % (GRP1[reg], R32[rm], sib, MEM[nxt])
        elif op in (0x00, 0x08, 0x20, 0x28, 0x30, 0x38):
            m = {0x00: "add", 0x08: "or", 0x20: "and", 0x28: "sub", 0x30: "xor", 0x38: "cmp"}[op]
            desc = "%s b [%s%s+0x2d], %s" % (m, R32[rm], sib, R8[reg])
        elif op == 0xFE and reg in (0, 1):
            desc = "%s b [%s%s+0x2d]" % (("inc", "dec")[reg], R32[rm], sib)
        elif op == 0xC0:
            desc = "shl/shr b [%s%s+0x2d], %d" % (R32[rm], sib, MEM[nxt])
        if desc:
            writes.append((va, desc))
        p += 1

emit("")
emit("=== byte 写入 [..+0x2d]（全形式，含 SIB/disp32）===")
emit("total: %d" % len(writes))
for va, d in writes:
    emit("  %08x  %s" % (va, d))

# ---------------------------------------------------------------- 3) and al,0xF8
emit("")
emit("=== and al, 0xF8  (24 F8) 出现处 ===")
off = MEM.find(b"\x24\xf8")
cnt = 0
andal = []
while off >= 0 and cnt < 60:
    va = off2va(off)
    if va:
        andal.append(va)
        cnt += 1
    off = MEM.find(b"\x24\xf8", off + 1)
emit("total: %d" % len(andal))
emit("  " + " ".join("0x%08x" % v for v in andal))

# ---------------------------------------------------------------- 4) 上下文
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

def window(va, before=0x80, after=0x20, maxins=140):
    start = prologue(va)
    if start is None:
        start = va - before
    off = va2off(start)
    if off is None:
        return ["  (bad addr)"]
    src = bytes(MEM[off:off + 0x7000])
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

emit("")
emit("=== 0x43dd50（唯一 byte[+0x2d] 写入所在函数）上下文 ===")
for line in window(0x43DD50, before=0x120, after=0x30, maxins=200):
    emit(line)

open(os.path.join(HERE, "_rankwrite3.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("writes=%d andal=%d  see _rankwrite3.txt" % (len(writes), len(andal)))
