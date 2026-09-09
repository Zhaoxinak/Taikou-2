#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_castle_map.py — 生成大地图城坐标 data/castle_map.json

太阁立志传2 原版大地图每座城有固定屏幕坐标，但我们的 castles.json 导出
**不含 xy 坐标字段**（已核实）。本脚本按「国(province)聚类」生成一份
**近似坐标**，仅用于最小可玩空壳阶段把 200 座城摆上大地图、支持移动/进城。

⚠️ 诚实未接：这是聚类近似坐标，非原版固定坐标。待从原版 EXE 导出真实
   城坐标表后替换（届时只需更新 data/castle_map.json，逻辑层无需改动）。

输出形状：
  {"map_w": int, "map_h": int, "castles": [{"id": int, "x": float, "y": float}, ...]}
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    with open(os.path.join(ROOT, "data", "castles.json"), encoding="utf-8") as f:
        castles = json.load(f)["castles"]
    with open(os.path.join(ROOT, "data", "provinces.json"), encoding="utf-8") as f:
        provinces = json.load(f)["provinces"]

    n = len(provinces)
    GRID_COLS = 7
    GRID_ROWS = (n + GRID_COLS - 1) // GRID_COLS   # 49 → 7
    CELL_W, CELL_H = 260, 160
    PAD = 30
    map_w = GRID_COLS * CELL_W
    map_h = GRID_ROWS * CELL_H

    # 按国分组城
    by_prov: dict[int, list] = {}
    for c in castles:
        by_prov.setdefault(int(c["province"]), []).append(c)

    out: list[dict] = []
    for p in range(n):
        col = p % GRID_COLS
        row = p // GRID_COLS
        ox = col * CELL_W + PAD
        oy = row * CELL_H + PAD
        lst = by_prov.get(p, [])
        k = len(lst)
        cols = min(5, max(1, k))
        rows = (k + cols - 1) // cols
        cw = (CELL_W - 2 * PAD) / cols
        ch = (CELL_H - 2 * PAD) / rows
        for i, c in enumerate(lst):
            cc = i % cols
            rr = i // cols
            x = ox + cw * (cc + 0.5)
            y = oy + ch * (rr + 0.5)
            out.append({"id": int(c["id"]), "x": round(x, 1), "y": round(y, 1)})

    payload = {"map_w": map_w, "map_h": map_h, "castles": out}
    with open(os.path.join(ROOT, "data", "castle_map.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote data/castle_map.json: %d castles, map %dx%d" % (len(out), map_w, map_h))


if __name__ == "__main__":
    main()
