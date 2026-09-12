# gen_world_scene_3d.py — 生成 3D 大地图场景 world_screen_3d.tscn
# 输入 data/world_map.json + data/heightmap.json
# 输出：3D 节点树（地形由 world_screen_3d.gd 运行时生成）：
#   Terrain / Sea / Sun / WorldEnvironment / Rivers / Roads(Trunk,Branch) /
#   Cities(城村3D造型预置,编辑器可见) / Peaks / Sights / Provinces(Label3D) /
#   Player / Camera3D / UI(CanvasLayer)
import json, math, re

SRC = "data/world_map.json"
HM = "data/heightmap.json"
DST = "scenes/screens/world_screen_3d.tscn"
S = 0.25

d = json.load(open(SRC, encoding="utf-8"))
hm = json.load(open(HM, encoding="utf-8"))
HM_ORIG = hm["origin"]; HM_CELL = hm["cell"]; HM_W = hm["w"]; HM_H = hm["h"]; HM_DATA = hm["data"]

def hmh(x2, y2):
    ix = int((x2 - HM_ORIG[0]) / HM_CELL)
    iy = int((y2 - HM_ORIG[1]) / HM_CELL)
    ix = max(0, min(HM_W - 1, ix)); iy = max(0, min(HM_H - 1, iy))
    return HM_DATA[iy][ix] * S

def p3(x2, y2):
    return (x2 * S, hmh(x2, y2), y2 * S)

## Godot 节点名不允许 `/` `:` `@` `"` `%` 等（会破坏父路径解析，导致子 mesh 丢失/错位）。
## 生成节点名时净化，显示文本仍用原名。
def safe(n):
    return str(n).replace("/", "・").replace(":", "：").replace("@", "＠").replace('"', "＂").replace("%", "％")

# ---------- 资源收集 ----------
subs = []          # [id, 定义行]
sub_ids = set()

def sub(res_id, txt):
    if res_id not in sub_ids:
        subs.append((res_id, txt))
        sub_ids.add(res_id)

def mat(id_, color, rough=0.85, meta=True):
    lines = ['[sub_resource type="StandardMaterial3D" id="%s"]' % id_,
             'albedo_color = Color(%s, 1)' % color,
             'roughness = %s' % rough,
             'shading_mode = 0']   # unshaded：图标恒色，不受光照影响
    if meta:
        lines += ['metallic = 0.05']
    sub(id_, "\n".join(lines))

def box(id_, sx, sy, sz, mat_id):
    sub(id_, '\n'.join([
        '[sub_resource type="BoxMesh" id="%s"]' % id_,
        'size = Vector3(%s, %s, %s)' % (sx, sy, sz),
        'material = SubResource("%s")' % mat_id]))

def cyl(id_, r1, r2, h, mat_id):
    sub(id_, '\n'.join([
        '[sub_resource type="CylinderMesh" id="%s"]' % id_,
        'top_radius = %s' % r1,
        'bottom_radius = %s' % r2,
        'height = %s' % h,
        'material = SubResource("%s")' % mat_id]))

# 材质
mat("mat_stone", "0.72, 0.68, 0.62")
mat("mat_wall", "0.96, 0.94, 0.90")
mat("mat_wall_d", "0.84, 0.82, 0.78")
mat("mat_roof", "0.30, 0.36, 0.46")
mat("mat_wood", "0.62, 0.49, 0.34")
mat("mat_thatch", "0.68, 0.54, 0.32")
mat("mat_gold", "0.83, 0.66, 0.30")
mat("mat_flag", "0.85, 0.30, 0.25")
mat("mat_door", "0.30, 0.22, 0.16")
mat("mat_player", "0.99, 0.83, 0.28")   # 主角金色标记（unshaded 恒亮）
sub('sph_player', '\n'.join([
    '[sub_resource type="SphereMesh" id="sph_player"]',
    'radius = 7.0',
    'height = 14.0',
    'material = SubResource("mat_player")']))
sub('cyl_player', '\n'.join([
    '[sub_resource type="CylinderMesh" id="cyl_player"]',
    'top_radius = 1.6',
    'bottom_radius = 1.6',
    'height = 8.0',
    'material = SubResource("mat_player")']))
sub('mat_sea', '\n'.join([
    '[sub_resource type="StandardMaterial3D" id="mat_sea"]',
    'albedo_color = Color(0.13, 0.27, 0.48, 1)',
    'roughness = 0.95',
    'shading_mode = 0']))
