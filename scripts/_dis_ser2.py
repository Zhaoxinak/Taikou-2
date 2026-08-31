#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提取各序列化器的「读宽 → 写偏移」映射（读顺序即流顺序）。

坑提醒：capstone 对 <10 的位移量输出十进制（[esi+5]）而非 [esi+0x5]，正则须两者都吃。
另：代码里 `mov esi, X` 的 X 通常是「真基址 + 首字段偏移」，首字段写在 [esi-k]，
    故真基址 = X - k（城表：X=0x51eb8c, 首字段 [esi-4] ⇒ 真基址 0x51eb88）。
"""
import re, json
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

BYTE_RD = 0x47d910   # 1B
WORD_RD = 0x47d930   # 2B

SERS = [
    ('S5',  0x47e5a0,  180), ('S6', 0x47e770,   46), ('S7', 0x47ea80, 3200),
    ('S8',  0x47ebb0,  360), ('S9', 0x47ecb0,   80), ('S10', 0x47ed10, 120),
    ('S12', 0x47ee50,  160), ('S13', 0x47ef00, 2280), ('S15', 0x47f0a0,  25),
    ('S16', 0x47f1b0,   40), ('S17', 0x47f210,  133),
]

IMM = r'(?:0x[0-9a-f]+|\d+)'
DEST_RE = re.compile(rf'\[(esi|edi|ebx|eax|ecx)\s*([+-])\s*({IMM})\]')
BASE_RE = re.compile(rf'mov\s+(esi|edi|ebx|eax|ecx),\s*(0x51[0-9a-fA-F]{{4}})')


def parse_imm(s):
    return int(s, 16) if s.lower().startswith('0x') else int(s)


out = {}
for name, va, ln in SERS:
    off = va - BASE
    ins_list = []
    for ins in md.disasm(IMG[off:off + 400], va):
        ins_list.append((ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic in ('ret', 'retn'):
            break

    # 收集：基址寄存器装入 / 目标偏移 / 读调用
    base_reg, base_val = None, None
    pending_dest = None
    fields = []        # (width, dest_off_relative_to_base_reg)
    consts = []
    for a, m, o in ins_list:
        g = BASE_RE.search(f'{m} {o}')
        if g:
            base_reg, base_val = g.group(1), int(g.group(2), 16)
        d = DEST_RE.search(o)
        if d and base_reg and d.group(1) == base_reg:
            v = parse_imm(d.group(3))
            pending_dest = -v if d.group(2) == '-' else v
        if m == 'call':
            tgt = None
            try:
                tgt = int(o.split()[0], 16)
            except Exception:
                pass
            if tgt in (BYTE_RD, WORD_RD) and pending_dest is not None:
                fields.append((2 if tgt == WORD_RD else 1, pending_dest))
                pending_dest = None
        if m == 'mov' and re.match(rf'(ebx|edi|esi|ecx|ebp),\s*{IMM}$', o):
            consts.append(parse_imm(o.split(',')[1].strip()))

    print(f'\n=== {name}  0x{va:x}  ({ln}B) ===')
    if base_val is not None:
        print(f'  基址寄存器 {base_reg} = 0x{base_val:x}')
    if consts:
        print(f'  立即数: {[hex(c) for c in consts]}')
    if fields:
        print(f'  字段序列 ({len(fields)}):')
        run = 0
        for w, d in fields:
            print(f'     [{run:3d}] {"W(2B)" if w==2 else "B(1B)"} -> [{base_reg}{d:+#x}]')
            run += w
        print(f'     合计 {run}B/记录')
    out[name] = {'func': hex(va), 'len': ln, 'base_reg': base_reg,
                 'base_val': hex(base_val) if base_val else None,
                 'fields': fields, 'consts': [hex(c) for c in consts]}
json.dump(out, open('scripts/_ser_fields.json', 'w'), indent=1)
print('\nsaved scripts/_ser_fields.json')
