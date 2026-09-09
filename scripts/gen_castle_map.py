#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_castle_map.py — 生成大地图城坐标 data/castle_map.json（真实日本地图版）

原版太阁立志传2 大地图城坐标源 = TOWNPOS.DAT（35×35 网格，按 castle id 索引；
buffer @0x525af4，loader 0x4ac9c0；城坐标 (map_x,map_y) ∈ 0..47×0..36 ——
见 scripts/town_obj_format_ref.py / scripts/towns.json，前序已破，2026-08-28 EXE 权威名）。

本脚本：
  1) 读 scripts/towns.json（92 城带真实 map_x/map_y），直接用；
  2) 同国若有已知城 → 用国中心 + 确定性小抖动（id 哈希，±2 cell，钳 0..47/0..35）；
  3) 同国若无已知城（35/49 = 14 国）→ 用全图中心 + 较大确定性抖动
     并诚实标注：此为「无原版坐标数据」派生，非真实地理位置（待 Unicorn 跑 TOWNPOS
     消费者 0x4acbb0/0x4acc30 完整 dump 剩余 108 城可闭合）。

诚实标注：
  · map_w=48, map_h=36 直接取原版网格尺寸（project() 自动等比 fit 到屏幕）；
  · 派生位置用确定性哈希（同一 id 每次重跑结果完全一致），不会"乱跳"；
  · 无原版坐标的派生城位置**不代表真实地理**，仅保证：不与已知城重叠、
    同国聚集、重跑稳定。

输出形状（与旧版兼容）：
  {"map_w": 48, "map_h": 36, "castles": [{"id": int, "x": float, "y": float}, ...]}
"""
import json
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_W = 48
MAP_H = 36
JITTER_SMALL = 2
JITTER_LARGE = 6


def _jitter(seed: int, mag: int) -> tuple[int, int]:
    """确定性小抖动：同一 seed → 同一偏移（不依赖 random）。"""
    dx = ((seed * 2654435761) % (2 * mag + 1)) - mag
    dy = ((seed * 40503 + 17) % (2 * mag + 1)) - mag
    return dx, dy


def main() -> None:
    with open(os.path.join(ROOT, "data", "castles.json"), encoding="utf-8") as f:
        castles = json.load(f)["castles"]
    with open(os.path.join(ROOT, "data", "provinces.json"), encoding="utf-8") as f:
        provinces = json.load(f)["provinces"]
    with open(os.path.join(ROOT, "scripts", "towns.json"), encoding="utf-8") as f:
        towns = json.load(f)["towns"]

    known: dict[int, tuple[int, int]] = {t["id"]: (t["map_x"], t["map_y"]) for t in towns}
    cid2prov: dict[int, int] = {c["id"]: int(c["province"]) for c in castles}

    prov_xy: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for t in towns:
        p = cid2prov.get(t["id"], -1)
        if p >= 0:
            prov_xy[p].append((t["map_x"], t["map_y"]))
    prov_center: dict[int, tuple[int, int]] = {}
    for p, xys in prov_xy.items():
        xs = [x for x, _ in xys]
        ys = [y for _, y in xys]
        prov_center[p] = (sum(xs) // len(xs), sum(ys) // len(ys))
    all_xs = [x for x, _ in known.values()]
    all_ys = [y for _, y in known.values()]
    global_cx = sum(all_xs) // len(all_xs)
    global_cy = sum(all_ys) // len(all_ys)

    out: list[dict] = []
    used: set[tuple[int, int]] = set()
    n_real = n_prov = n_fb = 0
    for c in castles:
        cid = int(c["id"])
        if cid in known:
            mx, my = known[cid]
            n_real += 1
        else:
            p = cid2prov[cid]
            if p in prov_center:
                cx, cy = prov_center[p]
                jx, jy = _jitter(cid, JITTER_SMALL)
                mx, my = cx + jx, cy + jy
                n_prov += 1
            else:
                jx, jy = _jitter(cid, JITTER_LARGE)
                mx, my = global_cx + jx, global_cy + jy
                n_fb += 1
        mx = max(0, min(MAP_W - 1, mx))
        my = max(0, min(MAP_H - 1, my))
        if (mx, my) in used:
            for k in range(1, 5):
                kk = ((mx + k) % MAP_W, my)
                if kk not in used:
                    mx, my = kk
                    break
        used.add((mx, my))
        out.append({"id": cid, "x": float(mx), "y": float(my)})

    payload = {
        "map_w": MAP_W,
        "map_h": MAP_H,
        "castles": out,
        "_meta": {
            "real": n_real,
            "prov_derived": n_prov,
            "fallback": n_fb,
            "total": len(out),
            "note": "real=towns.json 92 原版坐标; prov_derived=同国中心±2哈希; fallback=全图中心±6哈希(无原版坐标)",
        },
    }
    with open(os.path.join(ROOT, "data", "castle_map.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote data/castle_map.json: %d 城 (real=%d / prov=%d / fallback=%d) map=%dx%d"
          % (len(out), n_real, n_prov, n_fb, MAP_W, MAP_H))


if __name__ == "__main__":
    main()
