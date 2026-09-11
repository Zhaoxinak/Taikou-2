#!/usr/bin/env python3
"""大地图底图后处理：Blender 渲染色块 → 太阁5 手绘风
- 海面由岸到外海浅→深渐变（原版海渐变）
- 细波纹横线（原版海波纹）
- 手绘纸纹噪点（去 3D 塑料感）
- 海岸 1px 柔化
用法: python3 scripts/post_process_map.py [season ...]  （默认 4 季）
"""
import sys, os
from PIL import Image, ImageFilter, ImageChops
import random

LON0, LON1, LAT0, LAT1 = 128.6, 142.2, 30.8, 41.7
MAP_W, MAP_H = 48.0, 36.0

def proj(lat, lon):
    return (lon - LON0) / (LON1 - LON0) * (MAP_W - 1), (LAT1 - lat) / (LAT1 - LAT0) * (MAP_H - 1)

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
_SADO = [[38.05,138.22],[38.15,138.30],[38.30,138.48],[38.40,138.35],[38.42,138.12],
         [38.30,137.98],[38.12,137.92],[38.00,138.05],[38.05,138.22]]
POLYS = [[proj(lat, lon) for lat, lon in r] for r in (_HONSHU, _KYUSHU, _SHIKOKU, _SADO)]

def in_poly(px, py, pts):
    inside = False
    n = len(pts); j = n - 1
    for i in range(n):
        xi, yi = pts[i]; xj, yj = pts[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / ((yj - yi) + 1e-12) + xi:
            inside = not inside
        j = i
    return inside

def land_mask_grid(w, h):
    """w×h 陆地掩码（0 海 / 255 陆），坐标北在上"""
    im = Image.new('L', (w, h), 0)
    p = im.load()
    for j in range(h):
        wy = j / (h - 1) * (MAP_H - 1)
        for i in range(w):
            wx = i / (w - 1) * (MAP_W - 1)
            if any(in_poly(wx, wy, poly) for poly in POLYS):
                p[i, j] = 255
    return im


def sea_distance(mask, maxd=220):
    """海岸距离场（MaxFilter 迭代膨胀）。返回 0..maxd，海内为到陆地距离，陆地为 0"""
    dist = mask.point(lambda v: 255 if v == 0 else 0)  # 海=255
    land = mask.point(lambda v: 255 if v > 0 else 0)
    out = dist.point(lambda v: 255)
    cur = dist
    steps = []
    for d in range(1, maxd + 1):
        cur = cur.filter(ImageFilter.MaxFilter(3))
        # 与陆地相减：膨胀圈内但不在原海 = 距离 d 的海环
        ring = ImageChops.subtract(cur, land)
        if ring.getextrema()[1] == 0:
            break
        steps.append((d, ring))
    # 组装距离图（每像素 = 最近陆地距离）
    import numpy as np
    try:
        arr = np.zeros((mask.height, mask.width), dtype=np.int16)
        for d, ring in steps:
            arr[np.asarray(ring, dtype=bool)] = d
        return arr
    except ImportError:
        arr = Image.new('I', (mask.width, mask.height), 0)
        for d, ring in steps:
            arr = ImageChops.lighter(arr, ring.point(lambda v: d if v else 0))
        return arr


def main():
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets')
    seasons = sys.argv[1:] if len(sys.argv) > 1 else ['spring', 'summer', 'autumn', 'winter']
    # 陆地掩码（2048×1536 计算距离场）
    W, H = 2048, 1536
    print('building land mask...')
    mask = land_mask_grid(W, H)
    dist = sea_distance(mask)
    land = mask.point(lambda v: 255 if v > 0 else 0)
    rng = random.Random(20260911)
    for seas in seasons:
        src = os.path.join(root, 'map_bg_%s_blender.png' % seas)
        if not os.path.exists(src):
            print('skip', src); continue
        im = Image.open(src).convert('RGB')
        # 深蓝海色（各季微调）
        deep = {'spring': (18, 58, 118), 'summer': (14, 72, 128),
                'autumn': (20, 60, 112), 'winter': (24, 62, 116)}[seas]
        # 用 2048 尺寸处理海渐变，再放大回 4096
        small = im.resize((W, H), Image.LANCZOS)
        sp = small.load()
        darr = dist
        for j in range(H):
            for i in range(W):
                d = darr[j, i]
                if d > 0:
                    t = min(1.0, d / 150.0)
                    r, g, b = sp[i, j]
                    dr, dg, db = deep
                    sp[i, j] = (int(r + (dr - r) * t * 0.55),
                                int(g + (dg - g) * t * 0.55),
                                int(b + (db - b) * t * 0.55))
        # 波纹横线（海面，d>6 区域）：细短横虚线
        for j in range(0, H, 7):
            base = (j * 37) % 90
            for i in range(base % 14, W, 14):
                d = darr[j, i]
                if d > 6:
                    for k in range(4):
                        x = i + k
                        if x < W:
                            r, g, b = sp[x, j]
                            sp[x, j] = (min(255, r + 9), min(255, g + 11), min(255, b + 13))
        # 手绘纸纹：低幅噪点
        for j in range(0, H, 2):
            for i in range(0, W, 2):
                nz = rng.randint(-5, 5)
                r, g, b = sp[i, j]
                sp[i, j] = (max(0, min(255, r + nz)), max(0, min(255, g + nz)), max(0, min(255, b + nz)))
        small = small.resize((4096, 3072), Image.LANCZOS)
        small.save(os.path.join(root, 'map_bg_%s.png' % seas))
        print('POST', seas)

if __name__ == '__main__':
    main()
