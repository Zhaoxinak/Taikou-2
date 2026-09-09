#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_test_world_mirror.py — world_map.gd 纯逻辑 + GameState 大地图方法的 Python 等价镜像。
与 GDScript 同一套断言，用于本机 --script 失效时的逻辑验证替代链路。
坐标用 (x, y) 元组模拟 Vector2。
"""
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MAP_W, MAP_H = 1820, 1120
STEP = 36.0
ENTER_DIST = 90.0


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
    # project 角点
    chk("project 原点", project((0, 0), MAP_W, MAP_H, view) == (180.0, 64.0))
    chk("project 右下角", project((MAP_W, MAP_H), MAP_W, MAP_H, view) == (1740.0, 1024.0))
    # unproject 往返
    p = project((500, 300), MAP_W, MAP_H, view)
    u = unproject(p, MAP_W, MAP_H, view)
    chk("unproject 往返", abs(u[0] - 500) < 1e-6 and abs(u[1] - 300) < 1e-6)
    # clamp 边界
    chk("clamp 上限", clamp_pos((99999, -50), MAP_W, MAP_H) == (MAP_W, 0))
    # step 步长 / clamp
    chk("step 自原点", step((0, 0), 1, 1, MAP_W, MAP_H) == (36.0, 36.0))
    chk("step 越界 clamp", step((1810, 1110), 1, 1, MAP_W, MAP_H) == (MAP_W, MAP_H))
    # nearest
    positions = {0: (0, 0), 1: (100, 100), 2: (1000, 1000)}
    chk("nearest 近 0", nearest((5, 5), positions) == 0)
    chk("nearest 近 2", nearest((990, 990), positions) == 2)
    chk("nearest 空", nearest((0, 0), {}) == -1)

    # —— GameState 大地图方法（用真实 castle_map 模拟）——
    with open(os.path.join(ROOT, "data", "castle_map.json"), encoding="utf-8") as f:
        cm = json.load(f)
    real_positions = {c["id"]: (c["x"], c["y"]) for c in cm["castles"]}
    # 模拟 player_map_pos 落在城 0 坐标上 → nearest 必为 0
    p0 = real_positions[0]
    chk("nearest_castle 真实 城0", nearest(p0, real_positions) == 0)
    # 移动到边界再 nearest（不应越界崩溃，返回有效 id）
    chk("nearest 边界有效", nearest((MAP_W, MAP_H), real_positions) >= 0)
    chk("城堡总数 200", len(real_positions) == 200)

    print("WORLD MIRROR: pass=%d fail=%d" % (_pass, _fail))
    if _fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
