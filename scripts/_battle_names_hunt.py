#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合戦相关中文名表 —— 精确列举 + xref 定性
========================================
由 `_string_pool_scan.py` 命中的三处候选出发：
  0x5037e0  总大将/第二军/…/城门     → 疑「部队槽名 + 战场设施名」
  0x5099d8  统御/武力/骑马/洋枪       → 疑战斗属性名
  0x50bfe8  步兵/骑兵/洋枪/城守备     → 疑 **兵种名**（长期缺口！）
另外 0x50bfd0 之前有一段 byte 数组（值 0..3）疑「图形 id → 兵种类别」映射。

本脚本：
 1) 变长 null 结尾串精确列举（不假设 stride）
 2) 对每个候选基址做全镜像绝对立即数 xref
 3) 反汇编每个引用点周围指令，判定索引来源
"""
from __future__ import annotations

import os
import struct
import sys

from capstone import *
from capstone.x86 import *

BASE = 0x400000
IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_unpacked_mem.bin')
mem = open(IMG, 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

CODE_LO, CODE_HI = 0x401000, 0x500000


def rd(va, n):
    return mem[va - BASE: va - BASE + n]


def list_strings(lo, hi, label):
    """列出 [lo,hi) 内所有 null 结尾串（含空串位置），精确 VA。"""
    print(f'\n=== {label}  {lo:#x}..{hi:#x} ===')
    va = lo
    while va < hi:
        end = va
        while end < hi and mem[end - BASE] != 0:
            end += 1
        raw = rd(va, end - va)
        if raw:
            try:
                txt = raw.decode('gbk')
                mark = ''
            except UnicodeDecodeError:
                txt = repr(raw)
                mark = ' (非GBK)'
            print(f'  {va:#08x} +{end - va}B  {txt!r}{mark}')
        va = end + 1


def xrefs(target):
    """全镜像找 4 字节小端 == target 的位置（绝对立即数/指针）。"""
    pat = struct.pack('<I', target)
    out, i = [], 0
    while True:
        i = mem.find(pat, i)
        if i < 0:
            break
        out.append(BASE + i)
        i += 1
    return out


def find_func_start(va, calls):
    """在 call-target 集合里找 <= va 的最大者（本镜像唯一可靠的函数边界法）。"""
    best = None
    for c in calls:
        if c <= va and (best is None or c > best):
            best = c
    return best


def all_call_targets():
    tg = set()
    off = CODE_LO - BASE
    end = CODE_HI - BASE
    buf = mem[off:end]
    i = 0
    while i < len(buf) - 5:
        if buf[i] == 0xE8:
            rel = struct.unpack_from('<i', buf, i + 1)[0]
            t = CODE_LO + i + 5 + rel
            if CODE_LO <= t < CODE_HI:
                tg.add(t)
        i += 1
    return tg


def disasm_around(va, back=32, fwd=24):
    """在 va 附近线性反汇编（起点回退对齐尝试）。"""
    for pad in range(back, -1, -1):
        start = va - pad
        code = rd(start, pad + fwd)
        ins = list(md.disasm(code, start))
        if any(i.address == va for i in ins):
            return ins
    return list(md.disasm(rd(va, fwd), va))


def probe(name, target, calls):
    refs = [r for r in xrefs(target) if CODE_LO <= r < CODE_HI]
    print(f'\n### {name} {target:#x} —— {len(refs)} 处代码 xref')
    for r in refs[:12]:
        fn = find_func_start(r - 3, calls)
        ins = disasm_around(r - 3)
        print(f'  ref@{r:#08x}  (func {fn:#x})' if fn else f'  ref@{r:#08x}')
        for i in ins:
            flag = '  <<<' if i.address <= target_in(i, target) else ''
            print(f'      {i.address:#08x}  {i.mnemonic:<7s} {i.op_str}{flag}')


def target_in(i, target):
    for op in i.operands:
        if op.type == X86_OP_MEM and op.mem.disp == target:
            return i.address
        if op.type == X86_OP_IMM and op.imm == target:
            return i.address
    return -1


def cli():
    """python _battle_names_hunt.py -x 0x50953c 0x50b6ba ...  → 只做 xref probe"""
    vas = [int(a, 0) for a in sys.argv[2:]]
    print('[*] 建立 call-target 集合 ...')
    calls = all_call_targets()
    for va in vas:
        probe(f'表{va:#x}', va, calls)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '-x':
        cli()
        sys.exit(0)
    list_strings(0x5037e0, 0x503860, '合戦部队/设施名池')
    list_strings(0x5099c0, 0x509ab0, '战斗属性名池')
    list_strings(0x50bfe0, 0x50c010, '兵种名池')

    print('\n=== 0x50bfa0..0x50bfe8 前置 byte 数组 ===')
    arr = rd(0x50bfa0, 0x50bfe8 - 0x50bfa0)
    for k in range(0, len(arr), 16):
        print(f'  {0x50bfa0 + k:#08x}  ' + ' '.join(f'{b:02x}' for b in arr[k:k + 16]))

    print('\n[*] 建立 call-target 集合 ...')
    calls = all_call_targets()
    print(f'    {len(calls)} 个函数起点')

    for nm, va in [('部队/设施名表', 0x5037e0),
                   ('战斗属性名A', 0x5099d8),
                   ('战斗属性名B', 0x509a78),
                   ('兵种名表', 0x50bfe8),
                   ('兵种类别映射?', 0x50bfd0)]:
        probe(nm, va, calls)
