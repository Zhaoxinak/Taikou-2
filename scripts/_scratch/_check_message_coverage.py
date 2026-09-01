#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_check_message_coverage.py — 分析 MESSAGE 文本字符覆盖 vs HBCHAR2 字体。

HBCHAR2 仅覆盖 348 个名称表唯一字符。
MESSAGE 文本有 ~1426 个唯一 CJK 字符。
本脚本找出缺失字符，并检查 HKCHAR/TOWNCHAR/MAPCHAR 是否补充覆盖。
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

import sys, os, json, struct
sys.path.insert(0, os.path.dirname(__file__))
from real_assets import ls11_decompress, load_lzw

DATA_ROOT = "F:/Games/Taikou2"
DUMP = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000

# ── 1. 加载 HBCHAR2 映射 ──────────────────────────────────────────────
mapping_path = _ROOT + '/scripts/_probe/font_atlas/hbchar2_mapping.json'
with open(mapping_path, "r", encoding="utf-8") as f:
    font_data = json.load(f)

hbchar2_chars = set()
for gbk_hex, glyph_idx in font_data["gbk_to_glyph"].items():
    # gbk_hex is like "b1b1" → convert to actual character
    b = bytes.fromhex(gbk_hex)
    try:
        ch = b.decode('gbk')
        hbchar2_chars.add(ch)
    except:
        pass

print(f"HBCHAR2: {len(hbchar2_chars)} unique chars mapped")

# ── 2. 提取 MESSAGE 文本唯一 CJK 字符 ────────────────────────────────
msg_chars = set()
msg_files = ["MESSAGE1.LZW", "MESSAGE2.LZW", "MESSAGE3.LZW", "MESSAGE4.LZW"]

for fname in msg_files:
    fpath = os.path.join(DATA_ROOT, fname)
    if not os.path.exists(fpath):
        print(f"  {fname}: NOT FOUND")
        continue
    raw = open(fpath, "rb").read()
    decompressed = ls11_decompress(raw)
    if not decompressed or decompressed[:4] != b"MSGX":
        print(f"  {fname}: decompress failed or not MSGX")
        continue
    
    n_msgs = struct.unpack_from("<H", decompressed, 4)[0]
    pointers = []
    for i in range(n_msgs):
        ptr = struct.unpack_from("<I", decompressed, 6 + i * 4)[0]
        pointers.append(ptr)
    pointers.append(len(decompressed))
    
    n_chars = 0
    for i in range(n_msgs):
        start = pointers[i]
        end = pointers[i + 1]
        msg_data = decompressed[start:end]
        # GBK decode
        j = 0
        while j < len(msg_data):
            b = msg_data[j]
            if b == 0:
                break
            if b < 0x80:
                j += 1  # ASCII
            elif j + 1 < len(msg_data):
                try:
                    ch = bytes([b, msg_data[j + 1]]).decode('gbk')
                    if ord(ch) > 0x7f:
                        msg_chars.add(ch)
                    j += 2
                except:
                    j += 1
            else:
                j += 1
        n_chars += 1
    
    print(f"  {fname}: {n_msgs} messages, total unique so far: {len(msg_chars)}")

print(f"\nMESSAGE total unique CJK chars: {len(msg_chars)}")

# ── 3. 计算覆盖缺口 ────────────────────────────────────────────────────
covered = msg_chars & hbchar2_chars
uncovered = msg_chars - hbchar2_chars
coverage_pct = len(covered) / len(msg_chars) * 100 if msg_chars else 0

print(f"\n{'='*60}")
print(f"Coverage Analysis")
print(f"{'='*60}")
print(f"  HBCHAR2 chars:   {len(hbchar2_chars)}")
print(f"  MESSAGE chars:   {len(msg_chars)}")
print(f"  Covered:         {len(covered)} ({coverage_pct:.1f}%)")
print(f"  Uncovered:       {len(uncovered)} ({100-coverage_pct:.1f}%)")

