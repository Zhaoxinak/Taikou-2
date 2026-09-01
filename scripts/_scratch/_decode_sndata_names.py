#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_decode_sndata_names.py — Phase 5 前哨：用 0x506ca8 名称表直接解码 SNDATA 记录。
不依赖字体映射，直接尝试将 SNDATA 49B 记录中的字节值解释为 0x506ca8 名称表的索引。

也检查：
1. 0x503108 字符串（Post-Load Init A 加载的文件名）
2. 0x5110d8 数据（被复制的 10B 条目表）
3. HBCHAR.LZW 解压后前几个字形的 ASCII-art（看能否识别排列顺序）
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
import os
import sys

BASE_DIR = "F:/Games/Taikou2"
DUMP = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000

# Load unpacked EXE
mem = open(DUMP, "rb").read()

def mem_read(va, size):
    off = va - BASE
    if off < 0 or off + size > len(mem):
        return b'\x00' * size
    return mem[off:off + size]

# ============================================================
# 1. Check strings and data
# ============================================================
print("="*70)
print("  Static data inspection")
print("="*70)

# 0x503108 — filename string for Post-Load Init A
s = mem_read(0x503108, 32)
end = s.find(b'\x00')
if end >= 0: s = s[:end]
print(f"  0x503108: {s.decode('ascii', 'replace')!r}")

# 0x5110d8 — 10-byte entries copied in Post-Load Init A (16×4=64 entries)
data_5110d8 = mem_read(0x5110d8, 640)
nonzero = sum(1 for i in range(64) if data_5110d8[i*10:(i+1)*10] != b'\x00'*10)
print(f"  0x5110d8: {nonzero}/64 non-zero 10-byte entries")
if nonzero > 0:
    for i in range(min(8, 64)):
        entry = data_5110d8[i*10:(i+1)*10]
        if entry != b'\x00'*10:
            print(f"    [{i}] {entry.hex(' ')}")

# ============================================================
# 2. Load the 0x506ca8 name table (370 entries × 9 bytes)
# ============================================================
print("\n" + "="*70)
print("  Loading name table from 0x506ca8 (370 entries × 9 bytes)")
print("="*70)
name_tbl_raw = mem_read(0x506ca8, 370 * 9)
names = []
for i in range(370):
    entry = name_tbl_raw[i*9:(i+1)*9]
    try:
        txt = entry.decode('gbk').rstrip('\x00')
    except:
        txt = ""
    names.append(txt)

# ============================================================
# 3. Load SNDATA records
# ============================================================
sndata_path = os.path.join(BASE_DIR, "SNDATA1.TR2")
if not os.path.exists(sndata_path):
    sndata_path = os.path.join(BASE_DIR, "sndata1.tr2")
if not os.path.exists(sndata_path):
    # Try uppercase/lowercase variations
    for f in os.listdir(BASE_DIR):
        if f.lower() == "sndata1.tr2":
            sndata_path = os.path.join(BASE_DIR, f)
            break

print(f"\n  SNDATA file: {sndata_path}")
sndata_raw = open(sndata_path, "rb").read()
print(f"  Size: {len(sndata_raw)} bytes")
print(f"  Header: {sndata_raw[:16]}")

# Parse: 16B signature + 833×49B records + 23B tail
SIG_SIZE = 16
REC_SIZE = 49
NUM_RECS = 833
TAIL_SIZE = 23

assert len(sndata_raw) >= SIG_SIZE + NUM_RECS * REC_SIZE + TAIL_SIZE, "SNDATA size mismatch"

records = []
for i in range(NUM_RECS):
    off = SIG_SIZE + i * REC_SIZE
    records.append(sndata_raw[off:off + REC_SIZE])

# ============================================================
# 4. Analyze SNDATA records — try to find name indices
# ============================================================
print("\n" + "="*70)
print("  SNDATA Record Analysis")
print("="*70)

# For each byte position in the 49-byte record, check if values
# are in range [0, 369] (valid name table indices)
print("\n  Byte position analysis (which offsets could be name indices?):")
print("  Offset | UniqueVals | InRange[0,369] | Sample values")
for off in range(REC_SIZE):
    values = set()
    in_range = 0
    total = 0
    for rec in records:
        v = rec[off]
        values.add(v)
        if 0 <= v <= 369:
            in_range += 1
        total += 1
    pct = in_range / total * 100 if total > 0 else 0
    if pct > 50:  # Only show positions where >50% values are in range
        sample_vals = sorted(list(values))[:10]
        print(f"  {off:5d} | {len(values):10d} | {in_range:5d}/{total:5d} ({pct:.1f}%) | {sample_vals}")

# ============================================================
# 5. Try decoding specific records using name table
# ============================================================
print("\n" + "="*70)
print("  Decoding SNDATA records (first 30, non-zero)")
print("="*70)

