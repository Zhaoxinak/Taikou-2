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
		"road_trunk": _draw_road(9.0, 5.0, C_ROAD_BED, C_ROAD_FACE, 0)
		"road_branch": _draw_road(4.5, 2.2, C_BRANCH_BED, C_BRANCH, 0)
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
	draw_polyline(points, Color(0.85, 0.92, 0.98, 0.9), 10.0, true)   # 岸/光
	draw_polyline(points, C_RIVER, 6.0, true)
	draw_polyline(points, C_RIVER_LIT, 2.5, true)


# ── 山系：多层立体山脊（宽体凸起 + 投影）─────────────────
func _draw_ridge() -> void:
	if points.size() < 2:
		return
	# 投影
	var sh := PackedVector2Array()
	for p in points:
		sh.append(p + Vector2(3, 4))
	draw_polyline(sh, Color(0, 0, 0, 0.25), 16.0, true)
	# 深色宽底 + 中色 + 亮色高光，末端圆收
	draw_polyline(points, C_MOUNT_DARK, 16.0, true)
	draw_polyline(points, C_MOUNT_MID, 9.5, true)
	draw_polyline(points, C_MOUNT_LIT, 3.5, true)
	# 山脊两端的"山头"（圆点）
	for p in [points[0], points[points.size() - 1]]:
		draw_circle(p, 7.0, C_MOUNT_DARK)
		draw_circle(p, 3.5, C_MOUNT_LIT)


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
			_draw_outline_text(f, Vector2(p.x - tw * 0.5, p.y - sz - 8 + UiTheme.baseline_y(txt, fs, fs)),
				txt, fs, C_TEXT_DIM, 1.0)


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


# ── 城（castle）：按史实规模三档城堡造型 ──
#   rank0 大城（兵粮≥4000：稻叶山/春日山/一乘谷/月山富田…）：四层天守 + 城下町
#   rank1 中城（1000~3999：米泽/黑川/高取…）：三层天守 + 少量屋
#   rank2 小城（<1000：丹波龟山/桑折…）：二层小天守
func _draw_city() -> void:
	if points.is_empty():
		return
	var p := points[0]
	var rank := int(extra.get("rank", 1))
	match rank:
		0: _draw_castle_rank0(p)
		1: _draw_castle_rank1(p)
		_: _draw_castle_rank2(p)
	if not label.is_empty() and show_label:
		_draw_label(p + Vector2(0, 18), label, 21, C_TEXT, true)


## rank0 大城：巨天守（四层）+ 城下町 8 屋 + 大门/双旗
func _draw_castle_rank0(p: Vector2) -> void:
	draw_ellipse_shadow(p + Vector2(5, 7), 30.0)
	# 城下町（大范围环绕）
	for i in range(8):
		var a := TAU * float(i) / 8.0 + 0.35
		var hp := p + Vector2(cos(a) * 40.0, sin(a) * 26.0 + 12.0)
		_draw_house(hp, float(i * 17 + 5), 5.0)
	# 石垣（高台）
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-26, 10), p + Vector2(26, 10), p + Vector2(23, 0), p + Vector2(-23, 0)]), C_CASTLE_STONE)
	draw_line(p + Vector2(-23, 0), p + Vector2(23, 0), C_CASTLE_DARK.darkened(0.3), 1.6)
	# 四层天守（每层收窄）
	var layers := [
		[16.0, 0, -9, C_CASTLE_DARK], [12.0, -9, -18, C_CASTLE_STONE],
		[9.0, -18, -27, C_CASTLE_DARK], [6.5, -27, -36, C_CASTLE_STONE],
	]
	for l in layers:
		draw_colored_polygon(PackedVector2Array([
			p + Vector2(-l[0], l[1]), p + Vector2(l[0], l[1]),
			p + Vector2(l[0] * 0.76, l[2]), p + Vector2(-l[0] * 0.76, l[2])]), l[3])
	# 四层瓦顶
	var roofs := [[14.0, -9], [10.5, -18], [8.0, -27], [5.8, -36]]
	for r0 in roofs:
		var w0: float = r0[0]
		var y0: float = r0[1]
		draw_colored_polygon(PackedVector2Array([
			p + Vector2(-w0, y0), p + Vector2(w0, y0), p + Vector2(0, y0 - 5.5)]), C_ROOF)
	# 大门 + 围墙
	draw_rect(Rect2(p + Vector2(-4.5, 2), Vector2(9, 7)), Color(0.35, 0.25, 0.18, 1))
	draw_line(p + Vector2(-23, 0), p + Vector2(-23, 7), C_CASTLE_DARK, 1.8)
	draw_line(p + Vector2(23, 0), p + Vector2(23, 7), C_CASTLE_DARK, 1.8)
	# 双旗
	for dx in [-5.0, 5.0]:
		draw_line(p + Vector2(dx, -36), p + Vector2(dx, -45), Color(0.2, 0.16, 0.12, 1), 1.3)
		draw_colored_polygon(PackedVector2Array([
			p + Vector2(dx, -45), p + Vector2(dx + 9, -42), p + Vector2(dx, -39.5)]),
			Color(0.85, 0.3, 0.25, 1))