# Print first 50 uncovered chars
uncovered_sorted = sorted(uncovered)
print(f"\n  First 50 uncovered chars: {''.join(uncovered_sorted[:50])}")
print(f"  Last 20 uncovered chars:  {''.join(uncovered_sorted[-20:])}")

# ── 4. 检查名称表 (0x506ca8) 的完整字符集 ────────────────────────────
mem = open(DUMP, "rb").read()

def mem_read(va, size):
    off = va - BASE
    if off < 0 or off + size > len(mem):
        return b'\x00' * size
    return mem[off:off + size]

# Name table: 370 entries × 9 bytes
tbl_raw = mem_read(0x506ca8, 370 * 9)
name_chars = set()
for i in range(370):
    entry = tbl_raw[i*9:(i+1)*9]
    try:
        txt = entry.decode('gbk').rstrip('\x00')
        for ch in txt:
            if ord(ch) > 127:
                name_chars.add(ch)
    except:
        pass

print(f"\nName table (0x506ca8): {len(name_chars)} unique CJK chars")

# ── 5. 检查其他字符文件 ────────────────────────────────────────────────
# HKCHAR.LZW: 18038B compressed → ? decompressed
# Try different glyph sizes
for fname, glyph_sizes in [
    ("HKCHAR.LZW", [128, 64, 32]),
    ("TOWNCHAR.LZW", [128, 64, 32]),
    ("MAPCHAR.LZW", [128, 64, 32]),
]:
    fpath = os.path.join(DATA_ROOT, fname)
    if not os.path.exists(fpath):
        continue
    raw = open(fpath, "rb").read()
    dec = ls11_decompress(raw)
    if not dec:
        print(f"\n{fname}: LS11 decompress failed")
        continue
    
    print(f"\n{fname}: {len(raw)}B → {len(dec)}B decompressed")
    for gs in glyph_sizes:
        n = len(dec) // gs
        rem = len(dec) % gs
        if n > 0 and n < 2000:
            print(f"  {gs}B/glyph → {n} glyphs (remainder {rem}B)")

# ── 6. 检查 EXE 中的其他字符串表 ──────────────────────────────────────
# String table at 0x503af8 (mentioned in memory)
str_tbl = mem_read(0x503af8, 0x4000)  # Read a chunk
str_chars = set()
i = 0
while i < len(str_tbl):
    b = str_tbl[i]
    if b == 0:
        i += 1
        continue
    if b < 0x80:
        i += 1
    elif i + 1 < len(str_tbl):
        try:
            ch = bytes([b, str_tbl[i+1]]).decode('gbk')
            if ord(ch) > 0x7f:
                str_chars.add(ch)
            i += 2
        except:
            i += 1
    else:
        i += 1

print(f"\nString table (0x503af8): {len(str_chars)} unique CJK chars")

# ── 7. 汇总：所有已知字符来源的并集 ────────────────────────────────────
all_known = hbchar2_chars | name_chars | str_chars
print(f"\nAll known char sources combined: {len(all_known)} unique chars")
print(f"  Still uncovered by all sources: {len(msg_chars - all_known)}")

still_uncovered = sorted(msg_chars - all_known)
if still_uncovered:
    print(f"  Uncovered chars: {''.join(still_uncovered[:80])}")

# Save full analysis
result = {
    "hbchar2_chars": len(hbchar2_chars),
    "message_chars": len(msg_chars),
    "covered": len(covered),
    "uncovered": len(uncovered),
    "coverage_pct": round(coverage_pct, 1),
    "name_table_chars": len(name_chars),
    "string_table_chars": len(str_chars),
    "all_known_combined": len(all_known),
    "still_uncovered": len(msg_chars - all_known),
    "uncovered_list": [f"U+{ord(c):04X} {c}" for c in still_uncovered],
}
out_path = _ROOT + '/scripts/_probe/font_atlas/message_coverage.json'
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\nSaved: {out_path}")
