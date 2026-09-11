#!/usr/bin/env python3
"""生成日本史实大地图的地形贴图（高度图 + 颜色图）。

数据源：scripts/japan_geo_data.py
- 海岸线：Natural Earth 50m 真实轮廓（25 环）
- 山脉：60 座史实名山（经纬度+权重）
- 河流：28 条主要河流（源→出海口）
- 湖泊：13 个真实湖泊
- 港口：20 个史实港口

输出（每格 30px，1440×1080）：
- /tmp/japan_terrain/height_<season>.png（灰度高度图，供 Blender Displace）
- /tmp/japan_terrain/color_<season>.png（颜色图，供 Blender 材质）

用法：python3 scripts/gen_japan_terrain.py [spring|summer|autumn|winter]
"""
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import japan_geo_data as G

# ------------------------------------------------------------
# 分辨率：每地图格 30px
PPG = 30
GX, GY = 48 * PPG, 36 * PPG  # 1440 x 1080

def ll_to_px(lat, lon):
    x, y = G.proj(lat, lon)
    return x / 47.0 * (GX - 1), y / 35.0 * (GY - 1)

def px_to_grid(px, py):
    return px / (GX - 1) * 47.0, py / (GY - 1) * 35.0

# ------------------------------------------------------------
# 季节调色板（HSV 调整 + 雪线 + 河色）
SEASONS = {
    'spring': dict(
        sea_top=(34, 96, 168), sea_bottom=(86, 156, 208),
        shallow=(118, 196, 214), beach=(240, 224, 172),
        grass=(188, 210, 96), grass2=(150, 188, 80), hill=(120, 160, 72),
        mountain=(104, 132, 84), rock=(128, 124, 108), snow=(244, 246, 244),
        river=(86, 158, 212), lake=(92, 164, 208), snowline=3.5,
        snow_boost=0.0, river_ice=False,
    ),
    'summer': dict(
        sea_top=(24, 88, 164), sea_bottom=(72, 148, 206),
        shallow=(104, 190, 210), beach=(238, 222, 166),
        grass=(142, 188, 74), grass2=(108, 156, 60), hill=(88, 128, 58),
        mountain=(80, 108, 68), rock=(116, 112, 96), snow=(248, 250, 248),
        river=(70, 150, 206), lake=(76, 158, 204), snowline=3.2,
        snow_boost=-0.3, river_ice=False,
    ),
    'autumn': dict(
        sea_top=(30, 84, 152), sea_bottom=(70, 136, 190),
        shallow=(100, 176, 196), beach=(232, 214, 158),
        grass=(196, 168, 84), grass2=(168, 138, 66), hill=(140, 110, 58),
        mountain=(116, 100, 70), rock=(122, 112, 96), snow=(246, 244, 240),
        river=(74, 136, 186), lake=(80, 142, 184), snowline=2.8,
        snow_boost=0.2, river_ice=False,
    ),
    'winter': dict(
        sea_top=(28, 70, 128), sea_bottom=(58, 108, 156),
        shallow=(86, 140, 168), beach=(216, 208, 182),
        grass=(188, 194, 186), grass2=(158, 168, 158), hill=(132, 142, 132),
        mountain=(112, 122, 112), rock=(120, 124, 118), snow=(250, 252, 252),
        river=(120, 148, 172), lake=(116, 146, 170), snowline=2.4,
        snow_boost=0.45, river_ice=True,
    ),
}

