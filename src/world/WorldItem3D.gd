@tool
class_name WorldItem3D
extends Node3D
## 大地图 3D 元素组件：高度图采样 + 贴地河流/道路 + 雪顶/景点小模型
## 编辑器内即生成 mesh（@tool + _ready），全部为可视化 3D 节点（非贴图）

const HM_PATH := "res://data/heightmap.json"
const S := 0.25                 # 3D 世界缩放（2D px × 0.25 → 3D 单位）
const SEA_Y := 0.0              # 海平面（3D）

static var _hm: Dictionary = {}
static var _hm_loaded := false

## 世界坐标(wx,wy)[2D px] → 3D 地形高度（单位）
static func hm_height(wx: float, wy: float) -> float:
	if not _hm_loaded:
		_hm_loaded = true
		if FileAccess.file_exists(HM_PATH):
			var f := FileAccess.open(HM_PATH, FileAccess.READ)
			_hm = JSON.parse_string(f.get_as_text())
	if _hm.is_empty():
		return 0.0
	var o: Array = _hm.get("origin", [0, 0])
	var cell: float = float(_hm.get("cell", 13.0))
	var nw := int(_hm.get("w", 384))
	var nh := int(_hm.get("h", 384))
	var ix := clampi(int((wx - o[0]) / cell), 0, nw - 1)
	var iy := clampi(int((wy - o[1]) / cell), 0, nh - 1)
	var g: Array = _hm.get("data", [])
	if iy >= g.size():
		return 0.0
	var row: Array = g[iy]
	if ix >= row.size():
		return 0.0
	return float(row[ix]) * S

## 3D 坐标（2D px → 3D 单位，贴地）
static func to3(pos2: Vector2) -> Vector3:
	return Vector3(pos2.x * S, hm_height(pos2.x, pos2.y), pos2.y * S)

## 高度→顶点色（海/滩/低地/高地/山/雪）
static func hm_color(h: float) -> Color:
	if h <= -1.5:
		return Color(0.13, 0.28, 0.52, 1.0)   # 深海
	if h <= 0.0:
		return Color(0.20, 0.40, 0.66, 1.0)   # 浅海
	if h <= 0.7:
		return Color(0.82, 0.76, 0.55, 1.0)   # 滩
	if h <= 5.0:
		return Color(0.34, 0.55, 0.26, 1.0)   # 低地绿
	if h <= 11.0:
		return Color(0.42, 0.60, 0.28, 1.0)   # 中地绿
	if h <= 18.0:
		return Color(0.56, 0.58, 0.30, 1.0)   # 丘陵
	if h <= 28.0:
		return Color(0.60, 0.48, 0.30, 1.0)   # 山地
	if h <= 38.0:
		return Color(0.52, 0.42, 0.28, 1.0)   # 高山
	return Color(0.93, 0.95, 0.94, 1.0)        # 雪


## 节点类型：river / road_trunk / road_branch / peak / sight
@export var kind: String = ""
@export var pts2d: PackedVector2Array = PackedVector2Array()   # 2D 世界坐标
@export var line_w: float = 4.0                                 # 贴地带宽度
@export var tint: Color = Color(1, 1, 1)
@export var h_peak: float = 0.0                                 # 山峰标高（2D 高度）
@export var sight_kind: String = ""                             # 寺社/山/绝景/瀑布/湖

var _built := false


func _ready() -> void:
	if _built:
		return
	_built = true
	match kind:
		"river": _build_band(0.9, Color(0.30, 0.56, 0.88), 0.45)
		"road_trunk": _build_band(1.6, Color(0.78, 0.64, 0.40), 1.3)
		"road_branch": _build_band(0.7, Color(0.66, 0.60, 0.50), 0.9)
		"peak": _build_peak()
		"sight": _build_sight()


