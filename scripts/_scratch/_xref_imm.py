# -*- coding: utf-8 -*-
"""太阁2 — 在映像中按「4 字节 LE 立即数」扫描对某全局 VA 的引用，并反汇编命中点附近指令。
用法：python _xref_imm.py 0x521aa8 0x506c54 0x513ff6 0x513ff8
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

import sys, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

def refs_va(target):
    le = target.to_bytes(4, "little")
    hits = []
    off = 0
    while True:
        idx = MEM.find(le, off)
        if idx < 0: break
        hits.append(idx); off = idx + 1
    return hits

def va_at(off):
    return BASE + off

def disasm_at(off, n=4):
    try:
        code = MEM[off:off+64]
    except Exception:
        return []
    rows = []
    for ins in md.disasm(code, BASE + off):
        rows.append(ins)
        if len(rows) >= n: break
    return rows

def fmt(ins):
    bs = " ".join("%02x" % x for x in ins.bytes)
    return "%08x  %-20s %s %s" % (ins.address, bs, ins.mnemonic, ins.op_str)

for arg in sys.argv[1:]:
    t = int(arg, 16) if arg.lower().startswith("0x") else int(arg)
    print("===== xref -> %#x =====" % t)
    hits = refs_va(t)
    if not hits:
        print("  (no raw 4-byte LE reference found)")
        continue
    seen = set()
    for h in hits:
        # 候选指令起点：h-2, h-1, h（覆盖 A1/A3 与 modrm 89/8B .. 05）
        for start in (h-2, h-1, h):
            if start < 0 or start in seen: continue
            rows = disasm_at(start, 1)
            if not rows: continue
            ins = rows[0]
            txt = (ins.mnemonic + " " + ins.op_str)
            # capstone 把绝对地址印成 0xNNNNNNNN（无前导零）
            if ("0x%x" % t) in txt:
                seen.add(start)
                print("  @%08x  %s" % (start, fmt(ins)))
    print("  (%d raw hits)" % len(hits))
