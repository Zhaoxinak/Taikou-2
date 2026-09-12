@tool
extends Node2D
## 大地图自绘元素（Item）：伪 3D 立体风格（非平面贴图，编辑器可见、可归类）
## 立体手法：多层叠色（山脊/海岸）、锥体+雪顶（山峰）、城堡/屋（城池）、
## 带厚度路面（道路）、渐变海面（sea）、层次地形（land 内缩色带）。
## 数据来自 data/world_map.json（生成器预置进 .tscn）。

# —— kind 取值 ——
#   sea       : points=矩形四角，渐变海面 + 波纹
#   land      : points=多边形，层次陆地（海岸+内缩色带+阴影）
#   river     : points=折线，立体水带
#   mountain  : points=折线，多层立体山脊
#   peak      : points=单点，锥体山（雪顶），extra.h=标高
#   road_trunk: points=折线，厚路（褐底+金面）
#   road_branch:points=折线，细路
#   city      : points=单点，立体城堡 + 名
#   town      : points=单点，小屋 + 名
#   sight     : points=单点，图标（寺社/山/绝景/瀑布/湖）+ 名
#   province  : 国名标签（半透明底）
#   player    : 立体小人 + 朝向
#   selection : 光环

const C_SEA_DEEP  := Color(0.10, 0.22, 0.42, 1.0)
const C_SEA       := Color(0.16, 0.32, 0.55, 1.0)
const C_SEA_LIGHT := Color(0.30, 0.50, 0.72, 1.0)
const C_LAND_EDGE := Color(0.30, 0.46, 0.26, 1.0)   # 海岸线（深绿）
const C_LAND_SHORE:= Color(0.78, 0.72, 0.50, 1.0)   # 滩色
const C_LAND_LOW  := Color(0.52, 0.68, 0.42, 1.0)   # 低地
const C_LAND_MID  := Color(0.58, 0.74, 0.46, 1.0)   # 中地
const C_LAND_HIGH := Color(0.66, 0.80, 0.52, 1.0)   # 高地
const C_RIVER     := Color(0.30, 0.58, 0.90, 0.95)
const C_RIVER_LIT := Color(0.52, 0.75, 0.97, 0.95)
const C_MOUNT_DARK:= Color(0.30, 0.22, 0.14, 0.95)
const C_MOUNT_MID := Color(0.45, 0.34, 0.22, 0.95)
const C_MOUNT_LIT := Color(0.62, 0.48, 0.30, 0.95)
const C_PEAK_SHADE:= Color(0.38, 0.30, 0.22, 1.0)
const C_PEAK_LIT  := Color(0.72, 0.58, 0.36, 1.0)
const C_SNOW      := Color(0.94, 0.95, 0.92, 1.0)
const C_ROAD_BED  := Color(0.42, 0.30, 0.18, 0.85)
const C_ROAD_FACE := Color(0.88, 0.76, 0.50, 0.95)
const C_BRANCH_BED:= Color(0.40, 0.36, 0.30, 0.40)
const C_BRANCH    := Color(0.72, 0.68, 0.58, 0.75)
const C_CASTLE_STONE := Color(0.62, 0.58, 0.52, 1.0)
const C_CASTLE_DARK  := Color(0.42, 0.38, 0.34, 1.0)
const C_ROOF      := Color(0.30, 0.28, 0.40, 1.0)   # 深蓝灰瓦
const C_HOUSE_WALL:= Color(0.80, 0.74, 0.60, 1.0)
const C_HOUSE_ROOF:= Color(0.55, 0.38, 0.22, 1.0)
const C_SIGHT     := Color(0.90, 0.45, 0.32, 1.0)
const C_TEXT      := Color(0.95, 0.93, 0.88, 0.95)
const C_TEXT_DIM  := Color(0.95, 0.93, 0.88, 0.72)
const C_PROV_BG   := Color(0.10, 0.08, 0.05, 0.55)
const C_PROV_TX   := Color(0.95, 0.90, 0.80, 0.85)
const C_PLAYER    := Color(0.32, 0.66, 0.96, 1.0)
const C_PLAYER_DK := Color(0.13, 0.36, 0.60, 1.0)
const C_SEL       := Color(1.0, 0.90, 0.50, 0.95)
const C_SHADOW    := Color(0.0, 0.0, 0.0, 0.30)

