#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量反汇编剩余序列化器，自动提取：目标基址 / 字段写偏移序列 / 循环次数。"""
import re, sys, json
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

# 段 -> (序列化器, 段长)
SERS = [
    ('S5',  0x47e5a0,  180),
    ('S6',  0x47e770,   46),
    ('S7',  0x47ea80, 3200),
    ('S8',  0x47ebb0,  360),
    ('S9',  0x47ecb0,   80),
    ('S10', 0x47ed10,  120),
    ('S12', 0x47ee50,  160),
    ('S13', 0x47ef00, 2280),
    ('S15', 0x47f0a0,   25),
    ('S16', 0x47f1b0,   40),
    ('S17', 0x47f210,  133),
]
BASE_RE = re.compile(r'mov\s+(esi|edi|ebx|eax),\s*(0x51[0-9a-f]{4})')
LOOP_RE = re.compile(r'mov\s+(ebx|edi|esi|ecx),\s*(0x[0-9a-f]+)|\bpush\s+(0x[0-9a-f]+)')
DEST_RE = re.compile(r'(?:lea|mov)\s+\w+,\s*\[(esi|edi|ebx|eax)\s*([+-])\s*(0x[0-9a-f]+)\]')


def dis(va, nbytes=320):
    off = va - BASE
    out = []
    for ins in md.disasm(IMG[off:off + nbytes], va):
        out.append((ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic in ('ret', 'retn'):
            break
    return out


result = {}
for name, va, ln in SERS:
    code = dis(va)
    print(f'\n{"="*70}\n=== {name}  0x{va:x}  ({ln}B) ===')
    for a, m, o in code:
        print(f'0x{a:x}  {m}  {o}')
    # 摘要
    bases = set()
    dests = []
    counts = []
    for a, m, o in code:
        g = BASE_RE.search(f'{m} {o}')
        if g: bases.add(int(g.group(2), 16))
        d = DEST_RE.search(o)
        if d:
            reg, sign, val = d.groups()
            v = int(val, 16)
            dests.append((reg, -v if sign == '-' else v, a))
        if m == 'mov' and re.match(r'(ebx|edi|esi|ecx),\s*0x', o):
            counts.append(int(o.split(',')[1].strip(), 16))
    if bases:
        print(f'  >>> 基址候选: {[hex(b) for b in sorted(bases)]}')
    if dests:
        seq = [f'{reg}{"-" if v<0 else "+"}{abs(v):#x}' for reg, v, a in dests]
        print(f'  >>> 字段写偏移序列 ({len(dests)}): {" ".join(seq)}')
    if counts:
        print(f'  >>> 立即数(含循环计数): {[hex(c) for c in counts]}')
    result[name] = {'func': hex(va), 'len': ln,
                    'bases': [hex(b) for b in sorted(bases)],
                    'dests': [[r, v] for r, v, a in dests],
                    'consts': [hex(c) for c in counts]}
json.dump(result, open('scripts/_ser_disasm.json', 'w'), indent=1)
print('\nsaved scripts/_ser_disasm.json')