# 海面 + 天空环境
sub('pl_sea', '\n'.join([
    '[sub_resource type="PlaneMesh" id="pl_sea"]',
    'size = Vector2(2600, 2600)']))
sub('sky_mat', '\n'.join([
    '[sub_resource type="ProceduralSkyMaterial" id="sky_mat"]',
    'sky_top_color = Color(0.62, 0.76, 0.95, 1)',
    'sky_horizon_color = Color(0.88, 0.90, 0.93, 1)',
    'ground_bottom_color = Color(0.35, 0.45, 0.60, 1)',
    'ground_horizon_color = Color(0.78, 0.82, 0.85, 1)']))
sub('sky', '[sub_resource type="Sky" id="sky"]\nsky_material = SubResource("sky_mat")')
sub('env', '\n'.join([
    '[sub_resource type="Environment" id="env"]',
    'background_mode = 2',
    'sky = SubResource("sky")',
    'ambient_light_source = 2',
    'ambient_light_color = Color(0.55, 0.62, 0.74, 1)',
    'ambient_light_energy = 0.3',
    'tonemap_mode = 0',
    'glow_enabled = false']))

# 网格资源（按 rank 模板复用，尺寸 ×1.4 便于全景可见）
box("box_stone0", 11.0, 2.6, 11.0, "mat_stone")
box("box_stone1", 8.4, 2.2, 8.4, "mat_stone")
box("box_stone2", 5.8, 1.8, 5.8, "mat_stone")
for i, sz in enumerate([12.0, 9.6, 7.4, 5.8]):
    box("box_w%d" % (i + 1), sz, 3.2, sz, "mat_wall" if i % 2 == 0 else "mat_wall_d")
for i, sz in enumerate([12.6, 10.2, 8.0, 6.4]):
    box("box_e%d" % (i + 1), sz, 0.6, sz, "mat_roof")
box("box_gold", 0.9, 0.8, 0.9, "mat_gold")
box("box_flag", 0.3, 1.2, 2.2, "mat_flag")
box("box_flagp", 0.22, 3.2, 0.22, "mat_door")
box("box_door", 2.0, 2.0, 0.5, "mat_door")
box("box_house", 3.8, 2.6, 3.8, "mat_wall")      # 町屋白墙
box("box_house_s", 2.6, 2.0, 2.6, "mat_wall")    # 小茅屋墙
cyl("cyl_thatch", 0.5, 2.4, 2.3, "mat_thatch")
cyl("cyl_thatch_s", 0.35, 1.8, 1.7, "mat_thatch")
cyl("cyl_cone", 0.05, 2.4, 2.2, "mat_roof")
cyl("cyl_cone_s", 0.05, 1.9, 1.7, "mat_roof")
# 人字屋顶（太阁2 町屋/天守顶）
sub('prism_roof', '\n'.join([
    '[sub_resource type="PrismMesh" id="prism_roof"]',
    'size = Vector3(6.4, 2.6, 6.8)',
    'material = SubResource("mat_roof")']))
sub('prism_roof_s', '\n'.join([
    '[sub_resource type="PrismMesh" id="prism_roof_s"]',
    'size = Vector3(4.4, 1.9, 4.8)',
    'material = SubResource("mat_roof")']))

# ---------- 节点输出 ----------
L = []

def T(name, parent, script=None, extra=()):
    s = '[node name="%s" type="%s" parent="%s"]' % (name, "Node3D", parent)
    if script:
        s = '[node name="%s" type="%s" parent="%s"]\nscript = ExtResource("%s")' % (name, "Node3D", parent, script)
    L.append(s)
    for k, v in extra:
        L.append("%s = %s" % (k, v))

def MI(parent, name, mesh_id, px, py, pz):
    L.append('[node name="%s" type="MeshInstance3D" parent="%s"]' % (name, parent))
    L.append("transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, %s, %s, %s)" % (px, py, pz))
    L.append("mesh = SubResource(\"%s\")" % mesh_id)

def label3d(name, parent, text, px, py, pz, fs=28, col="0.95, 0.93, 0.88"):
    L.append('[node name="%s" type="Label3D" parent="%s"]' % (name, parent))
    L.append("transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, %s, %s, %s)" % (px, py, pz))
    L.append('text = "%s"' % text)
    L.append("font_size = %d" % fs)
    L.append("outline_size = 6")
    L.append("outline_modulate = Color(0.12, 0.10, 0.06, 0.95)")
    L.append("modulate = Color(%s, 0.95)" % col)
    L.append("billboard = 1")
    L.append("no_depth_test = true")
    L.append('horizontal_alignment = 1')