## 元素类型（决定绘制方式）
@export var kind: String = "city"
## 显示名（空则不画标签）
@export var label: String = ""
## 几何数据（多边形/折线/单点，设计空间坐标）
@export var points: PackedVector2Array = PackedVector2Array()
## 附加数据（peak 的 h / city 的 id / sight 的 kind 等）
@export var extra: Dictionary = {}
## 是否显示文字标签（缩放分级 LOD 控制）
@export var show_label: bool = true

const UiTheme = preload("res://src/ui/UiTheme.gd")
var _font: Font = null

func _ready() -> void:
	_font = UiTheme.font()
	if Engine.is_editor_hint():
		queue_redraw()


func set_item(p_kind: String, p_label: String, p_points: PackedVector2Array, p_extra: Dictionary = {}) -> void:
	kind = p_kind
	label = p_label
	points = p_points
	extra = p_extra
	queue_redraw()


func _draw() -> void:
	match kind:
		"sea": _draw_sea()
		"land": _draw_land()
		"river": _draw_river()
		"mountain": _draw_ridge()
		"peak": _draw_peak()
		"road_trunk": _draw_road(6.0, 3.2, C_ROAD_BED, C_ROAD_FACE, 0)
		"road_branch": _draw_road(3.0, 1.4, C_BRANCH_BED, C_BRANCH, 0)
		"city": _draw_city()
		"town": _draw_town()
		"sight": _draw_sight()
		"province": _draw_province()
		"player": _draw_player()
		"selection": _draw_selection()


# ── 海：渐变底 + 波纹 ─────────────────────────────────────
func _draw_sea() -> void:
	if points.size() < 4:
		return
	var r := Rect2(points[0], points[2] - points[0])
	# 分层海色（模拟纵深渐变）
	var bands := 8
	for i in range(bands):
		var t := float(i) / float(bands)
		var bcol := C_SEA_DEEP.lerp(C_SEA_LIGHT, t)
		var y0 := r.position.y + r.size.y * t
		var y1 := r.position.y + r.size.y * (t + 1.0 / bands)
		draw_rect(Rect2(r.position.x, y0, r.size.x, y1 - y0), bcol)
	# 波纹（白色弧线，疏密有致）
	var wave_col := Color(1, 1, 1, 0.16)
	for i in range(14):
		var y := r.position.y + r.size.y * (0.10 + 0.064 * i)
		var x0 := r.position.x + 30.0 * (0.5 + 0.5 * sin(i * 1.7))
		var x1 := r.position.x + r.size.x - 30.0 * (0.5 + 0.5 * sin(i * 2.3 + 1.0))
		_draw_wave(x0, y, x1, wave_col)


func _draw_wave(x0: float, y: float, x1: float, col: Color) -> void:
	var pts := PackedVector2Array()
	var n := 6
	for i in range(n + 1):
		var t := float(i) / float(n)
		pts.append(Vector2(lerpf(x0, x1, t), y + sin(t * TAU * 2.0) * 3.0))
	draw_polyline(pts, col, 1.5, true)


