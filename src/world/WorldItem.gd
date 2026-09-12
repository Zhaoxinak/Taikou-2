@tool
extends Node2D
## 大地图自绘元素（Item）：城市/町/山脉/河流/道路/景点/陆地/国名/玩家
## @tool：编辑器内实时绘制外观（场景化后在 Godot 编辑器可见、可归类）。
## 所有元素均为真实节点（非贴图），数据来自 data/world_map.json（生成器预置进 .tscn）。

# —— kind 取值与绘制规则 ——
#   land      : points=多边形，填充陆地色（海由场景背景色表示）
#   river     : points=折线，蓝色水系
#   mountain  : points=折线，褐色山系
#   peak      : points=单点，山峰三角 + 名
#   road_trunk: points=折线，暗金干道
#   road_branch:points=折线，灰色支线
#   city      : points=单点，金色大圆 + 名（城）
#   town      : points=单点，米灰小圆 + 名（町/里/砦）
#   sight     : points=单点，红/金菱形 + 名（名所）
#   province  : 单点国名标签（半透明底）
#   player    : 玩家角色（箭头，可移动/朝向）

const LAND_COLOR   := Color(0.62, 0.78, 0.52, 1.0)   # 陆地绿
const LAND_EDGE    := Color(0.35, 0.50, 0.32, 1.0)   # 海岸线
const RIVER_COLOR  := Color(0.30, 0.55, 0.85, 0.95)  # 河蓝
const MOUNT_COLOR  := Color(0.45, 0.33, 0.22, 0.90)  # 山褐
const PEAK_COLOR   := Color(0.62, 0.50, 0.33, 1.0)
const TRUNK_COLOR  := Color(0.85, 0.72, 0.45, 0.90)  # 干道金
const BRANCH_COLOR := Color(0.70, 0.68, 0.62, 0.55)  # 支线灰
const CITY_COLOR   := Color(0.95, 0.80, 0.35, 1.0)   # 城金
const TOWN_COLOR   := Color(0.78, 0.75, 0.68, 1.0)   # 町米
const SIGHT_COLOR  := Color(0.88, 0.42, 0.30, 1.0)   # 名所红
const PROV_COLOR   := Color(0.95, 0.90, 0.80, 0.55)
const PLAYER_COLOR := Color(0.30, 0.65, 0.95, 1.0)

## 元素类型（决定绘制方式）
@export var kind: String = "city"
## 显示名（城市/山/河/景点/国名；空则不画标签）
@export var label: String = ""
## 几何数据（多边形/折线/单点，设计空间坐标，已含世界变换）
@export var points: PackedVector2Array = PackedVector2Array()
## 附加数据（峰的标高 / 城 id / 道路两端城 id 等）
@export var extra: Dictionary = {}

const UiTheme = preload("res://src/ui/UiTheme.gd")
var _font: Font = null

func _ready() -> void:
	_font = UiTheme.font()
	if Engine.is_editor_hint():
		queue_redraw()


## 供 world_screen.gd 在数据加载后设置几何（运行时也走这里）
func set_item(p_kind: String, p_label: String, p_points: PackedVector2Array, p_extra: Dictionary = {}) -> void:
	kind = p_kind
	label = p_label
	points = p_points
	extra = p_extra
	queue_redraw()


func _draw() -> void:
	match kind:
		"land":
			if points.size() >= 3:
				draw_colored_polygon(points, LAND_COLOR)
				draw_polyline(points + PackedVector2Array([points[0]]), LAND_EDGE, 2.0)
		"river":
			_draw_line(RIVER_COLOR, 2.5)
		"mountain":
			_draw_line(MOUNT_COLOR, 2.0)
		"road_trunk":
			_draw_line(TRUNK_COLOR, 2.5)
		"road_branch":
			_draw_line(BRANCH_COLOR, 1.0)
		"peak":
			_draw_peak()
		"city":
			_draw_city(6.0, CITY_COLOR, 20)
		"town":
			_draw_city(3.5, TOWN_COLOR, 16)
		"sight":
			_draw_sight()
		"province":
			_draw_province()
		"player":
			_draw_player()
		"selection":
			_draw_selection()


func _draw_line(col: Color, width: float) -> void:
	if points.size() < 2:
		return
	draw_polyline(points, col, width, true)


func _draw_city(r: float, col: Color, fs: int) -> void:
	if points.is_empty():
		return
	var p := points[0]
	draw_circle(p, r, Color(0, 0, 0, 0.4))
	draw_circle(p, r, col)
	if not label.is_empty():
		var f := _font
		if f != null:
			draw_string(f, Vector2(p.x + r + 3, p.y - r - 3 + UiTheme.baseline_y(label, fs, fs)),
				label, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(0.95, 0.93, 0.88, 0.92))


func _draw_peak() -> void:
	if points.is_empty():
		return
	var p := points[0]
	var h := float(extra.get("h", 0))
	# 三角山峰
	draw_colored_polygon(PackedVector2Array([p + Vector2(0, -10), p + Vector2(-7, 2), p + Vector2(7, 2)]), PEAK_COLOR)
	if not label.is_empty():
		var f := _font
		if f != null:
			var fs := 14
			var txt := label if h <= 0 else "%s %dm" % [label, int(h)]
			draw_string(f, Vector2(p.x + 9, p.y - 6 + UiTheme.baseline_y(txt, fs, fs)),
				txt, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(0.9, 0.85, 0.75, 0.9))


func _draw_sight() -> void:
	if points.is_empty():
		return
	var p := points[0]
	var sz := 6.0
	# 菱形（红）
	draw_colored_polygon(PackedVector2Array([
		p + Vector2(0, -sz), p + Vector2(sz, 0), p + Vector2(0, sz), p + Vector2(-sz, 0)]), SIGHT_COLOR)
	if not label.is_empty():
		var f := _font
		if f != null:
			var fs := 16
			draw_string(f, Vector2(p.x + sz + 3, p.y - sz + UiTheme.baseline_y(label, fs, fs)),
				label, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(0.95, 0.85, 0.75, 0.95))


func _draw_province() -> void:
	if points.is_empty() or label.is_empty():
		return
	var p := points[0]
	var f := _font
	if f == null:
		return
	var fs := 26
	var tw := f.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
	var rect := Rect2(p.x - tw * 0.5 - 8, p.y - fs - 6, tw + 16, fs + 10)
	draw_rect(rect, Color(0.10, 0.08, 0.05, 0.55))
	draw_string(f, Vector2(p.x - tw * 0.5, p.y - 4 + UiTheme.baseline_y(label, fs, fs)),
		label, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, PROV_COLOR)


func _draw_player() -> void:
	# 角色：圆头 + 身体 + 朝向箭头（extra.facing 弧度）
	var p := points[0] if not points.is_empty() else Vector2.ZERO
	var face := float(extra.get("facing", 0.0))
	draw_circle(p + Vector2(0, -5), 5.0, PLAYER_COLOR)
	draw_circle(p, 6.5, Color(0.15, 0.35, 0.55, 1.0))
	# 朝向箭头
	var dirv := Vector2(cos(face), sin(face))
	draw_line(p, p + dirv * 14.0, PLAYER_COLOR, 2.0)
	draw_circle(p + dirv * 14.0, 2.0, PLAYER_COLOR)


func _draw_selection() -> void:
	if points.is_empty():
		return
	var p := points[0]
	draw_arc(p, 12.0, 0.0, TAU, 32, Color(1.0, 0.9, 0.5, 0.95), 2.0)