# ---------- 城/村 3D 造型 ----------
def house(parent, dx, dy, dz, big=False, thatch=True):
    base = "box_house" if not big else "box_bighouse"
    if thatch:
        MI(parent, "h", base, dx, dy + 1.4, dz)
        MI(parent, "ht", "cyl_thatch" if not big else "cyl_thatch_s", dx, dy + 3.3, dz)
    else:
        MI(parent, "h", base, dx, dy + 2.2, dz)
        MI(parent, "ht", "cyl_cone_s", dx, dy + 4.8, dz)

def castle(parent, rank):
    # 太阁2 风格：天守剪影图标（白墙黑瓦 + 石垣 + 旗），无城下町
    if rank == 0:
        # 大城：三层天守（白墙方块层层收窄 + 黑瓦出檐 + 大蓝灰瓦顶 + 金饰 + 大旗）
        MI(parent, "stone", "box_stone0", 0, 1.3, 0)
        MI(parent, "w1", "box_w1", 0, 4.0, 0)
        MI(parent, "e1", "box_e1", 0, 2.7, 0)
        MI(parent, "w2", "box_w2", 0, 7.5, 0)
        MI(parent, "e2", "box_e2", 0, 6.2, 0)
        MI(parent, "w3", "box_w3", 0, 11.0, 0)
        MI(parent, "e3", "box_e3", 0, 9.7, 0)
        MI(parent, "prism", "prism_roof", 0, 14.8, 0)
        MI(parent, "gold", "box_gold", 0, 16.6, 0)
        MI(parent, "fp", "box_flagp", 0, 17.6, 0)
        MI(parent, "f", "box_flag", 0, 19.0, 0)
    elif rank == 1:
        # 中城：两层天守
        MI(parent, "stone", "box_stone1", 0, 1.1, 0)
        MI(parent, "w1", "box_w2", 0, 3.6, 0)
        MI(parent, "e1", "box_e2", 0, 2.5, 0)
        MI(parent, "w2", "box_w3", 0, 6.7, 0)
        MI(parent, "e2", "box_e3", 0, 5.6, 0)
        MI(parent, "prism", "prism_roof_s", 0, 9.8, 0)
        MI(parent, "gold", "box_gold", 0, 11.0, 0)
        MI(parent, "fp", "box_flagp", 0, 12.0, 0)
        MI(parent, "f", "box_flag", 0, 13.2, 0)
    else:
        # 小城：单层小天守
        MI(parent, "stone", "box_stone2", 0, 0.9, 0)
        MI(parent, "w1", "box_w4", 0, 3.0, 0)
        MI(parent, "e1", "box_e4", 0, 2.1, 0)
        MI(parent, "prism", "prism_roof_s", 0, 5.7, 0)
        MI(parent, "fp", "box_flagp", 0, 6.7, 0)
        MI(parent, "f", "box_flag", 0, 7.7, 0)

def town(parent, rank):
    if rank == 3:      # 大町：三间连排白墙黑瓦町屋
        for i, dx in enumerate([-3.6, 0.0, 3.6]):
            MI(parent, "h%d" % i, "box_house", dx, 1.3, 0)
            MI(parent, "r%d" % i, "prism_roof", dx, 3.4, 0)
    elif rank == 4:    # 小町：两间
        for i, dx in enumerate([-2.4, 2.4]):
            MI(parent, "h%d" % i, "box_house", dx, 1.3, 0)
            MI(parent, "r%d" % i, "prism_roof_s", dx, 3.0, 0)
    else:              # 村：一间茅草屋（干净独立）
        MI(parent, "h", "box_house_s", 0, 1.0, 0)
        MI(parent, "ht", "cyl_thatch_s", 0, 2.5, 0)

# ---------- 主流程 ----------
out = []
out.append("[gd_scene load_steps=%d format=3]" % (6 + len(subs)))
out.append('[ext_resource type="Script" path="res://src/world/world_screen_3d.gd" id="1_scr"]')
out.append('[ext_resource type="Script" path="res://src/world/WorldItem3D.gd" id="2_item"]')
out.append('[ext_resource type="Script" path="res://src/ui/UiButton.gd" id="3_ub"]')
out.append('[ext_resource type="Script" path="res://src/ui/UiLabel.gd" id="4_ul"]')
out.append('[ext_resource type="Script" path="res://src/ui/UiPanel.gd" id="5_up"]')
for sid, txt in subs:
    out.append(txt)