# ── 陆地：立体切片 + 层次地形（海岸 + 内缩色带 + 高光）────
func _draw_land() -> void:
	if points.size() < 3:
		return
	# 立体切片：右下偏移深色层（厚度）
	var sh := PackedVector2Array()
	for p in points:
		sh.append(p + Vector2(7, 9))
	draw_colored_polygon(sh, Color(0.10, 0.16, 0.09, 0.85))
	var sh2 := PackedVector2Array()
	for p in points:
		sh2.append(p + Vector2(4, 5))
	draw_colored_polygon(sh2, Color(0.22, 0.32, 0.18, 0.9))
	# 海岸滩色（外扩）
	draw_colored_polygon(points, C_LAND_SHORE)
	# 内陆层次：向质心内缩 4 层（色差拉大，起伏感）+ 中央高地/山芯
	var c := _centroid(points)
	var layers := [
		[0.965, C_LAND_EDGE],
		[0.90, C_LAND_LOW],
		[0.76, C_LAND_MID],
		[0.58, C_LAND_HIGH],
	]
	for layer in layers:
		var inset := _inset(points, c, layer[0])
		if inset.size() >= 3:
			draw_colored_polygon(inset, layer[1])
	# 中央高地（棕）与山芯（深棕）：地形抬升感
	var up := _inset(points, c, 0.42)
	if up.size() >= 3:
		draw_colored_polygon(up, Color(0.60, 0.56, 0.38, 0.9))
	var core := _inset(points, c, 0.24)
	if core.size() >= 3:
		draw_colored_polygon(core, Color(0.52, 0.48, 0.34, 0.95))
	# 高光（左上边缘亮线）
	var hl := PackedVector2Array()
	for p in points:
		hl.append(p - Vector2(1, 1))
	draw_polyline(hl, Color(0.85, 0.92, 0.72, 0.35), 2.0, true)


func _centroid(pts: PackedVector2Array) -> Vector2:
	var s := Vector2.ZERO
	for p in pts:
		s += p
	return s / float(pts.size())


func _inset(pts: PackedVector2Array, c: Vector2, t: float) -> PackedVector2Array:
	var out := PackedVector2Array()
	for p in pts:
		out.append(c + (p - c) * t)
	return out


# ── 河流：立体水带（白边 + 蓝带 + 高光）────────────────────
func _draw_river() -> void:
	if points.size() < 2:
		return
	draw_polyline(points, Color(0.85, 0.92, 0.98, 0.9), 8.0, true)   # 岸/光
	draw_polyline(points, C_RIVER, 5.0, true)
	draw_polyline(points, C_RIVER_LIT, 2.0, true)


# ── 山系：多层立体山脊（宽体凸起 + 投影）─────────────────
func _draw_ridge() -> void:
	if points.size() < 2:
		return
	# 投影
	var sh := PackedVector2Array()
	for p in points:
		sh.append(p + Vector2(3, 4))
	draw_polyline(sh, Color(0, 0, 0, 0.25), 14.0, true)
	# 深色宽底 + 中色 + 亮色高光，末端圆收
	draw_polyline(points, C_MOUNT_DARK, 14.0, true)
	draw_polyline(points, C_MOUNT_MID, 8.5, true)
	draw_polyline(points, C_MOUNT_LIT, 3.0, true)
	# 山脊两端的"山头"（圆点）
	for p in [points[0], points[points.size() - 1]]:
		draw_circle(p, 6.0, C_MOUNT_DARK)
		draw_circle(p, 3.0, C_MOUNT_LIT)


