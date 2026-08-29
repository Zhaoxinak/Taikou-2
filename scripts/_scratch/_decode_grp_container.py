#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解码 IDX 图形容器 GRPDATA.LZW / HGRP.LZW (KOEI 图标/精灵归档)。
格式 (每条目):
  [0:2] u16  type  (=3 -> 3bpp / 8 色)
  [2:4] u16  width
  [4:6] u16  height
  [6:]   3bpp 索引像素 (w*h*3/8 字节), MSB-first 每 3 bit = 调色板索引 0..7
容器:
  [0:4] "IDX" + 1 字节
  [4:]  u32LE 偏移表 (各条目起始 VA-相对偏移), 直到 0 或非递增
仅渲染形状: 用 8 级灰度盘 (索引0=透明/黑 -> 7=白) 生成 contact sheet。
真实调色板后续从 EXE/或对比定位。
"""
import sys, os, struct, json
sys.path.insert(0, "scripts")
from real_assets import ls11_decompress

try:
    from PIL import Image
except ImportError:
    Image = None

OUTDIR = "scripts/_decoded_grp"
os.makedirs(OUTDIR, exist_ok=True)

def decode_entries(d):
    # 偏移表从 byte 4
    offs = []
    o = 4
    while o + 4 <= len(d):
        v = struct.unpack("<I", d[o:o+4])[0]
        if v == 0 or v >= len(d):
            break
        if offs and v <= offs[-1]:
            break
        offs.append(v)
        o += 4
    entries = []
    for i, a in enumerate(offs):
        b = offs[i+1] if i+1 < len(offs) else len(d)
        chunk = d[a:b]
        if len(chunk) < 6:
            continue
        typ = struct.unpack("<H", chunk[0:2])[0]
        w = struct.unpack("<H", chunk[2:4])[0]
        h = struct.unpack("<H", chunk[4:6])[0]
        px = chunk[6:]
        # 3bpp MSB-first
        idx = []
        total = w * h
        bitpos = 0
        nbits = len(px) * 8
        while len(idx) < total and bitpos + 3 <= nbits:
            byte = px[bitpos >> 3]
            # 取 3 bit
            # 简化: 用位累加器逐位
            val = 0
            for _ in range(3):
                bit = (byte >> (7 - (bitpos & 7))) & 1
                val = (val << 1) | bit
                bitpos += 1
                if (bitpos & 7) == 0:
                    byte = px[bitpos >> 3] if (bitpos >> 3) < len(px) else 0
            idx.append(val)
        # 若不足, 补 0
        while len(idx) < total:
            idx.append(0)
        entries.append({"i": i, "off": a, "type": typ, "w": w, "h": h,
                        "size": b-a, "px": idx})
    return entries

# 8 级灰度盘 (索引0 视为透明/黑, 7 白)。用于看形状。
GRAY8 = [(i*255//7, i*255//7, i*255//7, 255) for i in range(8)]
# 透明色 = 索引0 设为透明, 其余灰度
GRAY8A = [(0,0,0,0)] + [(i*255//7, i*255//7, i*255//7, 255) for i in range(1,8)]

def render_sheet(entries, title, path):
    cols = 20
    maxw = max((e["w"] for e in entries), default=8)
    maxh = max((e["h"] for e in entries), default=8)
    cell = max(48, maxw + 16, maxh + 16)
    rows = (len(entries) + cols - 1) // cols
    img = Image.new("RGBA", (cols*cell, rows*cell), (20,20,30,255))
    px = img.load()
    bad = 0
    for n, e in enumerate(entries):
        cx = (n % cols) * cell
        cy = (n // cols) * cell
        ox = cx + (cell - e["w"])//2
        oy = cy + (cell - e["h"])//2
        for y in range(e["h"]):
            for x in range(e["w"]):
                if ox+x >= img.width or oy+y >= img.height:
                    bad += 1
                    continue
                ci = e["px"][y*e["w"]+x]
                if ci < len(GRAY8A):
                    c = GRAY8A[ci]
                    if c[3] > 0:
                        px[ox+x, oy+y] = c[:3] + (255,)
    img.save(path)
    if bad:
        print(f"  [warn] {bad} px skipped (oversized cell)")
    return img.size, (maxw, maxh)

if __name__ == "__main__":
    result = {}
    for name in ["GRPDATA.LZW", "HGRP.LZW"]:
        d = ls11_decompress(open(f"F:/Games/Taikou2/{name}", "rb").read())
        ents = decode_entries(d)
        result[name] = {
            "bytes": len(d),
            "entries": len(ents),
            "sizes": sorted(set((e["w"], e["h"]) for e in ents)),
            "types": sorted(set(e["type"] for e in ents)),
        }
        path = os.path.join(OUTDIR, name.split(".")[0].lower() + "_contact.png")
        sz, dims = render_sheet(ents, name, path)
        result[name]["sheet"] = path
        result[name]["sheet_size"] = list(sz)
        result[name]["max_dims"] = list(dims)
        print(f"{name}: {len(ents)} entries, sizes={result[name]['sizes']}, types={result[name]['types']}, sheet={path}")
    with open(os.path.join(OUTDIR, "grp_meta.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("OK")
