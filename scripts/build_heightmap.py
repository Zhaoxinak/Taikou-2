# build_heightmap.py — 生成日本列岛 3D 地形高度图
# 输入 data/world_map.json（陆地多边形/山系/山峰标高），输出 data/heightmap.json
# 高度合成：
#   海面 -10；海岸过渡带 0→base；平原 base+微噪声；
#   山系折线距离场隆起（宽 75px）；山峰高斯锥（σ 随真实标高，富士最高）
import json, math, random

SRC = "data/world_map.json"
DST = "data/heightmap.json"

# 覆盖范围（含海面外扩 300px）
PAD = 320
X0, Y0 = -PAD, -PAD
W, H = 4336 + PAD * 2, 4056 + PAD * 2   # 4976 x 4696
GW, GH = 384, 384                        # 网格分辨率（约 13px/格）
CELL = W / GW

RIDGE_W = 85.0    # 山系隆起宽度（px）
RIDGE_H = 32.0    # 山系隆起强度（高度单位）
PEAK_K = 150.0    # 山峰最大高度（富士，3D ÷4 后约 37 单位）
SNOW = 95.0       # 雪线高度（Godot 端着色用）
PLAIN_H = 10.0    # 平原基础高度（2D 单位 → 3D 约 2.5，落在低地绿）
COAST_W = 18.0    # 海岸过渡带宽度（px）


def point_seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    L2 = vx * vx + vy * vy
    if L2 < 1e-9:
        return math.hypot(px - ax, py - ay)
    t = (wx * vx + wy * vy) / L2
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + vx * t), py - (ay + vy * t))


def poly_dist(px, py, poly):
    # 点到多边形的最小距离（含内部=0）
    inside = False
    best = 1e18
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        d = point_seg_dist(px, py, ax, ay, bx, by)
        if d < best:
            best = d
        # 射线法判内
        if (ay > py) != (by > py):
            xint = ax + (py - ay) * (bx - ax) / (by - ay)
            if px < xint:
                inside = not inside
    return 0.0 if inside else best


def main():
    d = json.load(open(SRC, encoding="utf-8"))
    lands = []
    for key in ("honshu", "shikoku", "kyushu"):
        poly = d["land"].get(key, [])
        if len(poly) >= 3:
            lands.append(poly)
    # 小岛（2 点示意线段 → 中点+半径椭圆陆地）
    isles = []
    for name, seg in d["land"].get("islands", {}).items():
        if len(seg) >= 2:
            mx = (seg[0][0] + seg[1][0]) * 0.5
            my = (seg[0][1] + seg[1][1]) * 0.5
            rr = math.hypot(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1]) * 0.5 + 30.0
            isles.append((mx, my, rr))

    # 预计算山系/山峰
    ridges = []
    for m in d["mountains"]:
        pts = m["points"]
        # 强度按折线长度分级（主山脉更长更宽）
        ln = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                 for i in range(len(pts) - 1))
        ridges.append((pts, min(1.35, 0.55 + ln / 2600.0)))
    peaks = [(p["x"], p["y"], p["h"]) for p in d["peaks"]]
    maxh = max(p[2] for p in peaks)

    # 微噪声（确定性）
    def noise(ix, iy):
        v = math.sin(ix * 127.1 + iy * 311.7) * 43758.5453
        return (v - math.floor(v)) * 2.0 - 1.0

    print("grid %dx%d cell=%.1f | lands=%d ridges=%d peaks=%d" % (GW, GH, CELL, len(lands), len(ridges), len(peaks)))

    data = []
    stats = {"min": 1e9, "max": -1e9}
    for j in range(GH):
        y = Y0 + (j + 0.5) * CELL
        row = []
        for i in range(GW):
            x = X0 + (i + 0.5) * CELL
            # 陆地判定 + 海岸距离
            best_d = 1e18
            on_land = False
            for poly in lands:
                dd = poly_dist(x, y, poly)
                if dd < best_d:
                    best_d = dd
                if dd == 0.0:
                    on_land = True
            if not on_land:
                for mx, my, rr in isles:
                    dd = math.hypot(x - mx, y - my)
                    if dd < rr:
                        on_land = True
                        if dd < best_d:
                            best_d = dd
            h = -10.0
            if on_land:
                h = PLAIN_H + noise(i, j) * 2.5    # 平原基础高度（绿）
                if best_d < COAST_W:               # 海岸过渡
                    h *= best_d / COAST_W
                # 山系隆起
                for pts, k in ridges:
                    md = 1e18
                    for s in range(len(pts) - 1):
                        dd = point_seg_dist(x, y, pts[s][0], pts[s][1],
                                            pts[s + 1][0], pts[s + 1][1])
                        if dd < md:
                            md = dd
                    if md < RIDGE_W:
                        h += RIDGE_H * k * (1.0 - md / RIDGE_W)
                # 山峰高斯锥
                for px, py, ph in peaks:
                    dd = math.hypot(x - px, y - py)
                    sig = 26.0 + (ph / maxh) * 55.0
                    if dd < sig * 3.2:
                        g = math.exp(-(dd * dd) / (2.0 * sig * sig))
                        h += (ph / maxh) * PEAK_K * g
            if h < stats["min"]:
                stats["min"] = h
            if h > stats["max"]:
                stats["max"] = h
            row.append(round(h, 1))
        data.append(row)
    print("h range: %.1f .. %.1f" % (stats["min"], stats["max"]))

    out = {"origin": [X0, Y0], "cell": round(CELL, 3), "w": GW, "h": GH,
           "map_w": W, "map_h": H, "data": data}
    json.dump(out, open(DST, "w", encoding="utf-8"))
    print("written", DST)


if __name__ == "__main__":
    main()
