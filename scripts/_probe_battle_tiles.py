#!/usr/bin/env python3
# Structural probe + atlas generation for battle tile files (HKMAP/HJMAP/etc).
# We cannot visually inspect PNGs, so we use structure-revealing rendering:
#   8bpp index -> grayscale (val/255)
#   4bpp index -> 16-step ramp
# to expose tile boundaries / coherence. User judges the real palette later.
import os, math, struct
from collections import Counter
import sys
sys.path.insert(0, os.path.dirname(__file__))
from real_assets import ls11_decompress

ROOT = "F:/Games/Taikou2"
OUT = os.path.join(os.path.dirname(__file__), "_probe", "battle_tiles")
os.makedirs(OUT, exist_ok=True)

try:
    from PIL import Image
except ImportError:
    Image = None

def entropy(b):
    c = Counter(b)
    n = len(b)
    e = 0.0
    for v in c.values():
        p = v / n
        e -= p * math.log2(p)
    return e

def analyze(name):
    raw = open(os.path.join(ROOT, name), "rb").read()
    dec = ls11_decompress(raw)
    print(f"\n=== {name} ===")
    print(f"  LZW size   : {len(raw)}")
    print(f"  DEC size   : {len(dec)}")
    if not dec:
        print("  (decompress failed / not LS11)")
        return None
    c = Counter(dec)
    print(f"  distinct   : {len(c)}")
    print(f"  entropy    : {entropy(dec):.3f} bits/byte")
    top = c.most_common(8)
    print(f"  top values : {[(hex(v), n) for v, n in top]}")
    # factor pairs for 8bpp bitmap hypotheses
    N = len(dec)
    print("  8bpp WxH factorizations (W<=480):")
    pairs = []
    for w in range(1, 481):
        if N % w == 0:
            h = N // w
            if w >= h:  # landscape-ish
                pairs.append((w, h))
    print("    " + ", ".join(f"{w}x{h}" for w, h in pairs[:14]))
    return dec

def save_atlas(dec, name, bpp, tw, th, cols, kind):
    if Image is None:
        return None
    if bpp == 8:
        bpp_bytes = tw * th
    else:
        bpp_bytes = tw * th // 2
    if bpp_bytes <= 0 or len(dec) % bpp_bytes != 0:
        print(f"  [{kind}] {name}: size {len(dec)} not divisible by tile {bpp_bytes}B -> skip")
        return None
    tile_count = len(dec) // bpp_bytes
    img_w = cols * tw
    img_h = ((tile_count + cols - 1) // cols) * th
    img = Image.new("L", (img_w, img_h), 0)
    px = img.load()
    for ti in range(tile_count):
        chunk = dec[ti * bpp_bytes:(ti + 1) * bpp_bytes]
        tx = (ti % cols) * tw
        ty = (ti // cols) * th
        if bpp == 8:
            for i in range(tw * th):
                x = i % tw; y = i // tw
                px[tx + x, ty + y] = chunk[i]
        else:
            for i in range(tw * th):
                x = i % tw; y = i // tw
                nib = (chunk[i // 2] >> (4 if (i % 2 == 0) else 0)) & 0xF
                px[tx + x, ty + y] = nib * 17
    path = os.path.join(OUT, f"{name}_{kind}_{bpp}bpp_{tw}x{th}.png")
    img.save(path)
    print(f"  saved {path}  tiles={tile_count} grid={img_w}x{img_h}")
    return path

files = ["HKMAP.LZW", "HJMAP.LZW", "HKCHAR.LZW", "HJCHAR.LZW", "HGRP.LZW", "HBMAP.LZW"]
decs = {}
for f in files:
    d = analyze(f)
    if d:
        decs[f] = d

print("\n=== generating atlases (16x16, cols=20) ===")
for f, dec in decs.items():
    # 8bpp
    save_atlas(dec, f.replace(".LZW", ""), 8, 16, 16, 20, "tiles")
    # 4bpp
    save_atlas(dec, f.replace(".LZW", ""), 4, 16, 16, 20, "tiles")
print("\ndone.")
