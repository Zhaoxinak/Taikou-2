#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_test_world_mirror.py — world_map.gd 纯逻辑 + 大地图数据的 Python 等价镜像。
与 GDScript 同一套断言，用于本机 --script 失效时的逻辑验证替代链路。
坐标用 (x, y) 元组模拟 Vector2。
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MAP_W, MAP_H = 48.0, 36.0
STEP = 1.0
ENTER_DIST = 1.6


def project(pos, map_w, map_h, view):
    vx, vy, vw, vh = view
    s = min(vw / map_w, vh / map_h)
    dw = map_w * s
    dh = map_h * s
    ox = vx + (vw - dw) / 2.0
    oy = vy + (vh - dh) / 2.0
    return (ox + pos[0] * s, oy + pos[1] * s)


def unproject(screen, map_w, map_h, view):
    vx, vy, vw, vh = view
    s = min(vw / map_w, vh / map_h)
    dw = map_w * s
    dh = map_h * s
    ox = vx + (vw - dw) / 2.0
    oy = vy + (vh - dh) / 2.0
    return ((screen[0] - ox) / s, (screen[1] - oy) / s)


def clamp_pos(pos, map_w, map_h):
    return (max(0.0, min(map_w, pos[0])), max(0.0, min(map_h, pos[1])))


def nearest(pos, positions):
    best = -1
    best_d = float("inf")
    for k, v in positions.items():
        d = math.hypot(pos[0] - v[0], pos[1] - v[1])
        if d < best_d:
            best_d = d
            best = k
    return best


def step(pos, dx, dy, map_w, map_h):
    return clamp_pos((pos[0] + dx * STEP, pos[1] + dy * STEP), map_w, map_h)


def move_towards(pos, target, map_w, map_h):
    d = math.hypot(target[0] - pos[0], target[1] - pos[1])
    if d <= STEP * 0.5:
        return clamp_pos(target, map_w, map_h)
    return clamp_pos((pos[0] + (target[0] - pos[0]) / d * STEP,
                      pos[1] + (target[1] - pos[1]) / d * STEP), map_w, map_h)


def within_enter(pos, city_pos):
    return math.hypot(pos[0] - city_pos[0], pos[1] - city_pos[1]) <= ENTER_DIST


def travel_days(a, b):
    return max(1, int(math.ceil(math.hypot(a[0] - b[0], a[1] - b[1]) / STEP * 1.0)))


_pass = 0
_fail = 0


def chk(name, cond):
    global _pass, _fail
    if cond:
        _pass += 1
        print("  PASS  ", name)
    else:
        _fail += 1
        print("  FAIL  ", name)


