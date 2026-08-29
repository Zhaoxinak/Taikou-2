# -*- coding: utf-8 -*-
"""set_rank(0x49a7e0) 调用者 —— 用「末条指令正好结束于 call 地址」做对齐，
保证上下文反汇编正确（capstone 遇内联数据会停，不能从远处序言起解）。
"""
import struct, os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
SZ = len(MEM)

OUT = []
def emit(s=""):
    OUT.append(s)

def insns(start, hi, maxb=0x200):
    """反汇编 [start, hi] 区间，返回 [(addr,size,mn,op)]。遇非法字节停止。"""
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

def ctx(c, span=0xC0):
    """找一个起始偏移，使反汇编末条指令正好结束于 c（即 c 处指令被正确对齐）"""
    best = []
    for off in range(c - span, c):
        seq = insns(off, c - 1)
        if seq and seq[-1][0] + seq[-1][1] == c:
            if len(seq) > len(best):
                best = seq
    return best

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

for tgt, tag in ((0x49A7E0, "set_rank(entity, rank)  [word+0x2c bit8..10]"),
                 (0x49A840, "set 2-bit field bit13..14 (value<4)")):
    cs = find_callers(tgt)
    emit("=" * 78)
    emit("调用 0x%08x  %s" % (tgt, tag))
    emit("callers: %d" % len(cs))

    rows = []
    for c in cs:
        seq = ctx(c)
        lp = None
        for (a, s, m, o) in seq:
            if m == "push":
                lp = (a, o)
        val = lp[1] if lp else "?"
        isconst = val.startswith("0x") or val.lstrip("-").isdigit()
        rows.append((c, val, isconst, seq))

    emit("")
    emit("--- 立即数（初始化/固定任命）---")
    for (c, val, ic, seq) in rows:
        if ic:
            emit("  0x%08x  push %s" % (c, val))
    emit("")
    emit("--- 计算值（晋升候选）---")
    for (c, val, ic, seq) in rows:
        if not ic:
            emit("  0x%08x  push %s" % (c, val))

    emit("")
    emit("--- 「计算值」调用点上下文（对齐反汇编）---")
    for (c, val, ic, seq) in rows:
        if ic:
            continue
        emit("")
        emit("---- call @ 0x%08x   last push: %s" % (c, val))
        for (a, s, m, o) in seq[-24:]:
            emit("  %08x  %-8s %s" % (a, m, o))
        emit("  %08x  call    0x%08x" % (c, tgt))
    emit("")

open(os.path.join(HERE, "_setrank_callers.txt"), "w", encoding="utf-8").write("\n".join(OUT))
n = len([1 for c in find_callers(0x49A7E0)])
print("done. see _setrank_callers.txt  (set_rank callers=%d)" % n)
