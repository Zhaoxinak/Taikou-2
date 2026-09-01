# -*- coding: utf-8 -*-
"""修正映射：_unpacked_mem.bin 是平坦内存映像，off = va - 0x400000。
（promo_ref.py 即以此映射读出 9 个職位名并 11/11 通过，可证。）
本脚本用正确映射全文件重扫。
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

def off2va(off):
    return BASE + off

def va2off(va):
    return va - BASE

R8 = ["al", "cl", "dl", "bl", "ah", "ch", "dh", "bh"]
R16 = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
R32 = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]
GRP1 = ["add", "or", "adc", "sbb", "and", "sub", "xor", "cmp"]

OUT = []
def emit(s=""):
    OUT.append(s)

emit("file size = 0x%x (%d bytes)   -> VA 0x400000 .. 0x%x"
     % (SZ, SZ, BASE + SZ))

# 抽样验证映射
emit("")
emit("=== 映射抽样（应为有效 GBK 串 / 可读指针）===")
for va in (0x50D850, 0x519868, 0x51EB88):
    o = va2off(va)
    emit("  0x%08x -> off 0x%x  bytes=%s" % (va, o, MEM[o:o + 16].hex()))

# ---------------------------------------------------------------- 扫描器
def scan_disp(disp, width16):
    """返回 [(va, desc)]，覆盖 mod=01/02、rm==4 SIB 形式。全文件扫描。"""
    res = []
    p = 0x1000
    end = SZ - 8
    while p < end:
        if width16:
            if MEM[p] != 0x66:
                p += 1
                continue
            op = MEM[p + 1]
            modrm = MEM[p + 2]
        else:
            op = MEM[p]
            modrm = MEM[p + 1]
        mod = (modrm >> 6) & 3
        reg = (modrm >> 3) & 7
        rm = modrm & 7
        if mod not in (1, 2):
            p += 1
            continue
        dpos = p + (3 if width16 else 2) + (1 if rm == 4 else 0)
        if mod == 1:
            disp = struct.unpack_from("<b", MEM, dpos)[0]
            nxt = dpos + 1
        else:
            disp = struct.unpack_from("<i", MEM, dpos)[0]
            nxt = dpos + 4
        if disp != disp_target:
            p += 1
            continue
        va = off2va(p)
        sib = "+sib" if rm == 4 else ""
        desc = None
        if width16:
            if op == 0x89:
                desc = "mov w [%s%s+0x%02x], %s" % (R32[rm], sib, disp, R16[reg])
            elif op == 0xC7 and reg == 0:
                desc = "mov w [%s%s+0x%02x], 0x%x" % (R32[rm], sib, disp, struct.unpack_from("<H", MEM, nxt)[0])
            elif op in (0x01, 0x09, 0x11, 0x19, 0x21, 0x29, 0x31):
                m = {0x01: "add", 0x09: "or", 0x11: "adc", 0x19: "sbb", 0x21: "and", 0x29: "sub", 0x31: "xor"}[op]
                desc = "%s w [%s%s+0x%02x], %s" % (m, R32[rm], sib, disp, R16[reg])
            elif op == 0x81:
                desc = "%s w [%s%s+0x%02x], 0x%x" % (GRP1[reg], R32[rm], sib, disp, struct.unpack_from("<H", MEM, nxt)[0])
            elif op == 0x83:
                desc = "%s w [%s%s+0x%02x], %d" % (GRP1[reg], R32[rm], sib, disp, struct.unpack_from("<b", MEM, nxt)[0])
        else:
            if op == 0x88:
                desc = "mov b [%s%s+0x%02x], %s" % (R32[rm], sib, disp, R8[reg])
            elif op == 0xC6 and reg == 0:
                desc = "mov b [%s%s+0x%02x], 0x%02x" % (R32[rm], sib, disp, MEM[nxt])
            elif op == 0x80:
                desc = "%s b [%s%s+0x%02x], 0x%02x" % (GRP1[reg], R32[rm], sib, disp, MEM[nxt])
            elif op in (0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38):
                m = {0x00: "add", 0x08: "or", 0x10: "adc", 0x18: "sbb", 0x20: "and", 0x28: "sub", 0x30: "xor", 0x38: "cmp"}[op]
                desc = "%s b [%s%s+0x%02x], %s" % (m, R32[rm], sib, disp, R8[reg])
            elif op == 0xFE and reg in (0, 1):
                desc = "%s b [%s%s+0x%02x]" % (("inc", "dec")[reg], R32[rm], sib, disp)
            elif op == 0xC0:
                desc = "shift b [%s%s+0x%02x], %d" % (R32[rm], sib, disp, MEM[nxt])
        if desc:
            res.append((va, desc))
        p += 1
    return res

def prologue(va):
    off = va2off(va)
    if off is None or off < 0 or off >= SZ:
        return None
    lo = max(0, off - 0x4000)
    best = None
    for sig in (b"\x55\x8b\xec", b"\x55\x89\xe5", b"\x53\x8b\xdc", b"\x56\x8b\xf1"):
        q = MEM.rfind(sig, lo, off)
        if q > 0 and (best is None or q > best):
            best = q
    return off2va(best) if best else None

def window(va, before=0x90, after=0x20, maxins=200):
    start = prologue(va)
    if start is None:
        start = va - before
    off = va2off(start)
    if off is None or off < 0 or off >= SZ:
        return ["  (bad addr)"]
    src = bytes(MEM[off:off + 0x8000])
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

results = {}
for disp_target, w16, label in ((0x2D, False, "byte 写 [..+0x2d]"),
                                (0x2C, True, "word 写 [..+0x2c]")):
    disp_target = disp_target
    r = scan_disp(disp_target, w16)
    results[label] = r
    emit("")
    emit("=== %s （全文件，正确映射）===" % label)
    emit("total: %d" % len(r))
    for va, d in r:
        emit("  %08x  %s" % (va, d))

# and al,0xF8
emit("")
emit("=== and al,0xF8 (24 F8) 全文件 ===")
off = MEM.find(b"\x24\xf8")
andal = []
while off >= 0:
    if off >= 0x1000:
        andal.append(off2va(off))
    off = MEM.find(b"\x24\xf8", off + 1)
emit("total: %d" % len(andal))
emit("  " + " ".join("0x%08x" % v for v in andal))

# 关键函数上下文
emit("")
for va, tag in ((0x43DE0C, "0x43de0c mov b [esi+0x2d], al （此前唯一 byte 写）"),):
    emit("=== %s ===" % tag)
    for line in window(va):
        emit(line)

open(os.path.join(HERE, "_rankwrite4.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("size=0x%x  2d=%d  2c16=%d  andal=%d" % (SZ, len(results["byte 写 [..+0x2d]"]), len(results["word 写 [..+0x2c]"]), len(andal)))
