#!/usr/bin/env python3
"""Replicate WorldMap._generate_procedural_map + _build_towns coordinate logic
to visually verify the fix for '画面是乱的' (garbled WorldMap)."""
import json
from PIL import Image

W, H = 256, 88
TOWN_GRID_W, TOWN_GRID_H = 48.0, 37.0
MAP_RENDER_W, MAP_RENDER_H = 896, 308

OCEAN = (155, 196, 212)
PARCH = (216, 192, 137)
PARCH_D = (168, 136, 74)
GOLD_D = (138, 106, 26)

img = Image.new("RGB", (W, H), OCEAN)
px = img.load()

islands = [
    [0,0, 20,0, 40,1, 60,3, 78,7, 92,12, 98,18, 94,24, 82,28, 68,28, 52,26, 36,24, 22,20, 10,16, 2,12, 0,6],
    [0,30, 8,26, 20,24, 40,22, 64,21, 90,21, 120,21, 150,21, 180,22, 210,24, 230,28, 240,34, 238,40, 228,46, 210,50, 180,52, 150,52, 120,52, 90,51, 60,50, 36,48, 20,44, 8,38, 0,34],
    [96,56, 110,54, 126,54, 140,58, 142,64, 130,68, 112,68, 94,64, 90,60],
    [0,60, 12,56, 28,54, 46,54, 64,56, 82,60, 98,64, 108,72, 102,80, 86,84, 64,86, 40,86, 20,82, 6,76, 0,70],
    [168,4, 184,4, 196,8, 198,14, 186,16, 172,12],
    [220,18, 232,20, 236,26, 226,30, 218,26],
    [132,52, 140,52, 142,56, 134,56],
    [146,58, 156,58, 156,62, 146,62],
    [60,82, 70,82, 72,86, 60,86],
]

def fill_poly(px, poly, color):
    if len(poly) < 6:
        return
    n = len(poly) // 2
    miny = min(poly[i*2+1] for i in range(n))
    maxy = max(poly[i*2+1] for i in range(n))
    miny = max(0, min(miny, H-1)); maxy = min(H-1, max(maxy, 0))
    for y in range(miny, maxy+1):
        xs = []
        for i in range(n):
            j = (i+1) % n
            y0, y1 = poly[i*2+1], poly[j*2+1]
            x0, x1 = poly[i*2], poly[j*2]
            if (y0 <= y and y1 > y) or (y1 <= y and y0 > y):
                xs.append(round(x0 + (y-y0)*(x1-x0)/(y1-y0)))
        xs.sort()
        k = 0
        while k+1 < len(xs):
            for x in range(max(0,xs[k]), min(W-1,xs[k+1])+1):
                px[x, y] = color
            k += 2

for poly in islands:
    fill_poly(px, poly, PARCH)

# darken land edges
def getp(x, y):
    if 0 <= x < W and 0 <= y < H:
        return px[x, y]
    return OCEAN
for y in range(H):
    for x in range(W):
        c = px[x, y]
        if c[0] < 0.6*255:
            continue
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nc = getp(x+dx, y+dy)
            if nc[0] < 0.6*255:
                px[x, y] = PARCH_D
                break

# town dots on base map
towns = json.load(open("scripts/towns.json", encoding="utf-8"))
if isinstance(towns, dict):
    towns = towns.get("towns", towns)
for t in towns:
    mx = int(t.get("map_x", 0)); my = int(t.get("map_y", 0))
    px2 = min(W-1, max(0, round(mx * W / TOWN_GRID_W)))
    py2 = min(H-1, max(0, round(my * H / TOWN_GRID_H)))
    for dy in (-1, 0):
        for dx in (-1, 0):
            nx, ny = px2+dx, py2+dy
            if 0 <= nx < W and 0 <= ny < H:
                c = px[nx, ny]
                if c[0] > 0.7*255 and c[1] > 0.6*255 and c[2] < 0.7*255:
                    px[nx, ny] = PARCH_D

# gold frame
for x in range(W):
    px[x, 0] = GOLD_D; px[x, H-1] = GOLD_D
for y in range(H):
    px[0, y] = GOLD_D; px[W-1, y] = GOLD_D

img.save("scripts/_verify_map_base.png")

# Stretched preview WITH town markers (what the game shows: bg texture stretched,
# town buttons placed at nx*MAP_RENDER_W). Draw to validate coordinate fix.
prev = img.resize((MAP_RENDER_W, MAP_RENDER_H), Image.NEAREST)
ppx = prev.load()
for t in towns:
    mx = int(t.get("map_x", 0)); my = int(t.get("map_y", 0))
    nx = mx / TOWN_GRID_W; ny = my / TOWN_GRID_H
    cx = int(nx * MAP_RENDER_W); cy = int(ny * MAP_RENDER_H)
    # gold dot 6x6
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            if dy*dy+dx*dx <= 9:
                if 0 <= cx+dx < MAP_RENDER_W and 0 <= cy+dy < MAP_RENDER_H:
                    ppx[cx+dx, cy+dy] = (212, 168, 55)

prev.save("scripts/_verify_map_preview.png")
print("towns:", len(towns))
print("base saved, preview saved")
# report coordinate spread for sanity
xs = [int(t.get("map_x",0)) for t in towns]
ys = [int(t.get("map_y",0)) for t in towns]
print("map_x range", min(xs), max(xs), "map_y range", min(ys), max(ys))
# normalized x positions in render space
nxs = [mx/TOWN_GRID_W*MAP_RENDER_W for mx in xs]
print("render-x range %.1f .. %.1f (want spread across 0..896)" % (min(nxs), max(nxs)))
