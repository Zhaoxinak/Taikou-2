#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 GAIJI（外字）渲染层所需的资产与数据：
  1. data/gaiji.json        —— 修正后的权威外字表（single / triple / glyphs / substitutes）
  2. assets/fonts/gaiji_atlas.png  —— 15 个 GAIJI.TR2 字形拼成的位图集（白墨透明底 RGBA）
  3. assets/fonts/gaiji_atlas.json —— slot -> {x,y,w,h} 矩形映射

源数据（已逆向，权威）：
  scripts/gaiji_spec.json      —— GAIJI.TR2 16×34B 布局 + 15 条字形 bitmap（32B 1bpp 行主序 MSB 先行）
  scripts/gaiji_identities.json—— 每槽字符身份 / 角色（compound_slice / standalone）/ 是否在用

关键修正：原 export_for_godot.py 的 GAIJI_SINGLE 把 0xA143 错映成「宗」，
实际 0xA143 是「宗我」双字切片（長宗我部 = 長|宗我|部）。本脚本以 identities 为准。

外字替换单元（渲染时交给位图绘制，其余交系统字体）：
  组合切片 宗我(0xA143) + 罕见独立字（垪/堯/籠/頸/惣/揆/梟/瓊/絆/渚/戌）。
  長/香/部 为标准汉字，系统字体即可，不入替换集。
"""
import json
import os
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = json.load(open(os.path.join(ROOT, "scripts/gaiji_spec.json"), encoding="utf-8"))
IDEN = json.load(open(os.path.join(ROOT, "scripts/gaiji_identities.json"), encoding="utf-8"))

# —— 1. 组装 single 映射（以 identities 字符为准，含全部 15 有效槽）——
single = {}
for slot, info in IDEN["slots"].items():
    ch = info.get("char")
    if ch is None:
        continue  # 终止记录（0xa14f）
    single[slot] = ch

# —— 2. triple（组合姓，来自 gaiji.json 旧 triple）——
triple = [
    {"codes": ["0xA141", "0xA143", "0xA144"], "text": "長宗我部"},
    {"codes": ["0xA142", "0xA143", "0xA144"], "text": "香宗我部"},
]

# —— 3. glyphs（bitmap 来自 spec）——
slot_to_bitmap = {g["slot"]: g["bitmap"] for g in SPEC["glyphs"]}
glyphs = []
for slot, info in sorted(IDEN["slots"].items(), key=lambda kv: int(kv[0], 16)):
    ch = info.get("char")
    if ch is None:
        continue
    glyphs.append({
        "slot": slot,
        "char": ch,
        "role": info.get("role", "standalone"),
        "status": info.get("status", "unused"),
        "bitmap": slot_to_bitmap.get(slot, ""),
    })

# —— 4. substitutes（渲染替换单元）——
EXCLUDE_STANDARD = {"0xa141", "0xa142", "0xa144"}  # 長/香/部 系统字体可渲染（键为小写，与 identities 对齐）
substitutes = []
for slot, info in IDEN["slots"].items():
    ch = info.get("char")
    if ch is None or slot in EXCLUDE_STANDARD:
        continue
    substitutes.append({"text": ch, "slot": slot})
# 组合切片（双字）置前，确保最长匹配优先
substitutes.sort(key=lambda d: -len(d["text"]))

gaiji = {
    "note": "GBK 0xA140..0xA14F 被劫持为外字区；single 以 gaiji_identities.json 为准（0xA143=宗我 双字切片）。",
    "single": single,
    "triple": triple,
    "glyphs": glyphs,
    "substitutes": substitutes,
    "affected_officers": [182, 557, 568, 581, 583],
}

os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
json.dump(gaiji, open(os.path.join(ROOT, "data/gaiji.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)
print("[OK] data/gaiji.json: %d single, %d triple, %d glyphs, %d substitutes"
      % (len(single), len(triple), len(glyphs), len(substitutes)))

# —— 5. 位图集 PNG（纯 python，无 PIL 依赖）——
def hex_to_rows(bm_hex):
    """32 字节 1bpp 行主序 MSB 先行 -> 16×16 ink 布尔矩阵"""
    raw = bytes.fromhex(bm_hex)
    rows = []
    for r in range(16):
        b0, b1 = raw[r * 2], raw[r * 2 + 1]
        bits = [(b0 >> (7 - k)) & 1 for k in range(8)] + [(b1 >> (7 - k)) & 1 for k in range(8)]
        rows.append(bits)
    return rows

GLYPHS = [g for g in glyphs if g["bitmap"]]  # 跳过位图为空的（terminator）
N = len(GLYPHS)
W, H = N * 16, 16
atlas_rect = {}

buf = bytearray()
for r in range(H):
    buf.append(0)  # filter type 0
    for gx in range(N):
        rows = hex_to_rows(GLYPHS[gx]["bitmap"])
        for cx in range(16):
            ink = rows[r][cx]
            if ink:
                buf += bytes((255, 255, 255, 255))
            else:
                buf += bytes((0, 0, 0, 0))

def chunk(tag, data):
    out = bytearray()
    out += len(data).to_bytes(4, "big") + tag + data
    out += zlib.crc32(tag + data).to_bytes(4, "big")
    return bytes(out)

png = b"\x89PNG\r\n\x1a\n"
png += chunk(b"IHDR", W.to_bytes(4, "big") + H.to_bytes(4, "big") + bytes((8, 6, 0, 0, 0)))
png += chunk(b"IDAT", zlib.compress(bytes(buf), 9))
png += chunk(b"IEND", b"")

out_dir = os.path.join(ROOT, "assets/fonts")
os.makedirs(out_dir, exist_ok=True)
open(os.path.join(out_dir, "gaiji_atlas.png"), "wb").write(png)

for i, g in enumerate(GLYPHS):
    atlas_rect[g["slot"]] = {"x": i * 16, "y": 0, "w": 16, "h": 16}
json.dump({"width": W, "height": H, "rects": atlas_rect},
          open(os.path.join(out_dir, "gaiji_atlas.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)
print("[OK] assets/fonts/gaiji_atlas.png: %dx%d, %d glyphs" % (W, H, N))
print("[OK] assets/fonts/gaiji_atlas.json written")
