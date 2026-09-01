# -*- coding: utf-8 -*-
"""
_probe_dip6.py —
  A) 关系矩阵 0x51dc60 的绝对引用点（找写入端）
  B) 名称表 0x5080d0 两处引用 0x44cf17 / 0x47a7dd 上下文——名称索引如何算
  C) e8 调用方扫描: 0x49fd80 / 0x49fe70 / 0x49f670
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

import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def dis(va, maxins=90):
    o = va - BASE
    out = []
    for ins in md.disasm(MEM[o:o + maxins * 8], va):
        out.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        if len(out) >= maxins or ins.mnemonic == "ret":
            break
    return "\n".join(out)


def find_abs(va):
    pat = struct.pack("<I", va)
    r = []
    i = MEM.find(pat)
    while i != -1:
        r.append(BASE + i)
        i = MEM.find(pat, i + 1)
    return r


def e8_callers(va, lo=0x401000, hi=0x520000):
    """扫描 e8 rel32 且目标 == va"""
    out = []
    o = lo - BASE
    end = hi - BASE
    i = o
    while i < end - 5:
        if MEM[i] == 0xE8:
            rel = struct.unpack("<i", MEM[i + 1:i + 5])[0]
            tgt = BASE + i + 5 + rel
            if tgt == va:
                out.append(BASE + i)
        i += 1
    return out


def func_start(va):
    o = va - BASE
    lim = max(0, o - 0x500)
    i = o
    while i > lim:
        b = MEM[i]
        if b == 0xC3:
            return BASE + i + 1
        if b == 0xC2 and i + 2 < SZ:
            return BASE + i + 3
        i -= 1
    return BASE + lim


print("=" * 78)
print("### A) 关系矩阵基址 0x51dc60 / 0x51dc5f 的绝对引用")
print("=" * 78)
for va in (0x51DC60, 0x51DC5F, 0x51DC61):
    hits = find_abs(va)
    print(f"  {va:#x}: {len(hits)} 处 -> {[hex(h) for h in hits]}")

print()
print("=" * 78)
print("### B) 名称表 0x5080d0 引用点上下文")
print("=" * 78)
for h in (0x44CF17, 0x47A7DD):
    print(f"\n--- 引用 {h:#x} 所属函数 {func_start(h):#x} ---")
    print(dis(func_start(h), 110))

print()
print("=" * 78)
print("### C) 调用方 (e8 扫描)")
print("=" * 78)
for va, nm in [(0x49FD80, "关系记录查找"), (0x49FE70, "关系取值"),
               (0x49F670, "自家prov取得")]:
    cs = e8_callers(va)
    print(f"\n  {nm} {va:#x}: {len(cs)} 个调用方")
    for c in cs:
        print(f"     {c:#x}   (in func {func_start(c):#x})")