out.append('')
out.append('[node name="World3D" type="Node3D"]')
out.append('script = ExtResource("1_scr")')

out.append('')
out.append('[node name="Terrain" type="Node3D" parent="."]')
out.append('')
out.append('[node name="Sea" type="MeshInstance3D" parent="."]')
out.append('transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 542.0, -1.0, 507.0)')   # 水平海面（y=-1）；旧版误绕X轴旋转成竖直深蓝墙（地图中间的"屏障"）
out.append('mesh = SubResource("pl_sea")')
out.append('material_override = SubResource("mat_sea")')

out.append('')
out.append('[node name="Sun" type="DirectionalLight3D" parent="."]')
out.append('transform = Transform3D(0.7, 0.45, -0.55, 0, 0.77, 0.63, 0.71, -0.44, 0.54, 0, 0, 0)')
out.append('light_color = Color(1, 0.97, 0.9, 1)')
out.append('light_energy = 0.5')
out.append('shadow_enabled = true')

out.append('')
out.append('[node name="WorldEnvironment" type="WorldEnvironment" parent="."]')
out.append('environment = SubResource("env")')

# 河流
out.append('')
out.append('[node name="Rivers" type="Node3D" parent="."]')
for i, r in enumerate(d["rivers"]):
    pts = r["points"]
    p2 = ", ".join("%.1f, %.1f" % (q[0], q[1]) for q in pts)
    out.append('[node name="R%d_%s" type="Node3D" parent="Rivers"]' % (i, safe(r["name"])))
    out.append('script = ExtResource("2_item")')
    out.append('kind = "river"')
    out.append('pts2d = PackedVector2Array(%s)' % p2)
    out.append('line_w = 0.8')

# 道路
out.append('')
out.append('[node name="Roads" type="Node3D" parent="."]')
out.append('[node name="Trunk" type="Node3D" parent="Roads"]')
for i, r in enumerate(d["roads"]):
    if r["kind"] != "trunk":
        continue
    pts = r["points"]
    p2 = ", ".join("%.1f, %.1f" % (q[0], q[1]) for q in pts)
    out.append('[node name="T%d_%s" type="Node3D" parent="Roads/Trunk"]' % (i, safe(r["name"])))
    out.append('script = ExtResource("2_item")')
    out.append('kind = "road_trunk"')
    out.append('pts2d = PackedVector2Array(%s)' % p2)
    out.append('line_w = 1.1')
out.append('[node name="Branch" type="Node3D" parent="Roads"]')
for i, r in enumerate(d["roads"]):
    if r["kind"] != "branch":
        continue
    pts = r["points"]
    p2 = ", ".join("%.1f, %.1f" % (q[0], q[1]) for q in pts)
    out.append('[node name="B%d_%s" type="Node3D" parent="Roads/Branch"]' % (i, safe(r["name"])))
    out.append('script = ExtResource("2_item")')
    out.append('kind = "road_branch"')
    out.append('pts2d = PackedVector2Array(%s)' % p2)
    out.append('line_w = 0.6')

# 城 / 村
out.append('')
out.append('[node name="Cities" type="Node3D" parent="."]')
for c in d["cities"]:
    x, y, z = p3(c["x"], c["y"])
    rank = c["rank"]
    sn = safe(c["name"])
    out.append('[node name="C%d_%s" type="Node3D" parent="Cities"]' % (c["id"], sn))
    out.append('transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, %.1f, %.1f, %.1f)' % (x, y, z))
    # 建筑模型统一缩放（标签不缩放，保持可读）
    out.append('[node name="Bld" type="Node3D" parent="Cities/C%d_%s"]' % (c["id"], sn))
    out.append('scale = Vector3(0.78, 0.78, 0.78)')
    if c["type"] == "castle":
        castle("Cities/C%d_%s/Bld" % (c["id"], sn), 0 if rank == 0 else (1 if rank == 1 else 2))
        ly = 16.0 if rank == 0 else (12.0 if rank == 1 else 7.8)
    else:
        town("Cities/C%d_%s/Bld" % (c["id"], sn), rank)
        ly = 5.0 if rank == 3 else (4.4 if rank == 4 else 3.6)
    label3d("CityLabel", "Cities/C%d_%s" % (c["id"], sn), c["name"], 0, y + ly, 0, fs=26)

