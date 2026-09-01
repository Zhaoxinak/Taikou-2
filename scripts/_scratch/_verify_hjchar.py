#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_verify_hjchar.py — 验证 HJCHAR.LZW 是不是 GBK 码序字体的第二部分。

HKCHAR 覆盖 0xB0A1-0xBEAE (1330 字形)。
HJCHAR 有 1202 字形 (32B/glyph) = 可能从 0xBEAF 开始覆盖 0xBEAF-0xC3CF。
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

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from real_assets import ls11_decompress
from PIL import Image, ImageDraw, ImageFont

DATA_ROOT = "F:/Games/Taikou2"

sys_font_path = None
for fp in ["C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simsun.ttc"]:
    if os.path.exists(fp):
        sys_font_path = fp
        break

def render_glyph_32(data, glyph_idx):
    base = glyph_idx * 32
    if base + 32 > len(data):
        return [0] * 256
    bm = [0] * 256
    for y in range(16):
        row = (data[base + y*2] << 8) | data[base + y*2 + 1]
        for x in range(16):
            if (row >> (15 - x)) & 1:
                bm[y * 16 + x] = 1
    return bm

def gbk_index_to_char(idx, start=0xB0A1):
    """Convert index 0..N to GBK character starting from start code"""
    start_lead = (start >> 8) & 0xFF
    start_trail = start & 0xFF
    
    lead = start_lead + ((start_trail - 0xA1 + idx) // 94)
    trail = 0xA1 + ((start_trail - 0xA1 + idx) % 94)
    if trail > 0xFE:
        trail = 0x40 + (trail - 0xFE)
        lead += 1
    try:
        return bytes([lead, trail]).decode('gbk')
    except:
        return None

# Load HJCHAR
raw = open(os.path.join(DATA_ROOT, "HJCHAR.LZW"), "rb").read()
dec = ls11_decompress(raw)
n_glyphs = len(dec) // 32
print(f"HJCHAR: {len(raw)}B → {len(dec)}B, {n_glyphs} glyphs × 32B")

# Render first 5 glyphs and test different start points
sys_font = ImageFont.truetype(sys_font_path, 16) if sys_font_path else None

# Test 3 hypotheses:
# A: HJCHAR starts at 0xB0A1 (same as HKCHAR)
# B: HJCHAR starts at 0xBEAF (right after HKCHAR ends at 0xBEAE)
# C: HJCHAR starts at 0xC3D0 (right after hypothetical end of 1202 from 0xBEAF)

hypotheses = [
    ("A_same_as_HKCHAR", 0xB0A1),
    ("B_after_HKCHAR", 0xBEAF),
    ("C_other", 0xC3D0),
]

for hyp_name, start_code in hypotheses:
    img = Image.new("RGB", (5 * 20, 2 * 20), (64, 64, 64))
    draw = ImageDraw.Draw(img)
    
    for i in range(5):
        bm = render_glyph_32(dec, i)
        cx = i * 20
        for y in range(16):
            for x in range(16):
                if bm[y * 16 + x]:
                    draw.point((cx + x, y), fill=(255, 255, 255))
        
        ch = gbk_index_to_char(i, start_code)
        if ch:
            gbk_hex = f"0x{ch.encode('gbk').hex().upper()}"
            if sys_font:
                draw.text((cx, 0), ch, fill=(255, 255, 0), font=sys_font)
    
    out = f"scripts/_probe/font_atlas/HJCHAR_test_{hyp_name}.png"
    img.save(out)
    print(f"  {hyp_name}: start=0x{start_code:04X}, saved {out}")

# ── Build the test: render middle of HJCHAR and compare ───────────────
# If HJCHAR starts at 0xBEAF:
# glyph[0] = 举 (0xBEAF? no, 0xBEAF is 挙 in some encodings)
# Actually 0xBEAF decodes to 举? Let me check.

print("\nGBK code table for 0xBEAF-0xBFC0:")
for code in range(0xBEAF, 0xBFC0):
    lead = (code >> 8) & 0xFF
    trail = code & 0xFF
    try:
        ch = bytes([lead, trail]).decode('gbk')
        print(f"  0x{lead:02X}{trail:02X} = {ch}", end="")
        if (code - 0xBEAF) % 10 == 9:
            print()
    except:
        print(f"  0x{lead:02X}{trail:02X} = ?", end="")
        if (code - 0xBEAF) % 10 == 9:
            print()
print()

# Render the first 20 chars of HJCHAR with hypothesis B
img = Image.new("RGB", (20 * 20, 2 * 20), (64, 64, 64))
draw = ImageDraw.Draw(img)

for i in range(min(20, n_glyphs)):
    bm = render_glyph_32(dec, i)
    cx = i * 20
    for y in range(16):
        for x in range(16):
            if bm[y * 16 + x]:
                draw.point((cx + x, y), fill=(255, 255, 255))
    
    ch = gbk_index_to_char(i, 0xBEAF)
    if ch and sys_font:
        draw.text((cx, 0), ch, fill=(255, 255, 0), font=sys_font)

img.save(_ROOT + '/scripts/_probe/font_atlas/HJCHAR_test_B_first20.png')
print("Saved: scripts/_probe/font_atlas/HJCHAR_test_B_first20.png")
print("  If yellow chars match the white glyphs, hypothesis B is correct")

# Also try hypothesis A for comparison
img2 = Image.new("RGB", (20 * 20, 2 * 20), (64, 64, 64))
draw2 = ImageDraw.Draw(img2)

for i in range(min(20, n_glyphs)):
    bm = render_glyph_32(dec, i)
    cx = i * 20
    for y in range(16):
        for x in range(16):
            if bm[y * 16 + x]:
                draw2.point((cx + x, y), fill=(255, 255, 255))
    
    ch = gbk_index_to_char(i, 0xB0A1)
    if ch and sys_font:
        draw2.text((cx, 0), ch, fill=(255, 255, 0), font=sys_font)

img2.save(_ROOT + '/scripts/_probe/font_atlas/HJCHAR_test_A_first20.png')
print("Saved: scripts/_probe/font_atlas/HJCHAR_test_A_first20.png")
print("  If yellow chars match the white glyphs, hypothesis A is correct")

# Also check if HJCHAR might be 64B/glyph (2-plane like HBCHAR2)
print("\nTrying HJCHAR as 64B/glyph (2-plane OR)...")
n_64 = len(dec) // 64
print(f"  {n_64} glyphs × 64B")

if sys_font:
    img3 = Image.new("RGB", (10 * 20, 2 * 20), (64, 64, 64))
    draw3 = ImageDraw.Draw(img3)
    
    for i in range(min(10, n_64)):
        base = i * 64
        bm = [0] * 256
        for y in range(16):
            r0 = (dec[base + y*2] << 8) | dec[base + y*2 + 1]
            r1 = (dec[base + 32 + y*2] << 8) | dec[base + 32 + y*2 + 1]
            combined = r0 | r1
            cx = i * 20
            for x in range(16):
                if (combined >> (15 - x)) & 1:
                    draw3.point((cx + x, y), fill=(255, 255, 255))
        
        ch = gbk_index_to_char(i, 0xB0A1)
        if ch:
            draw3.text((cx, 0), ch, fill=(255, 255, 0), font=sys_font)
    
    img3.save(_ROOT + '/scripts/_probe/font_atlas/HJCHAR_test_64B.png')
    print("Saved: scripts/_probe/font_atlas/HJCHAR_test_64B.png")