## 贴地窄带（沿折线生成三角带，高度随地形）
func _build_band(he: float, col: Color, bed_w: float) -> void:
	if pts2d.size() < 2:
		return
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := pts2d.size()
	var verts: Array[Vector3] = []
	for i in range(n):
		var p2 := Vector2(pts2d[i].x, pts2d[i].y)
		var c := to3(p2) + Vector3(0, he, 0)
		verts.append(c)
	for i in range(n - 1):
		var a: Vector3 = verts[i]
		var b: Vector3 = verts[i + 1]
		var dir := (b - a)
		dir.y = 0.0
		var side := dir.normalized().cross(Vector3.UP).normalized()
		var w := line_w * 0.5
		var aw := w + bed_w
		var bw := w
		if i > 0:
			# 前段衔接点微调（避免折角缺口，简单叠加）
			pass
		# 每个线段：两个矩形面（底面+顶面）
		var a1 := a + side * aw
		var a2 := a - side * aw
		var b1 := b + side * aw
		var b2 := b - side * aw
		# 顶面
		st.add_vertex(a1)
		st.add_vertex(a2)
		st.add_vertex(b2)
		st.add_vertex(a1)
		st.add_vertex(b2)
		st.add_vertex(b1)
		# 底面（略下沉，防 Z 面）
		var a1b := a1 - Vector3(0, 0.6, 0)
		var a2b := a2 - Vector3(0, 0.6, 0)
		var b1b := b1 - Vector3(0, 0.6, 0)
		var b2b := b2 - Vector3(0, 0.6, 0)
		st.add_vertex(a1b)
		st.add_vertex(b2b)
		st.add_vertex(a2b)
		st.add_vertex(a1b)
		st.add_vertex(b1b)
		st.add_vertex(b2b)
	st.generate_normals()
	var mesh := st.commit()
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var mat := StandardMaterial3D.new()
	mat.albedo_color = col
	mat.roughness = 0.9
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mi.material_override = mat
	add_child(mi)


## 山峰雪顶装饰（地形已隆起，顶部加白色锥帽，尺寸随峰高）
func _build_peak() -> void:
	if pts2d.is_empty():
		return
	var p2 := Vector2(pts2d[0].x, pts2d[0].y)
	var base := to3(p2)
	var base_h := base.y   # 地形峰顶 3D 高度
	var hh := clampf(base_h * 0.16, 1.5, 12.0)   # 雪帽高度
	var r := clampf(base_h * 0.22, 2.5, 12.0)    # 雪帽底半径
	var cone := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.05
	cm.bottom_radius = r
	cm.height = hh
	cone.mesh = cm
	cone.position = base + Vector3(0, hh * 0.5, 0)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.95, 0.96, 0.95)
	mat.roughness = 0.8
	cone.material_override = mat
	add_child(cone)


## 景点小模型（寺社=塔 / 山=石碑 / 绝景=鸟居 / 瀑布 / 湖）
func _build_sight() -> void:
	if pts2d.is_empty():
		return
	var base := to3(Vector2(pts2d[0].x, pts2d[0].y))
	match sight_kind:
		"寺社":
			# 五重塔：两段 Box + 尖顶
			_add_box(base + Vector3(0, 1.6, 0), Vector3(2.2, 3.2, 2.2), Color(0.78, 0.22, 0.18))
			_add_box(base + Vector3(0, 4.6, 0), Vector3(1.4, 2.2, 1.4), Color(0.80, 0.24, 0.20))
			_add_box(base + Vector3(0, 6.6, 0), Vector3(0.5, 1.8, 0.5), Color(0.30, 0.28, 0.25))
		"山":
			_add_box(base + Vector3(0, 2.0, 0), Vector3(0.8, 4.0, 0.8), Color(0.85, 0.80, 0.70))
		"绝景":
			# 小石碑
			_add_box(base + Vector3(0, 1.4, 0), Vector3(2.4, 2.8, 0.6), Color(0.82, 0.78, 0.70))
		"瀑布":
			_add_box(base + Vector3(0, 1.2, 0), Vector3(1.0, 2.4, 1.0), Color(0.55, 0.72, 0.92))
		"湖":
			_add_cyl(base + Vector3(0, 0.3, 0), 3.2, 0.6, Color(0.40, 0.62, 0.85))
		_:
			_add_box(base + Vector3(0, 1.2, 0), Vector3(1.4, 2.4, 1.4), Color(0.72, 0.30, 0.25))


func _add_box(pos: Vector3, size: Vector3, col: Color) -> void:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.position = pos
	var mat := StandardMaterial3D.new()
	mat.albedo_color = col
	mat.roughness = 0.85
	mi.material_override = mat
	add_child(mi)


func _add_cyl(pos: Vector3, r: float, h: float, col: Color) -> void:
	var mi := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = r
	cm.bottom_radius = r
	cm.height = h
	mi.mesh = cm
	mi.position = pos
	var mat := StandardMaterial3D.new()
	mat.albedo_color = col
	mat.roughness = 0.8
	mi.material_override = mat
	add_child(mi)
