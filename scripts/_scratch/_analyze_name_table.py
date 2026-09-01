#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_analyze_name_table.py — 深入分析名称表(0x506ca8)结构，理解9字节条目的真实格式。
同时尝试用 Unicorn 运行 0x443b60 (构建 0x51e9c0 表) 和 0x443d80 (构建 0x517838 表)。
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

import struct, os, sys
sys.path.insert(0, os.path.dirname(__file__))

DUMP = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(DUMP, "rb").read()

def mem_read(va, size):
    off = va - BASE
    if off < 0 or off + size > len(mem):
        return b'\x00' * size
    return mem[off:off + size]

# ── 1. 深入分析 9 字节条目的结构 ────────────────────────────────
print("=" * 60)
print("Deep analysis of 9-byte name table entries")
print("=" * 60)

tbl_raw = mem_read(0x506ca8, 370 * 9)

# Print raw bytes for first 55 entries (all provinces + first 6 castles)
for i in range(55):
    entry = tbl_raw[i*9:(i+1)*9]
    raw_hex = ' '.join(f'{b:02x}' for b in entry)
    try:
        txt = entry.decode('gbk', errors='replace')
    except:
        txt = "??"
    null_count = sum(1 for b in entry if b == 0)
    first_nonzero = next((j for j, b in enumerate(entry) if b != 0), 9)
    print(f"  [{i:3d}] hex={raw_hex:30s} gb={txt!r:15s} nulls={null_count} first_nz={first_nonzero}")

# ── 2. 分析条目中的非零字节偏移模式 ────────────────────────────
print("\n" + "=" * 60)
print("Non-zero byte offset distribution in entries")
print("=" * 60)

offset_counts = [0] * 9  # count how many entries have non-zero byte at each offset
for i in range(370):
    entry = tbl_raw[i*9:(i+1)*9]
    for j in range(9):
        if entry[j] != 0:
            offset_counts[j] += 1

print("  Non-zero byte counts per offset:")
for j in range(9):
    bar = "#" * (offset_counts[j] // 5)
    print(f"    offset {j}: {offset_counts[j]:3d} entries {bar}")

# ── 3. 检查名称字符串长度分布 ──────────────────────────────────
print("\n" + "=" * 60)
print("Name string length distribution")
print("=" * 60)

length_counts = {}
for i in range(370):
    entry = tbl_raw[i*9:(i+1)*9]
    # Find the first null byte
    null_pos = 9
    for j in range(9):
        if entry[j] == 0:
            null_pos = j
            break
    # GBK char count = null_pos / 2 (rounded up)
    char_count = (null_pos + 1) // 2
    if char_count not in length_counts:
        length_counts[char_count] = 0
    length_counts[char_count] += 1

print("  Character count distribution:")
for cnt in sorted(length_counts.keys()):
    bar = "#" * (length_counts[cnt] // 2)
    print(f"    {cnt} chars: {length_counts[cnt]:3d} entries {bar}")

# ── 4. 检查 0x443b60 函数：构建 0x51e9c0 表 ──────────────────
print("\n" + "=" * 60)
print("0x443b60 (GBK Lookup A) — disassemble")
print("=" * 60)

from capstone import *

def disasm(va_start, size, label=""):
    off = va_start - BASE
    code = mem[off:off + size]
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    print(f"\n  {label} (0x{va_start:x}..0x{va_start+size:x})")
    for ins in md.disasm(code, va_start):
        bhex = ' '.join(f'{b:02x}' for b in ins.bytes[:8])
        print(f"  0x{ins.address:06x}: {bhex:24s} {ins.mnemonic:8s} {ins.op_str}")

disasm(0x443b60, 256, "0x443b60 GBK Lookup A")

# ── 5. 检查 0x443d80 函数：构建 0x517838 表 ──────────────────
disasm(0x443d80, 256, "0x443d80 Get Char Code B")

# ── 6. 检查 0x45e3e0 函数：获取字符码 ─────────────────────────
disasm(0x45e3e0, 256, "0x45e3e0 Get Character Code")

# ── 7. 检查 0x443100 函数：字符查找入口 ──────────────────────
disasm(0x443100, 128, "0x443100 Character Lookup Entry")

# ── 8. 检查 0x4eb5c0 函数（Font Init Loop 中调用）────────────
disasm(0x4eb5c0, 128, "0x4eb5c0 Font Init Helper")

# ── 9. 检查 0x4432e0 函数：渲染 ──────────────────────────────
disasm(0x4432e0, 128, "0x4432e0 Render")