# ── 山峰：按类型分型的立体山（富士/火山/雪峰/高山/低山）────
func _draw_peak() -> void:
	if points.is_empty():
		return
	var p := points[0]
	var h := float(extra.get("h", 0))
	var nm := str(extra.get("name", label))
	var sz := clampf(20.0 + h / 110.0, 20.0, 58.0)
	# 底部阴影 + 底座等高线
	draw_ellipse_shadow(p + Vector2(4, 6), sz * 1.2)
	draw_ellipse_ring(p + Vector2(0, 4), sz * 1.05, Color(0.30, 0.44, 0.24, 0.5))
	draw_ellipse_ring(p + Vector2(0, 4), sz * 0.75, Color(0.38, 0.52, 0.28, 0.6))
	if nm == "富士山":
		_draw_peak_fuji(p, sz)
	elif nm in ["阿苏山", "樱岛", "浅间山", "开闻岳"]:
		_draw_peak_volcano(p, sz)
	elif h >= 2500.0:
		_draw_peak_cone(p, sz, 0.36)
	elif h >= 1500.0:
		_draw_peak_cone(p, sz, 0.18)
	else:
		_draw_peak_dome(p, sz)
	if not label.is_empty() and show_label:
		var f := _font
		if f != null:
			var txt := label if h <= 0 else "%s %dm" % [label, int(h)]
			var fs := 12
			var tw := f.get_string_size(txt, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
			draw_string(f, Vector2(p.x - tw * 0.5, p.y - sz - 8 + UiTheme.baseline_y(txt, fs, fs)),
				txt, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, C_TEXT_DIM)


## 富士山：宽缓大锥 + 大范围雪顶 + 火山口
func _draw_peak_fuji(p: Vector2, sz: float) -> void:
	var top := p + Vector2(0, -sz)
	var base_l := p + Vector2(-sz * 1.35, 5)
	var base_r := p + Vector2(sz * 1.35, 5)
	draw_colored_polygon(PackedVector2Array([top, base_l, p + Vector2(0, 5)]), C_PEAK_LIT)
	draw_colored_polygon(PackedVector2Array([top, p + Vector2(0, 5), base_r]), C_PEAK_SHADE)
	# 大雪顶（约占上部 40%）
	var sw := sz * 0.52
	var sh := sz * 0.42
	draw_colored_polygon(PackedVector2Array([
		top, top + Vector2(sw, sh), top + Vector2(-sw, sh)]), C_SNOW)
	# 火山口
	draw_ellipse_ring(top + Vector2(0, sz * 0.10), sz * 0.13, Color(0.6, 0.42, 0.24, 0.8))
	draw_line(base_l, top, C_PEAK_SHADE.darkened(0.35), 1.4)
	draw_line(top, base_r, C_PEAK_SHADE.darkened(0.35), 1.4)


## 火山：平顶锥 + 火口（红褐火口）
func _draw_peak_volcano(p: Vector2, sz: float) -> void:
	var top := p + Vector2(0, -sz * 0.86)
	var base_l := p + Vector2(-sz, 5)
	var base_r := p + Vector2(sz, 5)
	var col_l := Color(0.58, 0.42, 0.30, 1)
	var col_r := Color(0.42, 0.30, 0.22, 1)
	draw_colored_polygon(PackedVector2Array([top, base_l, p + Vector2(0, 5)]), col_l)
	draw_colored_polygon(PackedVector2Array([top, p + Vector2(0, 5), base_r]), col_r)
	# 平顶 + 火口（暗红内凹）
	draw_rect(Rect2(top + Vector2(-sz * 0.22, 0), Vector2(sz * 0.44, sz * 0.14)), col_r.darkened(0.2))
	draw_rect(Rect2(top + Vector2(-sz * 0.12, sz * 0.02), Vector2(sz * 0.24, sz * 0.10)), Color(0.7, 0.3, 0.16, 0.9))
	# 山体裂线
	draw_line(p + Vector2(-sz * 0.3, 2), p + Vector2(-sz * 0.18, sz * 0.4), Color(0.3, 0.22, 0.16, 0.6), 1.2)


## 雪峰 / 高山：标准锥体，雪顶比例不同
func _draw_peak_cone(p: Vector2, sz: float, snow_ratio: float) -> void:
	var top := p + Vector2(0, -sz)
	var base_l := p + Vector2(-sz, 5)
	var base_r := p + Vector2(sz, 5)
	draw_colored_polygon(PackedVector2Array([top, base_l, p + Vector2(0, 5)]), C_PEAK_LIT)
	draw_colored_polygon(PackedVector2Array([top, p + Vector2(0, 5), base_r]), C_PEAK_SHADE)
	var sw := sz * 0.40
	var sh := sz * snow_ratio
	draw_colored_polygon(PackedVector2Array([
		top, top + Vector2(sw, sh), top + Vector2(-sw, sh)]), C_SNOW)
	draw_line(base_l, top, C_PEAK_SHADE.darkened(0.35), 1.3)
	draw_line(top, base_r, C_PEAK_SHADE.darkened(0.35), 1.3)


## 低山：圆顶小山丘（弧线顶）
func _draw_peak_dome(p: Vector2, sz: float) -> void:
	var base_l := p + Vector2(-sz * 0.9, 4)
	var base_r := p + Vector2(sz * 0.9, 4)
	var top := p + Vector2(0, -sz * 0.85)
	var pts := PackedVector2Array()
	var n := 12
	for i in range(n + 1):
		var t := float(i) / float(n)
		var a := lerpf(0.0, PI, t)
		pts.append(Vector2(lerpf(base_l.x, base_r.x, t), top.y + sin(a) * sz * 0.85))
	draw_colored_polygon(pts, C_PEAK_LIT)
	draw_colored_polygon(PackedVector2Array([
		base_r, base_l, top + Vector2(0, sz * 0.85)]), C_PEAK_SHADE)
	draw_polyline(pts, C_PEAK_SHADE.darkened(0.3), 1.3, true)


# ── 道路：厚路面（深色底 + 亮色路面）───────────────────────
func _draw_road(w_bed: float, w_face: float, bed: Color, face: Color, _pad: int) -> void:
	if points.size() < 2:
		return
	draw_polyline(points, Color(0, 0, 0, 0.20), w_bed + 1.5, true)
	draw_polyline(points, bed, w_bed, true)
	draw_polyline(points, face, w_face, true)


# ── 城：按 rank 立体城堡（rank0 大名居城三层天守 / rank1 普通城二层）──
func _draw_city() -> void:
	if points.is_empty():
		return
	var p := points[0]
	var rank := int(extra.get("rank", 1))
	if rank <= 0:
		_draw_castle_big(p)
	elif rank == 1:
		_draw_castle_mid(p)
	else:
		_draw_house(p, float(extra.get("seed", 0)), 10.0)
	if not label.is_empty() and show_label:
		_draw_label(p + Vector2(0, 16), label, 20, C_TEXT, true)


## 大名居城/大城市：石垣 + 三层天守 + 大门 + 双旗 + 城下町
func _draw_castle_big(p: Vector2) -> void:
	draw_ellipse_shadow(p + Vector2(4, 6), 24.0)
	# 城下町（绕城小屋群）
	for i in range(6):
		var a := TAU * float(i) / 6.0 + 0.5
		var hp := p + Vector2(cos(a) * 30.0, sin(a) * 22.0 + 10.0)
		_draw_house(hp, float(i * 11 + 3), 4.5)
	# 石垣（宽台）
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-18, 8), p + Vector2(18, 8), p + Vector2(16, 0), p + Vector2(-16, 0)]), C_CASTLE_STONE)
	draw_line(p + Vector2(-16, 0), p + Vector2(16, 0), C_CASTLE_DARK.darkened(0.3), 1.4)
	# 三层天守（每层收窄）
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-12, 0), p + Vector2(12, 0), p + Vector2(9, -8), p + Vector2(-9, -8)]), C_CASTLE_DARK)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-9, -8), p + Vector2(9, -8), p + Vector2(7, -16), p + Vector2(-7, -16)]), C_CASTLE_STONE)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-6.5, -16), p + Vector2(6.5, -16), p + Vector2(4.8, -24), p + Vector2(-4.8, -24)]), C_CASTLE_DARK)
	# 三层瓦顶
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-10, -8), p + Vector2(10, -8), p + Vector2(0, -13)]), C_ROOF)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-7.5, -16), p + Vector2(7.5, -16), p + Vector2(0, -21)]), C_ROOF)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-5.5, -24), p + Vector2(5.5, -24), p + Vector2(0, -29)]), C_ROOF)
	# 大门 + 围墙
	draw_rect(Rect2(p + Vector2(-3.5, 1), Vector2(7, 6)), Color(0.35, 0.25, 0.18, 1))
	draw_line(p + Vector2(-16, 0), p + Vector2(-16, 6), C_CASTLE_DARK, 1.6)
	draw_line(p + Vector2(16, 0), p + Vector2(16, 6), C_CASTLE_DARK, 1.6)
	# 双旗
	for dx in [-4.0, 4.0]:
		draw_line(p + Vector2(dx, -29), p + Vector2(dx, -36), Color(0.2, 0.16, 0.12, 1), 1.2)
		draw_colored_polygon(PackedVector2Array([
			p + Vector2(dx, -36), p + Vector2(dx + 8, -33.5), p + Vector2(dx, -31)]),
			Color(0.85, 0.3, 0.25, 1))


