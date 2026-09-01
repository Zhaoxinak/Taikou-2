#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate PNG atlases of all 38 HJMAPDAT.DAT battle maps at confirmed
40x19 layout (1 byte/cell). Terrain = low nibble, modifier = high nibble."""
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
from PIL import Image

DAT = r"F:/Games/Taikou2/HJMAPDAT.DAT"
OUT = _ROOT + '/scripts/_probe/battle_maps'
REC = 1700
W, H = 40, 19
SCALE = 6

with open(DAT, "rb") as f:
    buf = f.read()
nrec = len(buf) // REC

# terrain colormap (low nibble 0..15)
TERRAIN = [
    (26, 58, 107),   # 0 deep water
    (42, 93, 176),   # 1 water
    (74, 155, 208),  # 2 shallow
    (224, 216, 160), # 3 sand
    (126, 200, 80),  # 4 plain
    (90, 168, 48),   # 5 grass
    (46, 125, 50),   # 6 forest
    (160, 136, 88),  # 7 hill
    (138, 138, 138), # 8 mountain
    (208, 208, 208), # 9 peak
    (192, 57, 43),   # 10 castle
    (58, 160, 224),  # 11 river
    (139, 90, 43),   # 12 bridge
    (106, 106, 106), # 13 wall
    (212, 160, 23),  # 14 gate
    (224, 64, 251),  # 15 special
]

def hsv_color(h, s, v):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h/360.0, s, v)
    return (int(r*255), int(g*255), int(b*255))

def build_atlas(get_val, colormap, fname, title=""):
    cols = 10
    rows = (nrec + cols - 1) // cols
    mw, mh = W*SCALE, H*SCALE
    img = Image.new("RGB", (cols*mw, rows*mh), (0,0,0))
    px = img.load()
    for r in range(nrec):
        rec = buf[r*REC:(r+1)*REC]
        B = rec[180:940]   # terrain section (record-local)
        C = rec[940:1700]  # unit section
        cx = (r % cols) * mw
        cy = (r // cols) * mh
        for y in range(H):
            for x in range(W):
                v = get_val(rec, x, y)
                col = colormap(v)
                for sy in range(SCALE):
                    for sx in range(SCALE):
                        px[cx + x*SCALE + sx, cy + y*SCALE + sy] = col
    img.save(f"{OUT}/{fname}")
    print(f"  saved {fname} ({cols}x{rows} maps, {img.size})")

# terrain (low nibble of section B)
def terrain_val(rec, x, y):
    B = rec[180:940]
    return B[y*W + x] & 0x0F

# modifier (high nibble of section B)
def mod_val(rec, x, y):
    B = rec[180:940]
    return (B[y*W + x] >> 4) & 0x0F

# unit/feature (raw byte of section C) -> hue by value
def unit_val(rec, x, y):
    C = rec[940:1700]
    return C[y*W + x]

def unit_color(v):
    if v < 36:
        return (0,0,0)  # shouldn't happen (min 36)
    # map 36..255 across hue wheel
    h = ((v - 36) * 360.0) / (255 - 36)
    return hsv_color(h, 0.85, 1.0)

print("Building atlases...")
build_atlas(terrain_val, lambda v: TERRAIN[v], "hjmapdat_terrain_40x19.png")
build_atlas(mod_val, lambda v: TERRAIN[v], "hjmapdat_modifier_40x19.png")
build_atlas(unit_val, unit_color, "hjmapdat_unit_40x19.png")

# Also dump terrain value stats per record for the doc
import collections
print("\nPer-record terrain (low-nibble) distinct types:")
for r in range(min(nrec, 38)):
    rec = buf[r*REC:(r+1)*REC]
    B = rec[180:940]
    terr = [b & 0xF for b in B]
    c = collections.Counter(terr)
    print(f"  rec{r:2d}: terrainTypes={dict(sorted(c.items()))}")
