#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_world_scene.py — 生成 scenes/screens/world_screen.tscn
读 data/world_map.json，把所有大地图元素（陆地/山系/山峰/河流/道路/城市/景点/国名）
预置为独立 Node2D 节点（WorldItem 自绘，编辑器可见可归类）。
运行：python tools/gen_world_scene.py
"""

import json
import os
import math
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(ROOT, "data", "world_map.json"), encoding="utf-8"))

# ── 道路连通性检查：支线图 是否全连通 ──
adj = collections.defaultdict(list)
for r in d["roads"]:
    if r["kind"] == "branch":
        a, b = r["a"], r["b"]
        adj[a].append(b)
        adj[b].append(a)
reach = set()
stack = [0]
while stack:
    u = stack.pop()
    if u in reach:
        continue
    reach.add(u)
    stack.extend(adj[u])
n_city = len(d["cities"])
unreach = [c["name"] for c in d["cities"] if c["id"] not in reach]
print("道路连通: %d/%d 城可达" % (len(reach), n_city), "| 不可达:", unreach[:15], "..." if len(unreach) > 15 else "")

# ── 生成 .tscn ────────────────────────────────────────────
L = []
A = L.append
A('[gd_scene load_steps=6 format=3]')
A('')
A('[ext_resource type="Script" path="res://src/world/world_screen.gd" id="1_wscr"]')
A('[ext_resource type="Script" path="res://src/world/WorldItem.gd" id="2_item"]')
A('[ext_resource type="Script" path="res://src/ui/UiPanel.gd" id="3_panel"]')
A('[ext_resource type="Script" path="res://src/ui/UiLabel.gd" id="4_label"]')
A('[ext_resource type="Script" path="res://src/ui/UiButton.gd" id="5_btn"]')
A('')
A('[node name="WorldScreen" type="Node2D"]')
A('script = ExtResource("1_wscr")')
A('')
A('[node name="World" type="Node2D" parent="."]')
A('')
# 陆地
A('[node name="Land" type="Node2D" parent="World"]')
A('')
LAND_NAMES = {"honshu": "Honshu", "shikoku": "Shikoku", "kyushu": "Kyushu"}
for key, poly in d["land"].items():
    if isinstance(poly, dict):  # islands: {name: points}
        for iname, ipoly in poly.items():
            A('[node name="%s" type="Node2D" parent="World/Land"]' % iname)
            A('script = ExtResource("2_item")')
            A('kind = "land"')
            A('points = PackedVector2Array(%s)' % ", ".join("%.1f, %.1f" % (p[0], p[1]) for p in ipoly))
            A('')
        continue
    nm = LAND_NAMES.get(key, key)
    A('[node name="%s" type="Node2D" parent="World/Land"]' % nm)
    A('script = ExtResource("2_item")')
    A('kind = "land"')
    A('points = PackedVector2Array(%s)' % ", ".join("%.1f, %.1f" % (p[0], p[1]) for p in poly))
    A('')
# 山系
A('[node name="Mountains" type="Node2D" parent="World"]')
A('')
A('[node name="Ranges" type="Node2D" parent="World/Mountains"]')
A('')
for m in d["mountains"]:
    A('[node name="M_%s" type="Node2D" parent="World/Mountains/Ranges"]' % m["name"])
    A('script = ExtResource("2_item")')
    A('kind = "mountain"')
    A('points = PackedVector2Array(%s)' % ", ".join("%.1f, %.1f" % (p[0], p[1]) for p in m["points"]))
    A('')
A('[node name="Peaks" type="Node2D" parent="World/Mountains"]')
A('')
for p in d["peaks"]:
    A('[node name="P_%s" type="Node2D" parent="World/Mountains/Peaks"]' % p["name"])
    A('script = ExtResource("2_item")')
    A('kind = "peak"')
    A('label = "%s"' % p["name"])
    A('points = PackedVector2Array(%.1f, %.1f)' % (p["x"], p["y"]))
    A('')
# 河流
A('[node name="Rivers" type="Node2D" parent="World"]')
A('')
for r in d["rivers"]:
    A('[node name="V_%s" type="Node2D" parent="World/Rivers"]' % r["name"])
    A('script = ExtResource("2_item")')
    A('kind = "river"')
    A('label = "%s"' % r["name"])
    A('points = PackedVector2Array(%s)' % ", ".join("%.1f, %.1f" % (p[0], p[1]) for p in r["points"]))
    A('')
# 道路
A('[node name="Roads" type="Node2D" parent="World"]')
A('')
A('[node name="Trunk" type="Node2D" parent="World/Roads"]')
A('')
for r in d["roads"]:
    if r["kind"] != "trunk":
        continue
    A('[node name="T_%s" type="Node2D" parent="World/Roads/Trunk"]' % r["name"])
    A('script = ExtResource("2_item")')
    A('kind = "road_trunk"')
    A('label = "%s"' % r["name"])
    A('points = PackedVector2Array(%s)' % ", ".join("%.1f, %.1f" % (p[0], p[1]) for p in r["points"]))
    A('')
A('[node name="Branch" type="Node2D" parent="World/Roads"]')
A('')
for r in d["roads"]:
    if r["kind"] != "branch":
        continue
    A('[node name="B_%s" type="Node2D" parent="World/Roads/Branch"]' % r["name"])
    A('script = ExtResource("2_item")')
    A('kind = "road_branch"')
    A('points = PackedVector2Array(%s)' % ", ".join("%.1f, %.1f" % (p[0], p[1]) for p in r["points"]))
    A('extra = {"a": %d, "b": %d}' % (r["a"], r["b"]))
    A('')
# 城市
A('[node name="Cities" type="Node2D" parent="World"]')
A('')
for c in d["cities"]:
    A('[node name="C%d_%s" type="Node2D" parent="World/Cities"]' % (c["id"], c["name"]))
    A('script = ExtResource("2_item")')
    A('kind = "%s"' % c["type"])
    A('label = "%s"' % c["name"])
    A('points = PackedVector2Array(%.1f, %.1f)' % (c["x"], c["y"]))
    A('extra = {"id": %d, "province": %d}' % (c["id"], c["province"]))
    A('')
# 景点
A('[node name="Sights" type="Node2D" parent="World"]')
A('')
for s in d["sights"]:
    A('[node name="S_%s" type="Node2D" parent="World/Sights"]' % s["name"])
    A('script = ExtResource("2_item")')
    A('kind = "sight"')
    A('label = "%s"' % s["name"])
    A('points = PackedVector2Array(%.1f, %.1f)' % (s["x"], s["y"]))
    A('extra = {"kind": "%s"}' % s["kind"])
    A('')
# 国名
A('[node name="Provinces" type="Node2D" parent="World"]')
A('')
for p in d["provinces"]:
    A('[node name="Pr_%s" type="Node2D" parent="World/Provinces"]' % p["name"])
    A('script = ExtResource("2_item")')
    A('kind = "province"')
    A('label = "%s"' % p["name"])
    A('points = PackedVector2Array(%.1f, %.1f)' % (p["cx"], p["cy"]))
    A('')
# 选中与玩家
A('[node name="Selection" type="Node2D" parent="World"]')
A('script = ExtResource("2_item")')
A('kind = "selection"')
A('visible = false')
A('')
A('[node name="Player" type="Node2D" parent="World"]')
A('script = ExtResource("2_item")')
A('kind = "player"')
A('points = PackedVector2Array(0, 0)')
A('')
# Camera2D
A('[node name="Camera2D" type="Camera2D" parent="."]')
A('position = Vector2(%d, %d)' % (d["meta"]["map_w"] / 2, d["meta"]["map_h"] / 2))
A('zoom = Vector2(1.1, 1.1)')
A('')
# UI 层
A('[node name="UI" type="CanvasLayer" parent="."]')
A('')
A('[node name="InfoPanel" type="Control" parent="UI"]')
A('layout_mode = 3')
A('anchors_preset = 0')
A('offset_left = 12.0')
A('offset_top = 12.0')
A('offset_right = 462.0')
A('offset_bottom = 128.0')
A('script = ExtResource("3_panel")')
A('title = "日 本 大 地 图"')
A('title_height = 56')
A('')
A('[node name="InfoLabel" type="Control" parent="UI/InfoPanel"]')
A('layout_mode = 1')
A('offset_left = 18.0')
A('offset_top = 64.0')
A('offset_right = 438.0')
A('offset_bottom = 106.0')
A('script = ExtResource("4_label")')
A('font_size = 24')
A('')
A('[node name="BackBtn" type="Control" parent="UI"]')
A('layout_mode = 3')
A('anchors_preset = 1')
A('anchor_left = 1.0')
A('anchor_right = 1.0')
A('offset_left = -392.0')
A('offset_top = 12.0')
A('offset_right = -12.0')
A('offset_bottom = 84.0')
A('grow_horizontal = 0')
A('script = ExtResource("5_btn")')
A('text = "返回状态画面"')
A('font_size = 24')
A('')
A('[node name="HintLabel" type="Control" parent="UI"]')
A('layout_mode = 3')
A('anchors_preset = 12')
A('anchor_top = 1.0')
A('anchor_right = 1.0')
A('anchor_bottom = 1.0')
A('offset_left = 12.0')
A('offset_top = -64.0')
A('offset_right = -12.0')
A('offset_bottom = -12.0')
A('grow_horizontal = 2')
A('grow_vertical = 0')
A('script = ExtResource("4_label")')
A('text = "滚轮缩放 · 拖拽平移 · 点击城池移动 · 点击干道沿线城市可直达"')
A('font_size = 20')
A('h_align = 1')
A('')
A('[connection signal="pressed" from="UI/BackBtn" to="." method="_on_back"]')

dst = os.path.join(ROOT, "scenes", "screens", "world_screen.tscn")
open(dst, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("written", dst, len(L), "lines")