## 普通城：石垣 + 二层天守 + 单旗
func _draw_castle_mid(p: Vector2) -> void:
	draw_ellipse_shadow(p + Vector2(3, 5), 14.0)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-13, 6), p + Vector2(13, 6), p + Vector2(12, 0), p + Vector2(-12, 0)]), C_CASTLE_STONE)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-9, 0), p + Vector2(9, 0), p + Vector2(7, -9), p + Vector2(-7, -9)]), C_CASTLE_DARK)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-6, -9), p + Vector2(6, -9), p + Vector2(4.5, -17), p + Vector2(-4.5, -17)]), C_CASTLE_STONE)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-7.5, -9), p + Vector2(7.5, -9), p + Vector2(0, -14)]), C_ROOF)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-5.5, -17), p + Vector2(5.5, -17), p + Vector2(0, -22)]), C_ROOF)
	draw_line(p + Vector2(0, -22), p + Vector2(0, -28), Color(0.2, 0.16, 0.12, 1), 1.2)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(0, -28), p + Vector2(7, -25.5), p + Vector2(0, -23)]), Color(0.85, 0.3, 0.25, 1))


# ── 町：差异化小屋（屋顶颜色按 seed 变化）────────────────
func _draw_town() -> void:
	if points.is_empty():
		return
	var p := points[0]
	var seed := float(extra.get("seed", 0))
	_draw_house(p, seed, 7.0)
	if not label.is_empty() and show_label:
		_draw_label(p + Vector2(0, 12), label, 15, C_TEXT_DIM, true)


