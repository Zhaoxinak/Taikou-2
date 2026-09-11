#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_map_bg.py — 预生成太阁5 手绘风大地图底图（4 季 1280×960 PNG）

与 src/core/world_terrain.gd 同算法（海岸线环射线法 + value-noise fbm），
在低分辨率 320×240 生成颜色图 → PIL 双线性放大 4 倍 → 平滑无格感；
海陆边界用 land mask 双线性 α 混合，海岸线柔和（手绘水彩感）。

用法: python3 scripts/gen_map_bg.py
输出: res://assets/map_bg_{winter,spring,summer,autumn}.png
"""
import math
import os
import random
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets")
os.makedirs(OUT_DIR, exist_ok=True)

# ---- 投影参数（与 japan_map.gd / gen_castle_map.py 一致） ----
LON0, LON1, LAT0, LAT1 = 128.6, 142.2, 30.8, 41.7
MAP_W, MAP_H = 48.0, 36.0
RES_W, RES_H = 320, 240
CELL = MAP_W / RES_W

def proj(lat, lon):
    return (lon - LON0) / (LON1 - LON0) * (MAP_W - 1), (LAT1 - lat) / (LAT1 - LAT0) * (MAP_H - 1)

# ---- 海岸线（经纬度，与 japan_map.gd 相同） ----
_HONSHU = [
    [41.05,140.90],[40.60,139.95],[40.00,139.80],[39.30,139.85],[38.90,139.95],
    [38.60,139.50],[38.20,139.20],[37.92,139.05],[37.60,138.90],[37.45,138.60],
    [37.35,138.00],[37.25,137.35],[36.85,136.90],[36.50,136.50],[36.30,136.20],
    [36.00,136.10],[35.90,135.80],[35.65,135.55],[35.72,135.25],[35.70,134.90],
    [35.80,134.35],[35.45,133.30],[35.00,132.60],[34.60,132.00],[34.45,131.50],
    [34.42,130.90],[34.02,130.82],
    [33.90,131.15],[33.78,131.65],[33.98,132.20],[34.20,132.55],[34.38,132.95],
    [34.28,133.40],[34.18,133.85],[34.05,134.25],[34.32,134.55],[34.60,135.02],
    [34.30,134.92],[33.92,135.00],[33.62,135.60],[33.50,135.95],[33.70,136.20],
    [34.00,136.30],[34.45,136.75],[34.72,136.95],[34.70,137.80],[34.80,138.50],
    [34.70,138.95],[35.12,139.72],[35.30,139.80],[35.60,140.05],[35.75,140.85],
    [36.30,140.75],[36.80,140.85],[37.20,141.05],[38.30,141.20],[38.60,141.55],
    [39.40,142.10],[40.40,141.85],[40.85,141.75],[41.30,141.50],[40.95,141.25],
    [41.05,140.90],
]
_KYUSHU = [
    [34.02,130.82],[33.92,130.60],[33.62,130.32],[33.45,130.00],[33.05,129.60],
    [32.62,129.68],[32.30,129.98],[31.62,130.30],[31.30,130.62],[31.18,130.98],
    [31.55,131.38],[32.05,131.65],[32.70,131.90],[33.30,132.00],[33.70,131.62],
    [34.00,131.10],[34.02,130.82],
]
_SHIKOKU = [
    [34.28,134.85],[34.18,134.60],[33.98,134.42],[33.90,134.50],[33.62,134.42],
    [33.32,134.22],[33.05,133.15],[32.92,132.90],[33.10,132.50],[33.42,132.40],
    [33.82,132.72],[34.10,132.85],[34.22,133.30],[34.32,133.80],[34.42,134.30],
    [34.28,134.85],
]
_SADO = [[38.32,138.42],[38.10,138.20],[37.82,138.28],[37.92,138.48],[38.20,138.52]]

POLYS = []
for ring in (_HONSHU, _KYUSHU, _SHIKOKU, _SADO):
    POLYS.append([proj(lat, lon) for lat, lon in ring])

MOUNTAINS = [
    (41.34,141.06),(39.09,140.05),(37.75,140.07),(36.62,137.60),
    (36.16,136.77),(35.36,138.73),(33.28,133.11),(32.88,131.08),
]
M_PTS = [proj(lat, lon) for lat, lon in MOUNTAINS]

# 港口 id（与 GameData.is_port_city 一致）
PORTS = {1,11,33,39,52,78,84,94,124,130,145,157,160,163,166,168,169,171,181,182,195}

# ---- value noise ----
def hash01(ix, iy, seedv):
    h = (ix * 374761393 + iy * 668265263 + seedv * 69069) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return (h & 0xFFFF) / 65535.0

def vnoise(x, y, seedv):
    ix = int(math.floor(x)); iy = int(math.floor(y))
    fx = x - math.floor(x); fy = y - math.floor(y)
    a = hash01(ix, iy, seedv); b = hash01(ix+1, iy, seedv)
    c = hash01(ix, iy+1, seedv); d = hash01(ix+1, iy+1, seedv)
    ux = fx*fx*(3-2*fx); uy = fy*fy*(3-2*fy)
    return a + (b-a)*ux + (c-a)*uy + (a-b-c+d)*ux*uy

def fbm(x, y, seedv, oct):
    v = 0.0; amp = 0.55; f = 1.0; tot = 0.0
    for i in range(oct):
        v += vnoise(x*f, y*f, seedv + i*101) * amp
        tot += amp; amp *= 0.5; f *= 2.0
    return v / tot

def in_poly(px, py, pts):
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if ((yi > py) != (yj > py)) and (px < (xj-xi)*(py-yi)/(yj-yi) + xi):
            inside = not inside
        j = i
    return inside

# ---- 读取城堡（城下町判定） ----
def load_castles():
    import json
    p = os.path.join(ROOT, "data", "castle_map.json")
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    towns = []
    for c in data["castles"]:
        if c["has_town"] or c["id"] in PORTS:
            towns.append((c["x"], c["y"]))
    return towns

def compute():
    print("computing terrain...")
    land = [False] * (RES_W * RES_H)
    hgt = [0.0] * (RES_W * RES_H)
    f2 = [0.0] * (RES_W * RES_H)
    towns = load_castles()
    for y in range(RES_H):
        for x in range(RES_W):
            lx = (x + 0.5) * CELL
            ly = (y + 0.5) * CELL
            on = False
            for pts in POLYS:
                if in_poly(lx, ly, pts):
                    on = True; break
            idx = y * RES_W + x
            land[idx] = on
            if on:
                h = fbm(lx*0.35, ly*0.35, 31, 3)
                for mx, my in M_PTS:
                    d = math.hypot(lx-mx, ly-my)
                    if d < 1.8:
                        h = max(h, 0.70 - d*0.16)
                hgt[idx] = h
                f2[idx] = fbm(lx*0.5+40.0, ly*0.5+17.0, 7, 2)
    # 类型
    typ = [0] * (RES_W * RES_H)  # 0 sea 1 beach 2 grass 3 forest 4 mount 5 town
    for y in range(RES_H):
        for x in range(RES_W):
            idx = y * RES_W + x
            if not land[idx]:
                continue
            lx = (x + 0.5) * CELL
            ly = (y + 0.5) * CELL
            # 城下町
            ist = False
            for tx, ty in towns:
                if math.hypot(lx-tx, ly-ty) < 0.55:
                    ist = True; break
            if ist:
                typ[idx] = 5; continue
            # 沙滩
            ns = False
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0: continue
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < RES_W and 0 <= ny < RES_H and not land[ny*RES_W+nx]:
                        ns = True; break
                if ns: break
            if ns:
                typ[idx] = 1; continue
            if hgt[idx] > 0.62:
                typ[idx] = 4; continue
            if f2[idx] > 0.53 and hgt[idx] < 0.50:
                typ[idx] = 3; continue
            typ[idx] = 2
    return land, hgt, f2, typ


# 季节陆地色（与 world_screen.gd LAND_GRASS/LAND_FOREST 同）
GRASS_COL = [(0.58,0.66,0.58),(0.66,0.74,0.46),(0.52,0.64,0.36),(0.66,0.56,0.34)]
FOREST_COL = [(0.40,0.48,0.42),(0.40,0.50,0.30),(0.32,0.42,0.24),(0.46,0.40,0.26)]
FOREST_TREE = [(0.30,0.38,0.32),(0.28,0.40,0.22),(0.22,0.32,0.16),(0.34,0.30,0.18)]

BIG_W, BIG_H = RES_W*2, RES_H*2  # 640x480 绘制分辨率

def up(img_like):
    return img_like.resize((BIG_W, BIG_H), Image.BILINEAR)

def mask_float(land, hgt, f2, typ, kind):
    """soft mask (0..1), bilinear upscaled"""
    m = Image.new("L", (RES_W, RES_H), 0)
    mpx = m.load()
    for y in range(RES_H):
        for x in range(RES_W):
            idx = y*RES_W+x
            mpx[x, y] = 255 if typ[idx] == kind else 0
    m = up(m)
    return Image.eval(m, lambda v: v/255.0)

def render(season, land, hgt, f2, typ):
    gcol = GRASS_COL[season]
    fcol = FOREST_COL[season]
    tcol = FOREST_TREE[season]
    # 草地基色（hgt 明暗渐变 → 连续地形起伏）
    base = Image.new("RGB", (BIG_W, BIG_H))
    px = base.load()
    for y in range(BIG_H):
        for x in range(BIG_W):
            sx = x // 2; sy = y // 2
            h = hgt[sy*RES_W+sx]
            shade = 0.78 + h*0.62
            px[x, y] = (int(255*min(1.0,gcol[0]*shade)),
                        int(255*min(1.0,gcol[1]*shade)),
                        int(255*min(1.0,gcol[2]*shade)))
    # 海（垂直渐变 + 噪声）
    sea = Image.new("RGB", (BIG_W, BIG_H))
    spx = sea.load()
    for y in range(BIG_H):
        deep = 0.72 + 0.34 * y / BIG_H
        for x in range(BIG_W):
            nn = (hash01(x*3, y*3, 91) - 0.5) * 0.10
            spx[x, y] = (int(255*max(0.0,min(1.0,0.22+nn))),
                         int(255*0.40*deep), int(255*0.56*deep))
    # 海陆 mask（双线性 + 高斯 1.4px → 海岸水彩柔边）
    m0 = Image.new("L", (RES_W, RES_H), 0)
    mpx = m0.load()
    for y in range(RES_H):
        for x in range(RES_W):
            mpx[x, y] = 255 if land[y*RES_W+x] else 0
    m0 = up(m0).filter(ImageFilter.GaussianBlur(1.4))
    img = Image.composite(base, sea, m0)
    # 沙滩带（mask 0.15..0.75 处沙色晕染）
    mband = Image.eval(m0, lambda v: 0 if v < 40 else (255 - int((v-40)/2.2)) if v < 190 else 0)
    sand = Image.new("RGB", img.size, (232, 218, 180))
    img = Image.composite(sand, img, mband)
    # 山丘（mount 软 mask + hgt 渐变，边缘羽化）
    mm = mask_float(land, hgt, f2, typ, 4)
    mimg = Image.new("RGB", img.size)
    mpx = mimg.load()
    for y in range(BIG_H):
        for x in range(BIG_W):
            sx = x//2; sy = y//2
            h = hgt[sy*RES_W+sx]
            t = (h-0.60)/0.40
            if t < 0: t = 0.0
            if t > 1: t = 1.0
            r = 0.52 + (0.80-0.52)*t
            g = 0.47 + (0.78-0.47)*t
            b = 0.40 + (0.74-0.40)*t
            if hash01(x, y, 41) > 0.62:
                r = min(1.0, r*1.15); g = min(1.0, g*1.15); b = min(1.0, b*1.15)
            mpx[x, y] = (int(255*r), int(255*g), int(255*b))
    img = Image.composite(mimg, img, Image.eval(mm, lambda v: int(v*255)))
    return img_like.resize((BIG_W, BIG_H), Image.BILINEAR)

def mask_float(land, hgt, f2, typ, kind):
    """soft mask (0..1), bilinear upscaled"""
    m = Image.new("L", (RES_W, RES_H), 0)
    mpx = m.load()
    for y in range(RES_H):
        for x in range(RES_W):
            idx = y*RES_W+x
            mpx[x, y] = 255 if typ[idx] == kind else 0
    m = up(m)
    return Image.eval(m, lambda v: v/255.0)

def render(season, land, hgt, f2, typ):
    gcol = GRASS_COL[season]
    fcol = FOREST_COL[season]
    tcol = FOREST_TREE[season]
    # 草地基色（hgt 明暗渐变 → 连续地形起伏）
    base = Image.new("RGB", (BIG_W, BIG_H))
    px = base.load()
    for y in range(BIG_H):
        for x in range(BIG_W):
            sx = x // 2; sy = y // 2
            h = hgt[sy*RES_W+sx]
            shade = 0.78 + h*0.62
            px[x, y] = (int(255*min(1.0,gcol[0]*shade)),
                        int(255*min(1.0,gcol[1]*shade)),
                        int(255*min(1.0,gcol[2]*shade)))
    # 海（垂直渐变 + 噪声）
    sea = Image.new("RGB", (BIG_W, BIG_H))
    spx = sea.load()
    for y in range(BIG_H):
        deep = 0.72 + 0.34 * y / BIG_H
        for x in range(BIG_W):
            nn = (hash01(x*3, y*3, 91) - 0.5) * 0.10
            spx[x, y] = (int(255*max(0.0,min(1.0,0.22+nn))),
                         int(255*0.40*deep), int(255*0.56*deep))
    # 海陆 mask（双线性 + 高斯 1.4px → 海岸水彩柔边）
    m0 = Image.new("L", (RES_W, RES_H), 0)
    mpx = m0.load()
    for y in range(RES_H):
        for x in range(RES_W):
            mpx[x, y] = 255 if land[y*RES_W+x] else 0
    m0 = up(m0).filter(ImageFilter.GaussianBlur(1.4))
    img = Image.composite(base, sea, m0)
    # 沙滩带（mask 0.15..0.75 处沙色晕染）
    mband = Image.eval(m0, lambda v: 0 if v < 40 else (255 - int((v-40)/2.2)) if v < 190 else 0)
    sand = Image.new("RGB", img.size, (232, 218, 180))
    img = Image.composite(sand, img, mband)
    # 山丘（mount 软 mask + hgt 渐变，边缘羽化）
    mm = mask_float(land, hgt, f2, typ, 4)
    mimg = Image.new("RGB", img.size)
    mpx = mimg.load()
    for y in range(BIG_H):
        for x in range(BIG_W):
            sx = x//2; sy = y//2
            h = hgt[sy*RES_W+sx]
            t = (h-0.60)/0.40
            if t < 0: t = 0.0
            if t > 1: t = 1.0
            r = 0.52 + (0.80-0.52)*t
            g = 0.47 + (0.78-0.47)*t
            b = 0.40 + (0.74-0.40)*t
            if hash01(x, y, 41) > 0.62:
                r = min(1.0, r*1.15); g = min(1.0, g*1.15); b = min(1.0, b*1.15)
            mpx[x, y] = (int(255*r), int(255*g), int(255*b))
    img = Image.composite(mimg, img, Image.eval(mm, lambda v: int(v*255)))
    # 城镇：淡灰底 + 建筑小点（屋顶色）
    tm = mask_float(land, hgt, f2, typ, 5)
    tpx = img.load()
    roof_cols = [(150,80,60),(110,120,150),(90,95,100),(140,120,80)]
    for y in range(BIG_H):
        for x in range(BIG_W):
            if tm.getpixel((x, y)) > 0.30:
                hsh = hash01(x, y, 53)
                if hsh > 0.70:
                    c = roof_cols[int(hash01(x, y, 61)*4) % 4]
                    tpx[x, y] = c
                elif hsh > 0.45:
                    tpx[x, y] = (min(255,int(255*0.62)), min(255,int(255*0.60)), min(255,int(255*0.55)))
    return img

FINAL_W, FINAL_H = 2048, 1536  # 每逻辑格 42.7px（2x 屏幕放大 ~3.7 倍，清晰）

def draw_peaks(img):
    """名山：锥形立体雪山（左上光照 + 雪顶 + 基座融入草地）"""
    px = img.load()
    W, H = img.size
    for mx, my in M_PTS:
        cx = mx / MAP_W * W; cy = my / MAP_H * H
        R = 96
        for dy in range(-R, R+1):
            for dx in range(-R, R+1):
                d2 = math.hypot(dx, dy)
                if d2 > R: continue
                xx = int(cx+dx); yy = int(cy+dy)
                if not (0 <= xx < W and 0 <= yy < H): continue
                # 锥形高度（顶点偏上）
                h = 1.0 - max(abs(dx)/(R*0.55), (dy + R*0.08)/(R*1.10))
                if h <= 0.02: continue
                li = max(0.35, min(1.0, 0.80 - dx/(R*0.85)))   # 左侧受光
                if h > 0.72:                                   # 雪顶
                    sn = (h-0.72)/0.28
                    r = int(255*(0.88+0.10*sn)*li); g = int(255*(0.90+0.08*sn)*li); b = int(255*(0.92+0.06*sn)*li)
                    newc = (min(255,r), min(255,g), min(255,b))
                elif h > 0.30:                                 # 岩坡（棕→灰）
                    a = (h-0.30)/0.42
                    r = int(255*(0.52+0.26*a)*li); g = int(255*(0.47+0.26*a)*li); b = int(255*(0.40+0.28*a)*li)
                    newc = (min(255,r), min(255,g), min(255,b))
                else:                                          # 山脚（融入草地棕）
                    a = h/0.30
                    old = px[xx, yy]
                    newc = (int(255*(0.52*a + 0.32*(1-a))*li),
                            int(255*(0.48*a + 0.52*(1-a))*li),
                            int(255*(0.40*a + 0.44*(1-a))*li))
                # 基座透明度混合
                aa = min(1.0, h*1.7)
                old = px[xx, yy]
                px[xx, yy] = (int(newc[0]*aa + old[0]*(1-aa)),
                              int(newc[1]*aa + old[1]*(1-aa)),
                              int(newc[2]*aa + old[2]*(1-aa)))
    return img

def main():
    land, hgt, f2, typ = compute()
    names = ["winter", "spring", "summer", "autumn"]
    for i, n in enumerate(names):
        out = os.path.join(OUT_DIR, f"map_bg_{n}.png")
        img = render(i, land, hgt, f2, typ)
        img = img.resize((FINAL_W, FINAL_H), Image.BILINEAR)
        img.save(out)
        print("saved", out, img.size)

if __name__ == "__main__":
    main()