## rank1 中城：三层天守 + 城下 4 屋 + 单旗
func _draw_castle_rank1(p: Vector2) -> void:
	draw_ellipse_shadow(p + Vector2(4, 6), 22.0)
	for i in range(4):
		var a := TAU * float(i) / 4.0 + 0.6
		var hp := p + Vector2(cos(a) * 28.0, sin(a) * 20.0 + 9.0)
		_draw_house(hp, float(i * 13 + 7), 4.0)
	# 石垣
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-19, 8), p + Vector2(19, 8), p + Vector2(17, 0), p + Vector2(-17, 0)]), C_CASTLE_STONE)
	draw_line(p + Vector2(-17, 0), p + Vector2(17, 0), C_CASTLE_DARK.darkened(0.3), 1.4)
	# 三层天守
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-13, 0), p + Vector2(13, 0), p + Vector2(10, -9), p + Vector2(-10, -9)]), C_CASTLE_DARK)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-10, -9), p + Vector2(10, -9), p + Vector2(7.5, -18), p + Vector2(-7.5, -18)]), C_CASTLE_STONE)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-6.8, -18), p + Vector2(6.8, -18), p + Vector2(5, -26), p + Vector2(-5, -26)]), C_CASTLE_DARK)
	# 三层瓦顶
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-11, -9), p + Vector2(11, -9), p + Vector2(0, -14)]), C_ROOF)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-8.5, -18), p + Vector2(8.5, -18), p + Vector2(0, -23)]), C_ROOF)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-5.8, -26), p + Vector2(5.8, -26), p + Vector2(0, -31)]), C_ROOF)
	# 大门 + 旗
	draw_rect(Rect2(p + Vector2(-3, 1), Vector2(6, 6)), Color(0.35, 0.25, 0.18, 1))
	draw_line(p + Vector2(0, -31), p + Vector2(0, -38), Color(0.2, 0.16, 0.12, 1), 1.2)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(0, -38), p + Vector2(8, -35), p + Vector2(0, -32.5)]), Color(0.85, 0.3, 0.25, 1))


## rank2 小城：二层小天守（支城）
func _draw_castle_rank2(p: Vector2) -> void:
	draw_ellipse_shadow(p + Vector2(3, 4), 13.0)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-12, 6), p + Vector2(12, 6), p + Vector2(10.5, 0), p + Vector2(-10.5, 0)]), C_CASTLE_STONE)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-8.5, 0), p + Vector2(8.5, 0), p + Vector2(6.5, -8), p + Vector2(-6.5, -8)]), C_CASTLE_DARK)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-5.5, -8), p + Vector2(5.5, -8), p + Vector2(4, -15), p + Vector2(-4, -15)]), C_CASTLE_STONE)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-7, -8), p + Vector2(7, -8), p + Vector2(0, -12.5)]), C_ROOF)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-4.8, -15), p + Vector2(4.8, -15), p + Vector2(0, -19.5)]), C_ROOF)
	draw_line(p + Vector2(0, -19.5), p + Vector2(0, -24), Color(0.2, 0.16, 0.12, 1), 1.0)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(0, -24), p + Vector2(5.5, -22), p + Vector2(0, -20.5)]), Color(0.85, 0.3, 0.25, 1))


