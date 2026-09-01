#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用严格 xref（指令包含判定）查各段基址的消费方，据调用上下文给表定名。"""
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

import struct, pickle, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False


def build():
    try:
        return pickle.load(open(_ROOT + '/scripts/_insn_addrs.pkl', 'rb'))
    except Exception:
        pass
    starts = set(); n = len(IMG)
    for i in range(n - 5):
        if IMG[i] == 0xE8:
            rel = struct.unpack('<i', IMG[i + 1:i + 5])[0]
            t = i + 5 + rel
            if 0 <= t < n: starts.add(t)
    insn = {}
    for s in sorted(starts):
        off = s; end = min(s + 0x4000, n)
        for ins in md.disasm(IMG[off:end], BASE + off):
            insn[off] = (ins.size, f'{ins.mnemonic} {ins.op_str}')
            off += ins.size
            if ins.mnemonic in ('ret', 'retn', 'retf', 'hlt', 'ud2', 'int3'): break
            if off >= end: break
    pickle.dump(insn, open(_ROOT + '/scripts/_insn_addrs.pkl', 'wb'))
    return insn


INSN = build()


def xref(imm):
    pat = struct.pack('<I', imm); out = []; off = 0
    while True:
        i = IMG.find(pat, off)
        if i < 0: break
        for j in range(max(0, i - 7), i + 1):
            if j in INSN:
                sz, txt = INSN[j]
                if j < i < j + sz or (j == i and sz >= 4):
                    out.append(j); break
        off = i + 1
    return out


TABLES = [
    ('S5',  0x5197b0, '6 x 30B'),
    ('S6',  0x516610, '1 x 46B (单条)'),
    ('S7',  0x516a28, '200 x 16B (全 0)'),
    ('S8',  0x517850, '30 x 12B'),
    ('S9',  0x519238, '40 x WORD'),
    ('S10', 0x5176a8, '60 x WORD'),
    ('S12', 0x517728, '20 x 12B (物品副池)'),
    ('S13', 0x5185b6, '20 x 114B (全 ff)'),
    ('S16', 0x519680, '20 x WORD'),
    ('S17', 0x517c70, '133B (EOF 填充)'),
]

for name, base, desc in TABLES:
    hits = []
    for delta in range(-4, 5):          # 关键：连扫 base±1..±4
        hits += [(j, delta) for j in xref(base + delta)]
    hits = sorted(set(hits))
    print(f"\n=== {name}  base 0x{base:x}  ({desc})  -> {len(hits)} 处引用 ===")
    seen = set()
    for j, delta in hits[:14]:
        sz, txt = INSN[j]
        key = (txt, delta)
        if key in seen: continue
        seen.add(key)
        tag = f'[base{delta:+d}]' if delta else '[base]'
        # 向后取 6 条看上下文
        ctx = []
        o = j
        for _ in range(6):
            if o in INSN:
                s2, t2 = INSN[o]; ctx.append(t2); o += s2
            else: break
        print(f"  0x{BASE+j:x} {tag:<8} {txt}")
        print(f"      … {' | '.join(ctx[1:5])}")