## 小屋：墙 + 三角顶（屋顶色 4 选 1）+ 小院
func _draw_house(p: Vector2, seed: float, base: float) -> void:
	draw_ellipse_shadow(p + Vector2(2, 3), base + 2.0)
	var roof_col := C_HOUSE_ROOF
	var r := int(seed) % 4
	match r:
		0: roof_col = Color(0.55, 0.38, 0.22, 1)   # 茅草棕
		1: roof_col = Color(0.42, 0.30, 0.30, 1)   # 深赤
		2: roof_col = Color(0.36, 0.42, 0.52, 1)   # 蓝灰瓦
		3: roof_col = Color(0.52, 0.56, 0.38, 1)   # 灰绿
	# 院墙
	draw_rect(Rect2(p + Vector2(-base - 4, -2), Vector2((base + 4) * 2, 7)), Color(0.72, 0.66, 0.52, 0.55))
	# 屋身
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-base, 4), p + Vector2(base, 4), p + Vector2(base, -3), p + Vector2(-base, -3)]), C_HOUSE_WALL)
	# 屋顶
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-base - 2.5, -3), p + Vector2(base + 2.5, -3), p + Vector2(0, -base - 6)]), roof_col)


# ── 景点：按类型小图标 ────────────────────────────────────
func _draw_sight() -> void:
	if points.is_empty():
		return
	var p := points[0]
	var sk := str(extra.get("kind", ""))
	match sk:
		"寺社":
			# 宝塔：两层塔身 + 尖顶
			draw_colored_polygon(PackedVector2Array([
				p + Vector2(-6, 6), p + Vector2(6, 6), p + Vector2(6, 0), p + Vector2(-6, 0)]), C_CASTLE_STONE)
			draw_colored_polygon(PackedVector2Array([
				p + Vector2(-5, 0), p + Vector2(5, 0), p + Vector2(0, -9)]), C_ROOF)
			draw_line(p + Vector2(0, -9), p + Vector2(0, -13), Color(0.2, 0.16, 0.12, 1), 1.0)
		"山":
			draw_colored_polygon(PackedVector2Array([
				p + Vector2(-8, 5), p + Vector2(0, -9), p + Vector2(0, 5)]), C_PEAK_SHADE)
			draw_colored_polygon(PackedVector2Array([
				p + Vector2(0, 5), p + Vector2(0, -9), p + Vector2(8, 5)]), C_PEAK_LIT)
		"瀑布":
			draw_rect(Rect2(p + Vector2(-2, -8), Vector2(4, 14)), C_RIVER)
			draw_line(p + Vector2(0, -8), p + Vector2(0, 6), C_RIVER_LIT, 1.2)
		"湖":
			draw_circle(p, 7.0, C_RIVER)
			draw_circle(p, 4.0, C_RIVER_LIT)
		_:
			# 绝景等：金色星标
			var sz := 7.0
			draw_colored_polygon(PackedVector2Array([
				p + Vector2(0, -sz), p + Vector2(sz * 0.32, -sz * 0.32), p + Vector2(sz, 0),
				p + Vector2(sz * 0.32, sz * 0.32), p + Vector2(0, sz),
				p + Vector2(-sz * 0.32, sz * 0.32), p + Vector2(-sz, 0),
				p + Vector2(-sz * 0.32, -sz * 0.32)]), C_SIGHT)
	if not label.is_empty() and show_label:
		_draw_label(p + Vector2(0, 14), label, 15, C_TEXT_DIM, true)