def build(season):
    P = SEASONS[season]
    # --------------------------------------------------------
    # 1. 陆地掩码（PIL 多边形填充）
    # --------------------------------------------------------
    land = np.zeros((GY, GX), dtype=np.uint8)
    img = Image.new('L', (GX, GY), 0)
    d = ImageDraw.Draw(img)
    for name, r in G.COASTLINES_LATLON:
        pts = [ll_to_px(lat, lon) for lat, lon in r]
        d.polygon(pts, fill=255)
    land = np.asarray(img, dtype=np.uint8) > 127

    # --------------------------------------------------------
    # 2. 距离带（浅海 / 海滩）：膨胀实现
    # --------------------------------------------------------
    def dilate(mask, n):
        m = mask.copy()
        for _ in range(n):
            m = (m |
                 np.roll(m, 1, 0) | np.roll(m, -1, 0) |
                 np.roll(m, 1, 1) | np.roll(m, -1, 1) |
                 np.roll(m, (1, 1)) | np.roll(m, (1, -1)) |
                 np.roll(m, (-1, 1)) | np.roll(m, (-1, -1)))
        return m

    beach_band = dilate(land, 2) & ~land          # 离岸 2px 内（海侧）
    shallow_band = dilate(land, 7) & ~dilate(land, 2)  # 离岸 7px 内（海侧）
    # 陆侧 1px 沙滩带 = 陆地 ∩ 海的膨胀
    beach_land = land & dilate(~land, 1)

    # --------------------------------------------------------
    # 3. 高度场
    # --------------------------------------------------------
    yy, xx = np.mgrid[0:GY, 0:GX].astype(np.float64)
    lat_arr = G.LAT1 - (yy / (GY - 1)) * (G.LAT1 - G.LAT0)
    lon_arr = G.LON0 + (xx / (GX - 1)) * (G.LON1 - G.LON0)

    height = np.zeros((GY, GX), dtype=np.float64)
    # 基础陆高
    height[land] = 0.55
    # 浅海/沙滩微高（视觉厚度）
    height[shallow_band] = -0.12
    height[beach_band] = -0.02

    # 山体：高斯叠加
    PX, PY = ll_to_px(0, 0)
    def gauss_px(lat, lon, sigma_px, amp):
        px, py = ll_to_px(lat, lon)
        return amp * np.exp(-(((xx - px) ** 2 + (yy - py) ** 2) / (2 * sigma_px ** 2)))

    for name, lat, lon, w in G.MOUNTAINS:
        sigma = (0.55 + 0.42 * w) * PPG * 0.62  # 山体半径（px）
        amp = 0.9 + 1.35 * w
        peak = gauss_px(lat, lon, sigma, amp)
        height += peak

    # 山脉连脊：相邻名山间抬升（简化：略过，高斯已够）

    # 河流：最速下降从源头流向海，挖河床
    def find_outlet(px, py):
        """沿最速下降走到海边；返回路径像素列表。"""
        path = []
        steps = 0
        while steps < 3000:
            gx, gy = int(round(px)), int(round(py))
            if gx < 1 or gy < 1 or gx >= GX - 1 or gy >= GY - 1:
                break
            path.append((gx, gy))
            if not land[gy, gx]:
                break  # 到海
            # 8 邻域最低
            nb = height[gy-1:gy+2, gx-1:gx+2]
            mi = np.unravel_index(np.argmin(nb), nb.shape)
            dy, dx = mi[0] - 1, mi[1] - 1
            if dx == 0 and dy == 0:
                # 局部平坦：向海方向试探（纬度递减=py 增大）
                dy = 1
            px, py = px + dx, py + dy
            steps += 1
        return path

    river_mask = np.zeros((GY, GX), dtype=np.uint8)
    for name, pts in G.RIVERS:
        start_lat, start_lon = pts[0]
        # 源头从山体高处开始，沿最速下降
        sx, sy = ll_to_px(start_lat, start_lon)
        path = find_outlet(sx, sy)
        if len(path) > 3:
            # 粗河道（2px 核心 + 下游 3px 宽）
            for (gx, gy) in path:
                river_mask[gy, gx] = 1
                if gx + 1 < GX:
                    river_mask[gy, gx + 1] = 1
            # 下游加宽
            n = len(path)
            for i, (gx, gy) in enumerate(path):
                if i > n * 0.7:
                    for dy in (-1, 1):
                        for dx in (-1, 1):
                            if 0 <= gy+dy < GY and 0 <= gx+dx < GX:
                                river_mask[gy+dy, gx+dx] = 1

    # 湖泊
    lake_mask = np.zeros((GY, GX), dtype=np.uint8)
    for name, lat, lon, rx, ry in G.LAKES:
        px, py = ll_to_px(lat, lon)
        rxp = rx / (G.LON1 - G.LON0) * (GX - 1)
        ryp = ry / (G.LAT1 - G.LAT0) * (GY - 1)
        yy_, xx_ = np.mgrid[0:GY, 0:GX]
        ell = (((xx_ - px) / rxp) ** 2 + ((yy_ - py) / ryp) ** 2) <= 1.0
        lake_mask[ell] = 1

    # 河/湖修正高度：挖低
    water_mask = (river_mask > 0) | (lake_mask > 0)
    height[water_mask] = np.minimum(height[water_mask], 0.35)
    # 河流源头在山上，要保证河道连到海：强制河道高度低
    height[river_mask > 0] = np.minimum(height[river_mask > 0], 0.30)
    # 湖在陆地上
    height[lake_mask > 0] = 0.33

    # 海平面下压缩
    hmin, hmax = -0.5, 6.0
    height = np.clip(height, hmin, hmax)

    # --------------------------------------------------------
    # 4. 颜色
    # --------------------------------------------------------
    col = np.zeros((GY, GX, 3), dtype=np.uint8)

    def setcolor(mask, rgb):
        col[mask] = rgb

    # 海：渐变（上深下浅）
    sea_grad = np.linspace(0, 1, GY)[:, None]  # 顶部 0 → 底部 1
    sea_rgb = np.broadcast_to(np.stack([
        P['sea_top'][0] + (P['sea_bottom'][0] - P['sea_top'][0]) * sea_grad,
        P['sea_top'][1] + (P['sea_bottom'][1] - P['sea_top'][1]) * sea_grad,
        P['sea_top'][2] + (P['sea_bottom'][2] - P['sea_top'][2]) * sea_grad,
    ], axis=2), (GY, GX, 3)).copy().astype(np.uint8)
    col[~land] = sea_rgb[~land]
    # 近岸海更亮（雾感）
    col[shallow_band] = P['shallow']
    col[beach_band] = (int(P['shallow'][0]*0.8), int(P['shallow'][1]*0.95), int(P['shallow'][2]))

    # 陆地基础色
    land_col = np.zeros((GY, GX, 3), dtype=np.uint8)
    land_col[:] = P['grass']
    # 纬度色差（北冷南暖）
    north_fac = np.clip((lat_arr - 33.0) / 8.0, 0, 1)[..., None]  # 越北越偏冷灰
    land_col = (land_col.astype(np.float64) * (1 - 0.28 * north_fac)).astype(np.uint8)

    # 高度着色（在山体上叠加深色/雪）
    h = height.copy()
    h[~land] = 0
    snow = (h > P['snowline'] + P['snow_boost']) & land
    rock = (h > 2.7) & land & ~snow
    hillm = (h > 1.15) & land & ~rock & ~snow

    land_col[hillm] = P['hill']
    land_col[rock] = P['rock']
    land_col[snow] = P['snow']
    # 雪线渐变（边缘柔化）
    snow_edge = (h > P['snowline'] - 0.5 + P['snow_boost']) & (h <= P['snowline'] + P['snow_boost']) & land
    land_col[snow_edge] = ((land_col[snow_edge].astype(np.float64) * 0.55) +
                           np.array(P['snow']).astype(np.float64) * 0.45).astype(np.uint8)

    # 沙滩
    land_col[beach_land] = P['beach']
    # 内陆淡色平原微噪（手绘感）
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 6, (GY, GX, 1))
    land_col = np.clip(land_col.astype(np.int16) + noise.astype(np.int16), 0, 255).astype(np.uint8)

    # 森林斑块（深绿散布，手绘感）
    forest = np.zeros((GY, GX), dtype=bool)
    n_seed = 0
    rng2 = np.random.default_rng(7)
    while n_seed < 2600:
        fx, fy = rng2.integers(0, GX), rng2.integers(0, GY)
        if not land[fy, fx]:
            continue
        r = rng2.integers(2, 6)
        yy_, xx_ = np.mgrid[0:GY, 0:GX]
        # 只处理局部区域避免全图开销
        y0, y1 = max(0, fy-r), min(GY, fy+r+1)
        x0, x1 = max(0, fx-r), min(GX, fx+r+1)
        sub_yy, sub_xx = np.mgrid[y0:y1, x0:x1]
        ell = ((sub_xx - fx) / r) ** 2 + ((sub_yy - fy) / r) ** 2 <= 1.0
        sub = land[y0:y1, x0:x1]
        forest[y0:y1, x0:x1] |= ell & sub
        n_seed += 1
    # 森林色：草绿加深偏蓝绿
    fc = (86, 132, 62)
    land_col[forest] = ((land_col[forest].astype(np.float64) * 0.35) + np.array(fc) * 0.65).astype(np.uint8)

    # 卡通山体：径向渐变圆叠加（亮部偏左上，太阁5 手绘感）
    def draw_cartoon_mountain(lat, lon, w):
        px, py = ll_to_px(lat, lon)
        sigma = (0.55 + 0.42 * w) * PPG * 0.62
        r = int(sigma * 1.25) + 2
        y0, y1 = max(0, int(py) - r), min(GY, int(py) + r + 1)
        x0, x1 = max(0, int(px) - r), min(GX, int(px) + r + 1)
        if y1 <= y0 or x1 <= x0:
            return
        sub_yy, sub_xx = np.mgrid[y0:y1, x0:x1]
        d = np.sqrt(((sub_xx - px) / (r * 0.92)) ** 2 + ((sub_yy - py) / (r * 0.92)) ** 2)
        m = (d <= 1.0) & land[y0:y1, x0:x1]
        if not m.any():
            return
        # 层次：核心雪/岩 → 中环棕 → 外环深绿
        core = d <= 0.30
        mid = (d > 0.30) & (d <= 0.62)
        outer = (d > 0.62) & (d <= 1.0)
        # 亮部：圆心偏左上
        d_light = np.sqrt(((sub_xx - (px - r * 0.22)) / (r * 0.92)) ** 2 +
                          ((sub_yy - (py - r * 0.22)) / (r * 0.92)) ** 2)
        light = d_light < d
        cm = land_col[y0:y1, x0:x1].astype(np.float64)
        # 雪顶（大权重山有雪）
        if w >= 2.0 and season != 'summer':
            cm[core & m] = (np.array(P['snow']) * 0.75 + cm[core & m] * 0.25)
        elif w >= 2.0:
            cm[core & m] = (np.array(P['rock']) * 0.7 + cm[core & m] * 0.3)
        else:
            cm[core & m] = (np.array(P['mountain']) * 0.55 + cm[core & m] * 0.45)
        cm[mid & m] = (np.array(P['mountain']) * 0.62 + cm[mid & m] * 0.38)
        cm[outer & m] = (np.array(P['hill']) * 0.55 + cm[outer & m] * 0.45)
        # 亮部提亮
        lit = m & light
        cm[lit] = np.minimum(cm[lit] * 1.14 + 10, 255)
        land_col[y0:y1, x0:x1] = np.clip(cm, 0, 255).astype(np.uint8)

    for name, lat, lon, w in G.MOUNTAINS:
        draw_cartoon_mountain(lat, lon, w)

    col[land] = land_col[land]

    # 河流与湖泊
    if P['river_ice']:
        col[river_mask > 0] = (150, 168, 182)
        col[lake_mask > 0] = (140, 160, 178)
    else:
        col[river_mask > 0] = P['river']
        col[lake_mask > 0] = P['lake']
    # 河岸 1px 浅色
    river_edge = dilate(river_mask > 0, 1) & land & ~(river_mask > 0)
    col[river_edge] = ((col[river_edge].astype(np.float64) * 0.7) + np.array(P['beach']) * 0.3).astype(np.uint8)

    # 港口：小码头符号（栈桥+小屋）
    port_col = (222, 214, 190)
    roof = (168, 92, 68)
    for name, lat, lon, typ in G.PORTS:
        px, py = ll_to_px(lat, lon)
        gx, gy = int(round(px)), int(round(py))
        # 栈桥伸向海
        best_dir = None
        # 找最近海方向（8 向）
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                if 0 <= gy+dy*3 < GY and 0 <= gx+dx*3 < GX and not land[gy+dy*3, gx+dx*3]:
                    best_dir = (dx, dy)
                    break
            if best_dir:
                break
        if best_dir:
            dx, dy = best_dir
            for k in range(1, 4):
                if 0 <= gy+dy*k < GY and 0 <= gx+dx*k < GX:
                    col[gy+dy*k, gx+dx*k] = port_col
        # 小屋（2×2）
        for dy in (0, 1):
            for dx in (0, 1):
                if 0 <= gy+dy < GY and 0 <= gx+dx < GX:
                    col[gy+dy, gx+dx] = port_col
        col[gy, gx] = roof

    # 装饰小帆船（近岸海中，静态装饰）
    ship_pts = [(34.2, 135.0), (34.4, 133.0), (35.2, 136.7), (33.9, 131.0),
                (34.6, 138.0), (36.2, 136.2), (33.5, 130.6), (42.8, 141.5),
                (38.3, 140.8), (35.7, 140.1), (33.0, 132.4), (31.0, 131.0)]
    for lat, lon in ship_pts:
        px, py = ll_to_px(lat, lon)
        gx, gy = int(round(px)), int(round(py))
        if not land[gy, gx]:
            hull = (120, 92, 74)
            sail = (238, 238, 232)
            col[gy, gx] = hull
            col[gy, gx+1] = hull
            if gx+2 < GX:
                col[gy-1, gx+1] = sail
                col[gy-1, gx+2] = sail
            col[gy, gx] = hull

    # --------------------------------------------------------
    # 5. 保存
    # --------------------------------------------------------
    os.makedirs('/tmp/japan_terrain', exist_ok=True)
    h8 = ((height - hmin) / (hmax - hmin) * 255).astype(np.uint8)
    Image.fromarray(h8).save(f'/tmp/japan_terrain/height_{season}.png')
    Image.fromarray(col).save(f'/tmp/japan_terrain/color_{season}.png')
    print(f'[{season}] saved height+color {GX}x{GY}')
    # 陆地占比统计
    print(f'[{season}] land {land.mean()*100:.1f}%  snow {snow.mean()*100:.2f}%  river {river_mask.mean()*100:.2f}%')

if __name__ == '__main__':
    seasons = sys.argv[1:] or ['spring']
    for s in seasons:
        build(s)