# ── 町（town）：按史实规模三档市镇造型 ──
#   rank3 大町（兵粮≥3000：大坂/小田原/骏府/冈山…）：豪商大屋 + 町屋群
#   rank4 小镇（1000~2999：二条/清洲/大垣…）：町屋 4 栋
#   rank5 村庄（<1000：江户/白石…）：村屋 1~2 栋
func _draw_town() -> void:
	if points.is_empty():
		return
	var p := points[0]
	var rank := int(extra.get("rank", 4))
	match rank:
		3: _draw_town_rank3(p)
		4: _draw_town_rank4(p)
		_: _draw_town_rank5(p)
	if not label.is_empty() and show_label:
		_draw_label(p + Vector2(0, 13), label, 16, C_TEXT_DIM, true)


## rank3 大町/城下町：豪商大屋（白墙大屋敷）+ 6 栋町屋 + 市街
func _draw_town_rank3(p: Vector2) -> void:
	draw_ellipse_shadow(p + Vector2(3, 4), 16.0)
	# 环绕町屋
	for i in range(6):
		var a := TAU * float(i) / 6.0 + 0.4
		var hp := p + Vector2(cos(a) * 26.0, sin(a) * 18.0 + 7.0)
		_draw_house(hp, float(i * 9 + 3), 4.0)
	# 豪商大屋敷（白墙 + 大瓦顶 + 门）
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-11, 6), p + Vector2(11, 6), p + Vector2(11, -6), p + Vector2(-11, -6)]), Color(0.88, 0.85, 0.78, 1))
	draw_line(p + Vector2(-11, -6), p + Vector2(11, -6), C_HOUSE_ROOF, 2.0)
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(-13, -6), p + Vector2(13, -6), p + Vector2(0, -15)]), Color(0.42, 0.32, 0.24, 1))
	draw_rect(Rect2(p + Vector2(-2.5, -1), Vector2(5, 6)), Color(0.3, 0.22, 0.16, 1))
	draw_line(p + Vector2(0, -15), p + Vector2(0, -19), Color(0.2, 0.16, 0.12, 1), 1.0)


## rank4 小镇：町屋 4 栋错落
func _draw_town_rank4(p: Vector2) -> void:
	draw_ellipse_shadow(p + Vector2(2, 3), 11.0)
	var offs := [Vector2(-11, 6), Vector2(9, 7), Vector2(-6, -5), Vector2(10, -4)]
	for i in range(4):
		_draw_house(p + offs[i], float(i * 7 + 2), 4.0)


## rank5 村庄：村屋 2 栋（简朴小村）
func _draw_town_rank5(p: Vector2) -> void:
	draw_ellipse_shadow(p + Vector2(2, 2), 7.0)
	_draw_house(p + Vector2(-6, 3), 3.0, 4.0)
	_draw_house(p + Vector2(7, 4), 11.0, 3.0)


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


# ── 国名标签：浅色文字 + 深色描边（无背景块，像印在地图上）──
func _draw_province() -> void:
	if points.is_empty() or label.is_empty() or not show_label:
		return
	var p := points[0]
	var f := _font
	if f == null:
		return
	var fs := 24
	var tw := f.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
	var pos := Vector2(p.x - tw * 0.5, p.y + UiTheme.baseline_y(label, fs, fs))
	_draw_outline_text(f, pos, label, fs, C_PROV_TX, 1.6)


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
## 带深色描边的文字（4 向偏移，印在地图上的干净感）
func _draw_outline_text(f: Font, pos: Vector2, txt: String, fs: int, col: Color, w: float = 1.0) -> void:
	var outline := Color(0.12, 0.10, 0.06, 0.92)
	for off in [Vector2(-w, 0), Vector2(w, 0), Vector2(0, -w), Vector2(0, w)]:
		draw_string(f, pos + off, txt, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, outline)
	draw_string(f, pos, txt, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, col)


func _draw_label(pos: Vector2, txt: String, fs: int, col: Color, center: bool) -> void:
	var f := _font
	if f == null:
		return
	var x := pos.x
	if center:
		var tw := f.get_string_size(txt, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
		x -= tw * 0.5
	_draw_outline_text(f, Vector2(x, pos.y + UiTheme.baseline_y(txt, fs, fs)), txt, fs, col, 1.0)


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