# 山峰雪顶
out.append('')
out.append('[node name="Peaks" type="Node3D" parent="."]')
for i, p in enumerate(d["peaks"]):
    x, y, z = p3(p["x"], p["y"])
    out.append('[node name="P%d_%s" type="Node3D" parent="Peaks"]' % (i, safe(p["name"])))
    out.append('script = ExtResource("2_item")')
    out.append('kind = "peak"')
    out.append('pts2d = PackedVector2Array(%.1f, %.1f)' % (p["x"], p["y"]))
    out.append('h_peak = %d' % p["h"])

# 景点
out.append('')
out.append('[node name="Sights" type="Node3D" parent="."]')
for i, s in enumerate(d["sights"]):
    x, y, z = p3(s["x"], s["y"])
    out.append('[node name="S%d_%s" type="Node3D" parent="Sights"]' % (i, safe(s["name"])))
    out.append('script = ExtResource("2_item")')
    out.append('kind = "sight"')
    out.append('sight_kind = "%s"' % s["kind"])
    out.append('pts2d = PackedVector2Array(%.1f, %.1f)' % (s["x"], s["y"]))

# 国名
out.append('')
out.append('[node name="Provinces" type="Node3D" parent="."]')
for p in d["provinces"]:
    x, y, z = p3(p["cx"], p["cy"])
    label3d("P_%s" % safe(p["name"]), "Provinces", p["name"], x, y + 8.0, z, fs=34)

# 玩家（金色标记：立柱 + 顶球，编辑器可见、运行时随脚本移动）
out.append('')
out.append('[node name="Player" type="Node3D" parent="."]')
x, y, z = p3(d["cities"][0]["x"], d["cities"][0]["y"])
out.append('transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, %.1f, %.1f, %.1f)' % (x, y + 1.6, z))
out.append('')
out.append('[node name="Marker" type="MeshInstance3D" parent="Player"]')
out.append('transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 5.0, 0)')
out.append('mesh = SubResource("cyl_player")')
out.append('material_override = SubResource("mat_player")')
out.append('')
out.append('[node name="MarkerTop" type="MeshInstance3D" parent="Player"]')
out.append('transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 12.0, 0)')
out.append('mesh = SubResource("sph_player")')
out.append('material_override = SubResource("mat_player")')

# 相机
out.append('')
out.append('[node name="Camera3D" type="Camera3D" parent="."]')
out.append('transform = Transform3D(0.87, 0.0, -0.49, 0.0, 1.0, 0.0, 0.49, 0.0, 0.87, 542.0, 420.0, 507.0)')
out.append('fov = 45.0')

# UI
out.append('')
out.append('[node name="UI" type="CanvasLayer" parent="."]')
out.append('')
out.append('[node name="InfoPanel" type="Control" parent="UI"]')
out.append('anchors_preset = 0')
out.append('offset_left = 12.0')
out.append('offset_top = 12.0')
out.append('offset_right = 300.0')
out.append('offset_bottom = 78.0')
out.append('script = ExtResource("5_up")')
out.append('')
out.append('[node name="Title" type="Label" parent="UI/InfoPanel"]')
out.append('offset_left = 12.0')
out.append('offset_top = 8.0')
out.append('offset_right = 288.0')
out.append('offset_bottom = 62.0')
out.append('text = "日本大地图(3D)"')
out.append('font_size = 22')
out.append('font_color = Color(0.96, 0.93, 0.86, 1)')
out.append('')
out.append('[node name="BackBtn" type="Button" parent="UI"]')
out.append('anchors_preset = 1')
out.append('anchor_left = 1.0')
out.append('anchor_right = 1.0')
out.append('offset_left = -170.0')
out.append('offset_top = 12.0')
out.append('offset_right = -12.0')
out.append('offset_bottom = 52.0')
out.append('text = "返回状态画面"')
out.append('script = ExtResource("3_ub")')

with open(DST, "w", encoding="utf-8") as f:
    txt = "\n".join(out + L)
    # Godot 4 的 .tscn 中 Color 必须 4 参数（补 alpha）
    txt = re.sub(r"Color\(([\d.]+), ([\d.]+), ([\d.]+)\)", r"Color(\1, \2, \3, 1)", txt)
    f.write(txt)
print("written", DST, len(out) + len(L), "lines")
