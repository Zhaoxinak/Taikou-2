#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对未名表基址做「读/写」分类：找出所有 WRITE 点，从写入值反推字段语义。

方法：对 base±1..±4 做严格 xref（指令包含判定），逐条看操作数落在
  · 源位置（如 `mov eax,[0x516a28]`）      -> READ
  · 目的位置（如 `mov [0x516a28+eax],dx`） -> WRITE  ★ 关键
  · 仅参与地址计算（`add edx,0x516a28`）   -> ADDR（其后通常紧跟读或写）
"""
import struct, pickle, bisect, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
INSN = pickle.load(open('scripts/_insn_addrs.pkl', 'rb'))
ORDER = sorted(INSN)


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
    return sorted(set(out))


MEM_RE = __import__('re').compile(r'\[\s*0x51[0-9a-fA-F]{4}')


def classify(ins_txt):
    m, o = (ins_txt.split(None, 1) + [''])[:2]
    if m in ('mov', 'movzx', 'movsx', 'lea', 'add', 'sub', 'cmp', 'inc', 'dec'):
        parts = o.split(',')
        if len(parts) == 2:
            dst, src = parts[0].strip(), parts[1].strip()
            if MEM_RE.search(dst):
                return 'WRITE', dst, src
            if MEM_RE.search(src):
                return 'READ', dst, src
    if m in ('push',) and MEM_RE.search(o):
        return 'ADDR', o, ''
    return 'OTHER', m, o


def ctx(j, nb=6, na=8):
    k = bisect.bisect_left(ORDER, j)
    return ([INSN[s][1] for s in ORDER[max(0, k - nb):k]],
            [INSN[s][1] for s in ORDER[k + 1:k + 1 + na]])


def report(name, base, span=4, show=10):
    sites = []
    for d in range(-span, span + 1):
        sites += [(j, d) for j in xref(base + d)]
    sites = sorted(set(sites))
    print(f'\n{"#"*72}\n### {name}  base 0x{base:x}  (±{span} 共 {len(sites)} 处)')
    kinds = {}
    for j, d in sites:
        k, a, b = classify(INSN[j][1])
        kinds.setdefault(k, []).append((j, d, a, b))
    print('  分类:', {k: len(v) for k, v in sorted(kinds.items())})
    for kind in ('WRITE', 'READ', 'ADDR'):
        v = kinds.get(kind, [])
        if not v: continue
        print(f'\n  ---- {kind} ({len(v)} 处) ----')
        for j, d, a, b in v[:show]:
            tag = f'base{d:+d}' if d else 'base'
            print(f'  0x{BASE+j:x} [{tag}] {INSN[j][1]}')
            if kind == 'WRITE':
                bb, aa = ctx(j, 5, 3)
                print(f'        前: {" | ".join(bb[-4:])}')


if __name__ == '__main__':
    T = [('S7  @0x516a28 (200×16B, 全0)', 0x516a28),
         ('S5  @0x5197b0 (6×30B, 全空)', 0x5197b0),
         ('S13 @0x5185b6 (20×114B, 全ff)', 0x5185b6),
         ('S6  @0x516610 (1×46B, 热全局)', 0x516610)]
    if len(sys.argv) > 1:
        T = [(f'0x{int(a,16):x}', int(a, 16)) for a in sys.argv[1:]]
    for nm, b in T:
        report(nm, b, span=int(sys.argv[0] and 4 or 4))