def main():
    view = (0, 64, 1920, 960)
    s = min(view[2] / MAP_W, view[3] / MAP_H)
    ox = view[0] + (view[2] - MAP_W * s) / 2.0
    oy = view[1] + (view[3] - MAP_H * s) / 2.0
    # project 角点（48×36）
    chk("project 原点", project((0, 0), MAP_W, MAP_H, view) == (ox, oy))
    chk("project 右下角", project((MAP_W, MAP_H), MAP_W, MAP_H, view) == (ox + MAP_W * s, oy + MAP_H * s))
    # unproject 往返
    p = project((30, 20), MAP_W, MAP_H, view)
    u = unproject(p, MAP_W, MAP_H, view)
    chk("unproject 往返", abs(u[0] - 30) < 1e-6 and abs(u[1] - 20) < 1e-6)
    # clamp 边界
    chk("clamp 上限", clamp_pos((99999, -50), MAP_W, MAP_H) == (MAP_W, 0))
    # step：1 格 = 1 单位（复刻原版逐格移动）
    chk("step 自原点", step((0, 0), 1, 1, MAP_W, MAP_H) == (1.0, 1.0))
    chk("step 越界 clamp", step((47.5, 35.5), 1, 1, MAP_W, MAP_H) == (MAP_W, MAP_H))
    # move_towards
    mt = move_towards((0, 0), (10, 0), MAP_W, MAP_H)
    chk("move_towards 走 1 格", abs(mt[0] - 1.0) < 1e-9 and mt[1] == 0)
    chk("move_towards 到达钳制", move_towards((9.8, 0), (10, 0), MAP_W, MAP_H) == (10.0, 0.0))
    # within_enter（1.6 格阈值）
    chk("within_enter 近", within_enter((0, 0), (1.5, 0)))
    chk("within_enter 远", not within_enter((0, 0), (5, 0)))
    # travel_days
    chk("travel_days 5 格", travel_days((0, 0), (5, 0)) == 5)
    # nearest
    positions = {0: (0, 0), 1: (100, 100), 2: (1000, 1000)}
    chk("nearest 近 0", nearest((5, 5), positions) == 0)
    chk("nearest 近 2", nearest((990, 990), positions) == 2)
    chk("nearest 空", nearest((0, 0), {}) == -1)

    # —— 真实数据层：200 城史实投影 + 航线 ——
    with open(os.path.join(ROOT, "data", "castle_map.json"), encoding="utf-8") as f:
        cm = json.load(f)
    real_positions = {c["id"]: (c["x"], c["y"]) for c in cm["castles"]}
    chk("城堡总数 200", len(real_positions) == 200)
    chk("地图尺寸 48×36", cm["map_w"] == 48 and cm["map_h"] == 36)
    # 城坐标全部在网格内
    in_grid = all(0 <= x <= MAP_W and 0 <= y <= MAP_H for x, y in real_positions.values())
    chk("全部城在网格内", in_grid)
    # 史实关键城位（东北右上 / 九州左下 / 四国右下 / 京畿中央）
    with open(os.path.join(ROOT, "data", "castles.json"), encoding="utf-8") as f:
        cs = json.load(f)
    castle_list = cs["castles"] if isinstance(cs, dict) and "castles" in cs else cs
    name_map = {c["name"]: int(c["id"]) for c in castle_list}
    key = {
        "三户": (True, True), "春日山": (True, True), "江户": (True, False),
        "小仓": (False, False), "鹿儿岛": (False, False),
        "浦户": (False, False), "山口": (False, False),
    }
    for nm, (want_x_hi, want_y_lo) in key.items():
        if nm in name_map:
            cid = name_map[nm]
            x, y = real_positions[cid]
            ok = (x > MAP_W / 2) == want_x_hi and (y < MAP_H / 2) == want_y_lo
            chk("史实位置 %s" % nm, ok)
        else:
            chk("史实位置 %s" % nm, False)
    # 二条（京都）在南北中部（不贴边）
    if "二条" in name_map:
        _, y2 = real_positions[name_map["二条"]]
        chk("二条在南北中部", MAP_H * 0.4 < y2 < MAP_H * 0.65)
    # 三户在东北（右上），鹿儿岛在九州（左下）
    x3, y3 = real_positions[name_map["三户"]]
    xk, yk = real_positions[name_map["鹿儿岛"]]
    chk("三户在鹿儿岛东北", x3 > xk and y3 < yk)
    # 江户在二条东边（关东 vs 京畿）
    xj, yj = real_positions[name_map["江户"]]
    xe, ye = real_positions[name_map["二条"]]
    chk("江户在二条以东", xj > xe)

    # —— 航线 / 港町 ——
    with open(os.path.join(ROOT, "data", "sea_routes.json"), encoding="utf-8") as f:
        sr = json.load(f)
    routes = sr["routes"]
    chk("航线 26 条", len(routes) == 26)
    # loader 自动双向展开 → 展开图每条边反向可达
    adj = {}
    for r in routes:
        adj.setdefault(r["from"], set()).add(r["to"])
        adj.setdefault(r["to"], set()).add(r["from"])
    chk("航线双向对称", all(t in adj[f] for f, ts in adj.items() for t in ts))
    ports = set()
    for r in routes:
        ports.add(r["from"])
        ports.add(r["to"])
    chk("港町 21 座", len(ports) == 21)
    # 手册主线：大坂(堺) → 德岛(鸣门) → 伊予(今治) → 小仓
    chk("堺→鸣门", 160 in adj[124])
    chk("鸣门→今治", 168 in adj[160])
    chk("今治→小仓", 171 in adj[168])
    # 每段航路 ≤2 日（原版：≤2 日免费搭船）
    chk("航路 ≤2 日", all(r["days"] <= 2 for r in routes))
    # 所有港町在 200 城内
    chk("港町均属 200 城", ports <= set(real_positions.keys()))
    # 92 町城 has_town
    towns = [c for c in cm["castles"] if c.get("has_town", False)]
    chk("92 町城", len(towns) == 92)
    # 港町兼为町城（原版堺=大坂港町）；至少大坂/敦贺/鹿儿岛为町城港
    ht = {c["id"]: c.get("has_town", False) for c in cm["castles"]}
    chk("大坂为町城港", ht[124] and 124 in ports)

    print("WORLD MIRROR: pass=%d fail=%d" % (_pass, _fail))
    if _fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
