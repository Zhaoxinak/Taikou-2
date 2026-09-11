#!/usr/bin/env python3
"""v2 底图后处理：海波纹 + 纸纹噪点 + 海岸柔化（太阁5 手绘感）。

用法: python3 scripts/post_process_v2.py [season ...]  （默认 4 季）
输入: assets/map_bg_<season>_v2.png（4096×3072）
输出: assets/map_bg_<season>.png（覆盖，Godot 使用）
"""
import sys, os
from PIL import Image, ImageFilter
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import japan_geo_data as G

W, H = 4096, 3072

def land_mask() -> np.ndarray:
    from PIL import ImageDraw
    img = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(img)
    for _name, r in G.COASTLINES_LATLON:
        pts = [(G.proj(lat, lon)[0] / 47 * (W - 1),
                G.proj(lat, lon)[1] / 35 * (H - 1)) for lat, lon in r]
        dr.polygon(pts, fill=255)
    return np.asarray(img) > 127

def process(season: str) -> None:
    src = os.path.join(ROOT, f'assets/map_bg_{season}_v2.png')
    dst = os.path.join(ROOT, f'assets/map_bg_{season}.png')
    im = Image.open(src).convert('RGB')
    arr = np.asarray(im).astype(np.int16)
    land = land_mask()
    sea = ~land

    rng = np.random.default_rng(20260911)

    # ---- 1. 海波纹：海上随机短横线（手绘小波浪）----
    wave = np.zeros((H, W), dtype=np.int16)
    n_wave = 9000
    ys = rng.integers(2, H - 2, n_wave)
    xs = rng.integers(4, W - 20, n_wave)
    ln = rng.integers(8, 26, n_wave)
    # 波纹色：深蓝压暗
    for i in range(n_wave):
        y, x, l = ys[i], xs[i], ln[i]
        if sea[y, x]:
            wave[y, x:x + l] = -14
    arr[..., 2] = np.clip(arr[..., 2] + wave, 0, 255)  # 只压蓝通道更自然

    # ---- 2. 纸纹噪点（±3 亮度，去 3D 塑料感）----
    noise = rng.integers(-3, 4, (H, W, 1))
    arr = np.clip(arr + noise, 0, 255)

    # ---- 3. 海岸 1px 柔化（陆地边缘向海过渡）----
    edge = np.zeros((H, W), dtype=bool)
    edge[:-1, :] |= land[1:, :] != land[:-1, :]
    edge[1:, :] |= land[:-1, :] != land[1:, :]
    edge[:, :-1] |= land[:, 1:] != land[:, :-1]
    edge[:, 1:] |= land[:, :-1] != land[:, 1:]
    edge = edge & sea
    arr[edge] = (arr[edge] * 0.55).astype(np.int16)  # 海侧半透明过渡

    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(dst)
    print(f'[{season}] post-processed -> {dst}')

if __name__ == '__main__':
    seasons = sys.argv[1:] or ['spring', 'summer', 'autumn', 'winter']
    for s in seasons:
        process(s)
