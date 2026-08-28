#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全静态段 GBK 串池扫描器
=======================
教训驱动：計略中文名一直被判为「不在 EXE 静态段」，实际就在 0x5032d8 的小串池里，
只因过去只扫了 0x506ca8 / 0x504800 / 0x507b58 几张大表。
本脚本**不做任何先验假设**，把 0x500000–0x530000 全部 GBK 串抠出来并按串池分组，
再用「等距 stride」检测把定长名表识别出来。

用法：
  python scripts/_string_pool_scan.py            # 全量池报告
  python scripts/_string_pool_scan.py --tables   # 只列疑似定长名表
  python scripts/_string_pool_scan.py --grep 足轻 鱼鳞
"""
from __future__ import annotations

import os
import sys
from collections import Counter

BASE = 0x400000
IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_unpacked_mem.bin')

SCAN_LO, SCAN_HI = 0x500000, 0x530000

# GBK 双字节：lead 0x81-0xFE, trail 0x40-0xFE (排除 0x7F)
def is_gbk_lead(b): return 0x81 <= b <= 0xFE
def is_gbk_trail(b): return 0x40 <= b <= 0xFE and b != 0x7F


def extract_cjk_strings(mem):
    """抠出所有「至少 2 个 GBK 双字节字符」的串（允许混 ASCII 可见字符）。"""
    out = []
    i = SCAN_LO - BASE
    end = min(SCAN_HI - BASE, len(mem))
    while i < end:
        b = mem[i]
        if is_gbk_lead(b) and i + 1 < end and is_gbk_trail(mem[i + 1]):
            start = i
            ncjk = 0
            while i < end:
                b = mem[i]
                if is_gbk_lead(b) and i + 1 < end and is_gbk_trail(mem[i + 1]):
                    ncjk += 1
                    i += 2
                elif 0x20 <= b < 0x7F:      # 允许内嵌 ASCII（如 %4u、∶）
                    i += 1
                else:
                    break
            if ncjk >= 2:
                raw = mem[start:i]
                try:
                    txt = raw.decode('gbk')
                except UnicodeDecodeError:
                    i = start + 2
                    continue
                out.append((BASE + start, len(raw), txt))
            else:
                i = start + 2
        else:
            i += 1
    return out


def group_pools(strings, gap=64):
    """按地址间隙分池。"""
    pools, cur = [], []
    for s in strings:
        if cur and s[0] - (cur[-1][0] + cur[-1][1]) > gap:
            pools.append(cur)
            cur = []
        cur.append(s)
    if cur:
        pools.append(cur)
    return pools


def detect_stride(pool):
    """池内相邻串起始地址差；若众数占比高则判为定长表。"""
    if len(pool) < 3:
        return None, 0.0
    diffs = [pool[i + 1][0] - pool[i][0] for i in range(len(pool) - 1)]
    c = Counter(diffs)
    stride, n = c.most_common(1)[0]
    return stride, n / len(diffs)


def main():
    args = sys.argv[1:]
    only_tables = '--tables' in args
    greps = []
    if '--grep' in args:
        greps = args[args.index('--grep') + 1:]

    with open(IMG, 'rb') as f:
        mem = f.read()

    strings = extract_cjk_strings(mem)
    print(f'扫描 {SCAN_LO:#x}–{SCAN_HI:#x}：共 {len(strings)} 条 CJK 串\n')

    if greps:
        print('== 关键词命中 ==')
        hit = 0
        for va, ln, txt in strings:
            if any(g in txt for g in greps):
                print(f'  {va:#08x}  len={ln:2d}  {txt!r}')
                hit += 1
        print(f'  命中 {hit} 条\n')
        if hit:
            return

    pools = group_pools(strings)
    print(f'== 分池：{len(pools)} 个 ==\n')

    tables = []
    for p in pools:
        stride, conf = detect_stride(p)
        is_tab = stride is not None and conf >= 0.6 and 3 <= stride <= 32
        if is_tab:
            tables.append((p, stride, conf))
        if only_tables and not is_tab:
            continue
        tag = f'  ★定长表 stride={stride} 置信 {conf:.0%}' if is_tab else ''
        print(f'池 {p[0][0]:#08x}–{p[-1][0] + p[-1][1]:#08x}  {len(p)} 条{tag}')
        for va, ln, txt in p[:24]:
            print(f'    {va:#08x} len={ln:2d}  {txt!r}')
        if len(p) > 24:
            print(f'    ... 还有 {len(p) - 24} 条')
        print()

    print(f'== 疑似定长名表汇总：{len(tables)} 张 ==')
    for p, stride, conf in tables:
        names = ' / '.join(t.replace('\u3000', '') for _, _, t in p[:12])
        print(f'  {p[0][0]:#08x}  n={len(p):3d} stride={stride:2d}  {names}')


if __name__ == '__main__':
    main()
