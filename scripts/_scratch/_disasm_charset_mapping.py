#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_disasm_charset_mapping.py — 深入反汇编 GBK→字形索引映射的关键函数。
目标：
  1. 0x4431a0 (glyph table cache builder) 完整逻辑
  2. 0x4432e0 (text rendering with looked-up value)
  3. 0x44395b..0x443c20 (GBK cmp al,0x81 cluster)
  4. 检查 0x51e9c0 处的查找表内容
  5. 检查 0x5030e8 / 0x5030f8 处的文件名字符串
  6. 反汇编 0x443100 完整的字符查找路径
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
from capstone import *

DUMP = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(DUMP, "rb").read()

def mem_read(va, size):
    off = va - BASE
    if off < 0 or off + size > len(mem):
        return b'\x00' * size
    return mem[off:off + size]

def disasm(va_start, size, label=""):
    off = va_start - BASE
    code = mem[off:off + size]
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  VA 0x{va_start:x}..0x{va_start+size:x} ({size} bytes)")
    print(f"{'='*70}")
    for ins in md.disasm(code, va_start):
        bhex = ' '.join(f'{b:02x}' for b in ins.bytes[:10])
        print(f"  0x{ins.address:06x}: {bhex:30s} {ins.mnemonic:8s} {ins.op_str}")

# ---- 1. Strings at 0x5030e8, 0x5030f8 ----
print("="*70)
print("  Charset filename strings")
print("="*70)
for va in [0x5030e8, 0x5030f8, 0x506bb2, 0x5034d2, 0x5034f2]:
    s = mem_read(va, 32)
    # null-terminated string
    end = s.find(b'\x00')
    if end >= 0:
        s = s[:end]
    try:
        txt = s.decode('ascii', 'replace')
    except:
        txt = str(s)
    print(f"  0x{va:06x}: {txt!r}")

# ---- 2. Table at 0x51e9c0 ----
print("\n" + "="*70)
print("  Lookup table at 0x51e9c0")
print("="*70)
tbl = mem_read(0x51e9c0, 64)
print(f"  First 64 bytes: {tbl.hex(' ')}")
# Try as uint32 LE array
print("  As u32 LE array (first 16):")
for i in range(16):
    val = struct.unpack_from("<I", tbl, i*4)[0]
    print(f"    [{i}] = 0x{val:08x} ({val})")

# ---- 3. Glyph table 0x519868 structure template (what it looks like when filled) ----
# Check the cache builder to understand the 47-byte entry layout
print("\n" + "="*70)
print("  Glyph table entry layout (47 bytes = 0x2f)")
print("="*70)
print("  Fields identified from cache builder:")
print("  [0x00..0x23] = ? (36 bytes)")
print("  [0x24] = page selector byte")
print("  [0x25..0x2c] = ? (8 bytes)")
print("  [0x2d] = flags (bits 0-2 checked: test byte [edi+0x2d], 7)")
print("  [0x2e] = ? (1 byte)")

# ---- 4. Cache builder 0x4431a0 full ----
disasm(0x4431a0, 256, "Glyph Table Cache Builder (0x4431a0)")

# ---- 5. Character lookup 0x443100 full + 0x4432e0 ----
disasm(0x443100, 160, "Character Lookup (0x443100)")

disasm(0x4432e0, 256, "Text Renderer (0x4432e0)")

# ---- 6. GBK cmp cluster 0x4439e0..0x443c20 ----
disasm(0x4439e0, 320, "GBK Character Classification (0x4439e0..0x443b20)")

# ---- 7. Also disassemble the call targets from 0x443100 ----
# 0x443e10, 0x443ca0, 0x443bd0, 0x443730
disasm(0x443e10, 128, "Charset check A (0x443e10)")
disasm(0x443ca0, 128, "Charset check B (0x443ca0)")

# ---- 8. Check what's at 0x507b85 (referenced in 0x443060) ----
s = mem_read(0x507b85, 64)
end = s.find(b'\x00')
if end >= 0:
    s = s[:end]
print(f"\n  String at 0x507b85: {s.decode('ascii', 'replace')!r}")

# ---- 9. Check the 0x516638 flag ----
flag = mem_read(0x516638, 4)
print(f"\n  Global flag at 0x516638: {flag.hex(' ')}")

# ---- 10. Scan for large u16 arrays that could be GBK→glyph tables ----
print("\n" + "="*70)
print("  Scanning for potential GBK→glyph lookup tables")
print("="*70)
# A GBK→glyph table would have entries in the range 0..1535 (HBCHAR glyph count)
# or 0..369 (glyph table entries), stored as u16 or u32
# Scan for regions where many consecutive u16 values are < 1536
best_regions = []
window = 256  # check 256 u16s at a time
for off in range(0, len(mem) - window*2, 2):
    vals = struct.unpack_from(f"<{window}H", mem, off)
    # Count how many are in range [0, 1535]
    in_range = sum(1 for v in vals if 0 < v < 1536)
    if in_range > window * 0.8:  # 80%+ in range
        va = BASE + off
        best_regions.append((va, in_range, vals[:8]))
if best_regions:
    print(f"  Found {len(best_regions)} candidate regions (>80% values < 1536)")
    for va, count, sample in best_regions[:10]:
        print(f"    0x{va:06x}: {count}/{window} in range, sample={sample}")
else:
    print("  No candidate GBK→glyph tables found (may be built at runtime)")

# Also check for u32 tables
print("\n  Scanning for u32 tables (values 0..369 range)...")
for off in range(0, len(mem) - 256*4, 4):
    vals = struct.unpack_from(f"<256I", mem, off)
    in_range = sum(1 for v in vals if 0 < v < 370)
    if in_range > 200:  # 78%+
        va = BASE + off
        print(f"    0x{va:06x}: {in_range}/256 in range [0,369], sample={vals[:8]}")
        break