# Skip records that are all-zero or all-0xFF
interesting_records = []
for i, rec in enumerate(records):
    if rec == b'\x00' * REC_SIZE or rec == b'\xff' * REC_SIZE:
        continue
    interesting_records.append((i, rec))

print(f"  Total non-trivial records: {len(interesting_records)}")

for idx, (rec_no, rec) in enumerate(interesting_records[:30]):
    print(f"\n  Record {rec_no}: {rec.hex(' ')}")
    # Try to interpret each byte as a name index
    name_hits = []
    for off in range(REC_SIZE):
        v = rec[off]
        if 0 < v < 370 and names[v]:
            name_hits.append(f"  byte[{off:2d}]={v:3d} → {names[v]!r}")
    if name_hits:
        print("  Name table matches:")
        for hit in name_hits[:8]:  # limit output
            print(hit)
    # Also try u16 LE pairs as GBK character codes
    gbk_hits = []
    for off in range(0, REC_SIZE - 1, 1):
        v = struct.unpack_from("<H", rec, off)[0]
        if 0x8140 <= v <= 0xFEFE:
            try:
                ch = struct.pack(">H", v).decode('gbk')  # big-endian GBK
                gbk_hits.append(f"  u16[{off:2d}]=0x{v:04x} → {ch!r}")
            except:
                pass
    if gbk_hits:
        print("  GBK character matches:")
        for hit in gbk_hits[:5]:
            print(hit)

# ============================================================
# 6. Also check BSDATA — we know names are plaintext GBK
# ============================================================
print("\n" + "="*70)
print("  BSDATA cross-reference (first 10 records)")
print("="*70)
bsdata_path = None
for f in os.listdir(BASE_DIR):
    if f.lower() == "bsdata1.tr2":
        bsdata_path = os.path.join(BASE_DIR, f)
        break
if bsdata_path:
    bsdata_raw = open(bsdata_path, "rb").read()
    print(f"  BSDATA file: {bsdata_path}, size: {len(bsdata_raw)}")
    for i in range(10):
        off = i * 59
        rec = bsdata_raw[off:off + 59]
        # Name is first 13 bytes: surname[0:4] + 00 00 00 + firstname[7:13]
        name_bytes = rec[:13]
        try:
            # Try GBK decode of the name
            surname = name_bytes[:4].split(b'\x00')[0].decode('gbk', 'replace')
            firstname = name_bytes[7:13].split(b'\x00')[0].decode('gbk', 'replace')
            print(f"  [{i:3d}] surname={surname!r} firstname={firstname!r} | rest={rec[13:30].hex(' ')}")
        except:
            print(f"  [{i:3d}] {name_bytes.hex(' ')} | {rec[13:30].hex(' ')}")

# ============================================================
# 7. Try rendering HBCHAR glyphs as ASCII art
# ============================================================
print("\n" + "="*70)
print("  HBCHAR glyph rendering (first 8 glyphs as ASCII art)")
print("="*70)

# Load LS11 decompressor
sys.path.insert(0, "scripts")
try:
    from real_assets import ls11_decompress
    hbchar_path = os.path.join(BASE_DIR, "HBCHAR.LZW")
    if os.path.exists(hbchar_path):
        raw = open(hbchar_path, "rb").read()
        decompressed = ls11_decompress(raw)
        print(f"  HBCHAR.LZW: {len(raw)}B → {len(decompressed)}B decompressed")
        # Try EGA 4-plane 16×16 = 128 bytes per glyph
        GLYPH_SIZE = 128
        NUM_GLYPHS = len(decompressed) // GLYPH_SIZE
        print(f"  Glyphs: {NUM_GLYPHS} (at {GLYPH_SIZE}B each)")
        # Render first 8 glyphs
        for gi in range(min(8, NUM_GLYPHS)):
            glyph_data = decompressed[gi * GLYPH_SIZE:(gi + 1) * GLYPH_SIZE]
            # EGA 4-plane: each plane is 16×16/8 = 32 bytes
            # Plane 0: bits 0, Plane 1: bits 1, etc.
            print(f"\n  Glyph {gi}:")
            for row in range(16):
                line = ""
                for col in range(16):
                    pixel = 0
                    for plane in range(4):
                        plane_data = glyph_data[plane * 32:(plane + 1) * 32]
                        byte_idx = row * 2 + col // 8
                        if byte_idx < len(plane_data):
                            bit = 7 - (col % 8)
                            if plane_data[byte_idx] & (1 << bit):
                                pixel |= (1 << plane)
                    line += " " if pixel == 0 else f"{pixel:x}"
                print(f"    {line}")
    else:
        print("  HBCHAR.LZW not found!")
except Exception as e:
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()