# ── 国名标签 ─────────────────────────────────────────────
func _draw_province() -> void:
	if points.is_empty() or label.is_empty() or not show_label:
		return
	var p := points[0]
	var f := _font
	if f == null:
		return
	var fs := 21
	var tw := f.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
	var rect := Rect2(p.x - tw * 0.5 - 8, p.y - fs - 6, tw + 16, fs + 12)
	draw_rect(rect, C_PROV_BG)
	draw_rect(rect, Color(0.85, 0.72, 0.45, 0.30), false, 1.0)
	draw_string(f, Vector2(p.x - tw * 0.5, p.y - 2 + UiTheme.baseline_y(label, fs, fs)),
		label, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, C_PROV_TX)


# ── 玩家：立体小人 + 朝向 ────────────────────────────────
func _draw_player() -> void:
	var p := points[0] if not points.is_empty() else Vector2.ZERO
	var face := float(extra.get("facing", 0.0))
	# 影子
	draw_ellipse_shadow(p + Vector2(2, 7), 8.0)
	# 身体（圆头 + 躯干 + 腿）
	draw_circle(p + Vector2(0, -10), 4.5, C_PLAYER)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-4.5, -6), p + Vector2(4.5, -6), p + Vector2(3, 3), p + Vector2(-3, 3)]), C_PLAYER_DK)
	draw_line(p + Vector2(-2, 3), p + Vector2(-3, 8), C_PLAYER_DK, 1.6)
	draw_line(p + Vector2(2, 3), p + Vector2(3, 8), C_PLAYER_DK, 1.6)
	# 朝向箭头
	var dirv := Vector2(cos(face), sin(face))
	draw_line(p + dirv * 9.0, p + dirv * 17.0, C_PLAYER, 2.2)
	draw_circle(p + dirv * 17.0, 2.2, C_PLAYER)


# ── 选中：光环 + 指示箭头 ────────────────────────────────
func _draw_selection() -> void:
	if points.is_empty():
		return
	var p := points[0]
	draw_arc(p, 13.0, 0.0, TAU, 40, C_SEL, 2.4)
	draw_arc(p, 17.0, 0.0, TAU, 40, Color(1, 1, 1, 0.4), 1.2)
	# 顶部指示箭头
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(0, -30), p + Vector2(-5, -22), p + Vector2(5, -22)]), C_SEL)


# ── 工具 ─────────────────────────────────────────────────
func _draw_label(pos: Vector2, txt: String, fs: int, col: Color, center: bool) -> void:
	var f := _font
	if f == null:
		return
	var x := pos.x
	if center:
		var tw := f.get_string_size(txt, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
		x -= tw * 0.5
	draw_string(f, Vector2(x, pos.y + UiTheme.baseline_y(txt, fs, fs)),
		txt, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, col)


func draw_ellipse_shadow(center: Vector2, r: float) -> void:
	var pts := PackedVector2Array()
	var n := 20
	for i in range(n):
		var a := TAU * float(i) / float(n)
		pts.append(center + Vector2(cos(a) * r, sin(a) * r * 0.42))
	draw_colored_polygon(pts, C_SHADOW)


func draw_ellipse_ring(center: Vector2, r: float, col: Color) -> void:
	var pts := PackedVector2Array()
	var n := 24
	for i in range(n + 1):
		var a := TAU * float(i) / float(n)
		pts.append(center + Vector2(cos(a) * r, sin(a) * r * 0.45))
	draw_polyline(pts, col, 1.4, true)
