#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
非图片方式验证 IDX 容器 (GRPDATA.LZW / HGRP.LZW) 解码正确性:
  1) 结构一致性: 每条目 avail字节 是否 >= 理论 3bpp 字节数 = ceil(w*h*3/8)
  2) 像素统计: 非零索引占比、调色板索引直方图 (真实图标应非均匀)
  3) 文本 ASCII 预览 (小条目) 供肉眼在无图环境下判断形状是否合理
"""
import sys, os, struct
sys.path.insert(0, "scripts")
from real_assets import ls11_decompress

GLYPH = " .:-=+*#%@"  # 索引 0..7 的 ASCII 近似 (0=透明/空)

def decode_entries(d):
    offs = []
    o = 4
    while o + 4 <= len(d):
        v = struct.unpack("<I", d[o:o+4])[0]
        if v == 0 or v >= len(d):
            break
        if offs and v <= offs[-1]:
            break
        offs.append(v); o += 4
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
        total = w * h
        need = (total * 3 + 7) // 8
        avail = len(px)
        # 3bpp MSB-first 解码
        idx = []
        bitpos = 0
        nbits = len(px) * 8
        while len(idx) < total and bitpos + 3 <= nbits:
            byte = px[bitpos >> 3]
            val = 0
            for _ in range(3):
                bit = (byte >> (7 - (bitpos & 7))) & 1
                val = (val << 1) | bit
                bitpos += 1
                if (bitpos & 7) == 0:
                    byte = px[bitpos >> 3] if (bitpos >> 3) < len(px) else 0
            idx.append(val)
        while len(idx) < total:
            idx.append(0)
        entries.append({"i": i, "off": a, "type": typ, "w": w, "h": h,
                        "size": b-a, "avail": avail, "need": need, "px": idx})
    return entries

def analyze(entries, name):
    print("="*70)
    print(f"# {name}  ({len(entries)} entries)")
    print("="*70)
    bad = [e for e in entries if e["avail"] < e["need"]]
    print(f"  字节充足: {len(entries)-len(bad)}/{len(entries)}  不足: {len(bad)}")
    for e in bad[:10]:
        print(f"    [!] entry {e['i']} @{e['off']:#x} {e['w']}x{e['h']} avail={e['avail']} need={e['need']}")
    # 非零占比 + 直方图
    ratios = []
    for e in entries:
        nz = sum(1 for v in e["px"] if v != 0)
        ratios.append(nz / max(1, len(e["px"])))
    import statistics
    print(f"  非零像素占比: min={min(ratios):.2f} med={statistics.median(ratios):.2f} max={max(ratios):.2f}")
    # 索引使用分布 (整个文件)
    from collections import Counter
    allc = Counter()
    for e in entries:
        allc.update(e["px"])
    dist = " ".join(f"{k}:{allc.get(k,0)}" for k in range(8))
    print(f"  调色板索引全局分布(0..7): {dist}")
    uniform = max(allc.values()) / max(1, len(allc))
    print(f"  最频索引占比={uniform:.3f} (接近1.0=噪声, 远小于1=有结构)")
    # 小条目 ASCII 预览
    small = [e for e in entries if e["w"] <= 32 and e["h"] <= 32][:6]
    for e in small:
        print(f"\n  -- entry {e['i']} @{e['off']:#x}  {e['w']}x{e['h']} type={e['type']}")
        for y in range(e["h"]):
            row = "".join(GLYPH[min(7, e["px"][y*e["w"]+x])] for x in range(e["w"]))
            print("     " + row)
    return bad

if __name__ == "__main__":
    for name in ["GRPDATA.LZW", "HGRP.LZW"]:
        d = ls11_decompress(open(f"F:/Games/Taikou2/{name}", "rb").read())
        print(f"\n[container] {name}: {len(d)} bytes, head={d[:8].hex()}")
        ents = decode_entries(d)
        analyze(ents, name)
    print("\nDONE")
