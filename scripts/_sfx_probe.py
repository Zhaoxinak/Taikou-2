#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_sfx_probe.py -- 音效子系统探测（草稿）：抽 play_sfx(0x4997c0) 各调用点的 ID 实参。"""
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

import os, re, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 0x400000
MEM = open(os.path.join(ROOT, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

SFX_MAIN = 0x4997c0
SFX_TBL = 0x50ba40


def rd(va, n):
    return MEM[va - BASE:va - BASE + n]


def cstr(va, maxlen=24):
    b = rd(va, maxlen)
    z = b.find(0)
    return b[:z if z >= 0 else maxlen].decode("ascii", "replace")


def disasm(va, size):
    return list(md.disasm(rd(va, size), va))


def imm(op_str):
    vals = []
    for tok in op_str.split(","):
        tok = tok.strip()
        m = re.fullmatch(r"(0x[0-9a-f]+|[0-9]+)", tok)
        if m:
            s = m.group(1)
            vals.append(int(s, 16) if s.startswith("0x") else int(s))
    return vals


# 1. 音效名表
names = []
for i in range(39):
    p = struct.unpack("<I", rd(SFX_TBL + 4 * i, 4))[0]
    names.append(cstr(p))
print("=== SFX 名表 @0x50ba40 (39 项) ===")
for i, n in enumerate(names):
    print("  [%2d] %s" % (i, n))

# 2. 找 call 0x4997c0 的站点 + 回溯 push 立即数
sites = []
for off in range(len(MEM) - 5):
    if MEM[off] != 0xE8:
        continue
    rel = struct.unpack_from("<i", MEM, off + 1)[0]
    tgt = (BASE + off + 5 + rel) & 0xFFFFFFFF
    if tgt != SFX_MAIN:
        continue
    va = BASE + off
    # 回溯反汇编：从 va-0x30 开始，取到 va
    start = va - 0x30
    ins = disasm(start, 0x30)
    pushes = []
    for i in ins:
        if i.address >= va:
            break
        if i.mnemonic == "push":
            v = imm(i.op_str)
            if v:
                pushes.append((i.address, v[0]))
    sites.append((va, pushes))

print("\n=== play_sfx 调用点 ID 分布 ===")
sites.sort()
from collections import Counter, defaultdict
byid = defaultdict(list)
variable = 0
for va, pushes in sites:
    small = [p for p in pushes if p[1] < 0x27]
    if small:
        byid[small[-1][1]].append(va)
    else:
        variable += 1
print("总调用点 %d，可定 ID %d，寄存器/变量 %d" % (len(sites), sum(len(v) for v in byid.values()), variable))
cnt = Counter({k: len(v) for k, v in byid.items()})
for i in range(39):
    print("  [%2d] %-18s 调用 %2d 次 : %s" % (
        i, names[i], cnt.get(i, 0),
        ", ".join("0x%x" % v for v in byid.get(i, [])[:8])))
