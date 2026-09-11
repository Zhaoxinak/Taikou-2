#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_castle_map.py — 生成大地图城坐标 data/castle_map.json（史实经纬度投影版）

2026-09-11 v3：废弃旧版的「国中心+哈希抖动」摆法（那些坐标不代表真实地理）。
现在 200 城全部按**史实城址经纬度**（scripts/castle_geo.json）线性投影到
原版大地图 48×36 网格：

    x = (lon - LON0) / (LON1 - LON0) * (MAP_W-1)
    y = (LAT1 - lat) / (LAT1 - LAT0) * (MAP_H-1)

投影范围覆盖整个日本列岛（含北海道）：
    LON0=128.5  LON1=146.0（根室以东）
    LAT1=45.8（礼文/利尻）      LAT0=30.0（种子岛/屋久岛以南）

同格冲突 → 确定性亚格微偏移（同 id 每次重跑一致），偏移量 ≤0.45 cell，
不破坏城之间的相对位置感知。所有城保留浮点坐标（绘制时投影缩放）。

数据源：
  · data/castles.json         —— 200 城权威名单（id/name/province）
  · scripts/castle_geo.json   —— 200 城史实城址经纬度（主城跡位置）
  · scripts/towns.json        —— 92 町城（原版有町的城，标记 has_town=true；
       注意：TOWNPOS.DAT 坐标含大量哨兵值且与经纬度无线性关系，
       本版不再使用 TOWNPOS 坐标，仅用其「哪些城有町」的信息）

诚实标注：
  · 坐标为史实城址的等距投影近似（日本列岛 48×36 网格分辨率有限，
    近畿/濑户内等密集区存在重叠，已做确定性微偏移）
  · 非原版 TOWNPOS 坐标（原版坐标经核实不可靠：哨兵值混入 + 与地理无线性关系）
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_W = 48
MAP_H = 36
LON0, LON1 = 128.5, 146.0
LAT1, LAT0 = 45.8, 30.0


def project(lat: float, lon: float) -> tuple[float, float]:
    x = (lon - LON0) / (LON1 - LON0) * (MAP_W - 1)
    y = (LAT1 - lat) / (LAT1 - LAT0) * (MAP_H - 1)
    return x, y


def _nudge(seed: int) -> tuple[float, float]:
    """确定性亚格微偏移（±0.45 cell），用于同格冲突。"""
    a = (seed * 2654435761) & 0xFFFFFFFF
    b = (seed * 40503 + 17) & 0xFFFFFFFF
    return ((a % 91) / 100.0 - 0.45, (b % 91) / 100.0 - 0.45)


def _land_mask() -> list[list[bool]]:
    """按新投影在 4096×3072 精度栅格化海岸线 → 陆地布尔掩码（用于入海城吸附）。"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import japan_geo_data as G
    from PIL import Image, ImageDraw
    gw, gh = 4096, 3072
    img = Image.new('L', (gw, gh), 0)
    dr = ImageDraw.Draw(img)
    for _name, r in G.COASTLINES_LATLON:
        pts = [(G.proj(lat, lon)[0] / (MAP_W - 1) * (gw - 1),
                G.proj(lat, lon)[1] / (MAP_H - 1) * (gh - 1)) for lat, lon in r]
        dr.polygon(pts, fill=255)
    import numpy as np
    return np.asarray(img) > 127


def _snap_to_land(x: float, y: float, land) -> tuple[float, float]:
    """若城点落在海里（全精度掩码判定），沿环带向外找最近陆地像素吸附。"""
    gw, gh = land.shape[1], land.shape[0]
    px = int(round(x / (MAP_W - 1) * (gw - 1)))
    py = int(round(y / (MAP_H - 1) * (gh - 1)))
    if land[py, px]:
        return x, y
    for r in range(1, 48):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                ny, nx = py + dy, px + dx
                if 0 <= ny < gh and 0 <= nx < gw and land[ny, nx]:
                    return (nx / (gw - 1) * (MAP_W - 1),
                            ny / (gh - 1) * (MAP_H - 1))
    return x, y


def main() -> None:
    with open(os.path.join(ROOT, "data", "castles.json"), encoding="utf-8") as f:
        castles = json.load(f)["castles"]
    with open(os.path.join(ROOT, "scripts", "castle_geo.json"), encoding="utf-8") as f:
        geo = {int(k): v for k, v in json.load(f)["geo"].items()}
    towns = json.load(open(os.path.join(ROOT, "scripts", "towns.json"), encoding="utf-8"))["towns"]
    town_ids = {t["id"] for t in towns}

    land = _land_mask()

    missing = [c["id"] for c in castles if c["id"] not in geo]
    if missing:
        raise SystemExit(f"缺少经纬度: {missing}")

    out: list[dict] = []
    used: dict[tuple[int, int], int] = {}
    for c in castles:
        cid = int(c["id"])
        lat, lon = geo[cid]
        x, y = project(lat, lon)
        key = (round(x), round(y))
        if key in used:
            dx, dy = _nudge(cid + used[key])
            x, y = x + dx, y + dy
            used[key] += 1
        else:
            used[key] = 1
        x = max(0.0, min(MAP_W - 1.0, x))
        y = max(0.0, min(MAP_H - 1.0, y))
        # 入海城吸附到最近陆地（史实临海城址如八户/平户/鸟羽/浦户）
        x, y = _snap_to_land(x, y, land)
        out.append({
            "id": cid,
            "x": round(x, 2),
            "y": round(y, 2),
            "has_town": cid in town_ids,
        })

    payload = {
        "map_w": MAP_W,
        "map_h": MAP_H,
        "castles": out,
        "_meta": {
            "total": len(out),
            "mode": "史实经纬度投影（castle_geo.json → 48×36 等距近似）",
            "projection": {"lon": [LON0, LON1], "lat": [LAT0, LAT1]},
            "note": "200 城全部按史实城址经纬度投影；原版 TOWNPOS 坐标经核实含哨兵值且与地理无线性关系，不再使用；has_town 标记来自 towns.json（92 町城）",
        },
    }
    with open(os.path.join(ROOT, "data", "castle_map.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote data/castle_map.json: %d 城, map=%dx%d" % (len(out), MAP_W, MAP_H))
    for cid, nm in [(0, "三户"), (33, "江户"), (50, "春日山"), (66, "清洲"), (111, "二条"),
                    (136, "姬路"), (145, "冈山"), (157, "山口"), (171, "小仓"), (195, "鹿儿岛")]:
        lat, lon = geo[cid]
        x, y = project(lat, lon)
        print(f"  {nm}: ({x:.1f},{y:.1f})")


if __name__ == "__main__":
    main()
