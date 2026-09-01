# -*- coding: utf-8 -*-
"""
_probe_dip11.py — 列出两个 setter 的全部调用方并按区域分组，
重点反汇编【评议/外交模块 0x4c0000..0x4cffff】内的调用点。
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


def dis(va, maxins=240):
    o = va - BASE
    out = []
    for ins in md.disasm(MEM[o:o + maxins * 8], va):
        out.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        if len(out) >= maxins or ins.mnemonic == "ret":
            break
    return "\n".join(out)


def func_start(va):
    o = va - BASE
    lim = max(0, o - 0x900)
    i = o
    while i > lim:
        b = MEM[i]
        if b == 0xC3:
            return BASE + i + 1
        if b == 0xC2 and i + 2 < SZ:
            return BASE + i + 3
        i -= 1
    return BASE + lim


def e8_callers(va, lo=0x401000, hi=0x600000):
    out = []
    i = lo - BASE
    end = hi - BASE - 5
    while i < end:
        if MEM[i] == 0xE8:
            rel = struct.unpack("<i", MEM[i + 1:i + 5])[0]
            if BASE + i + 5 + rel == va:
                out.append(BASE + i)
        i += 1
    return out


def region(va):
    return va & 0xFFF0000


for va, nm in [(0x49FE40, "set外交関係8级"), (0x49FF10, "set主从関係4级")]:
    cs = e8_callers(va)
    print("=" * 78)
    print(f"### {nm} {va:#x} —— {len(cs)} 个调用方")
    print("=" * 78)
    groups = {}
    for c in cs:
        groups.setdefault(region(c), []).append(c)
    for r in sorted(groups):
        print(f"  {r:#x}: " + " ".join(hex(x) for x in groups[r]))

print()
print("#" * 78)
print("# 外交/评议模块 (0x4c0000..0x4cffff) 内的调用点全文")
print("#" * 78)
seen = set()
for va, nm in [(0x49FE40, "set外交8级"), (0x49FF10, "set主从4级")]:
    for c in e8_callers(va):
        if not (0x4C0000 <= c < 0x4D0000):
            continue
        fs = func_start(c)
        if fs in seen:
            continue
        seen.add(fs)
        print(f"\n========== func {fs:#x}  (含 call {nm} @{c:#x}) ==========")
        print(dis(fs, 240))
