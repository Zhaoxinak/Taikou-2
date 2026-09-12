extends Node2D
## 日本大地图（真实地理还原）：全部元素为场景预置 item（world_screen.tscn，编辑器可见）。
## 交互：滚轮缩放 / 拖拽平移 / 点击城池→沿道路真实移动（Dijkstra 寻路 + 平滑移动 + 朝向）。
## 数据：data/world_map.json（build_world_map.py 生成，200 城真实经纬度等）。

const UiTheme = preload("res://src/ui/UiTheme.gd")

const _SPEED := 160.0          # 移动速度 px/s（设计空间）
const _CLICK_R := 22.0         # 城点击半径
const _ZOOM_MIN := 0.55
const _ZOOM_MAX := 3.2

var _cities: Dictionary = {}    # id -> {name, x, y, province, type}
var _city_by_name: Dictionary = {}
var _adj: Dictionary = {}       # 城 id -> [{to, dist}]
var _map_data: Dictionary = {}
var _info_label = null
var _hint_label = null
var _player = null
var _camera: Camera2D = null
var _world: Node2D = null

# 移动状态
var _path: Array = []           # [城id, ...]（含起点终点）
var _seg_from: Vector2 = Vector2.ZERO
var _seg_to: Vector2 = Vector2.ZERO
var _seg_progress := 0.0
var _moving := false
var _drag_pos := Vector2.ZERO
var _dragging := false


func _ready() -> void:
	_camera = $Camera2D
	_world = $World
	_player = $World/Player
	_info_label = $UI/InfoPanel/InfoLabel
	_hint_label = $UI/HintLabel

	# 图数据（寻路需要；节点已在场景预置）
	var d: Dictionary = _load_map_data()
	for c in d.get("cities", []):
		var cid := int(c["id"])
		_cities[cid] = c
		_city_by_name[str(c["name"])] = cid
	for r in d.get("roads", []):
		if r["kind"] != "branch":
			continue
		var a := int(r["a"])
		var b := int(r["b"])
		var dist := _city_dist(a, b)
		if not _adj.has(a):
			_adj[a] = []
		if not _adj.has(b):
			_adj[b] = []
		_adj[a].append({"to": b, "dist": dist})
		_adj[b].append({"to": a, "dist": dist})

	# 玩家初始位置：主角所在城（未开局 → 三户 0）
	var start_id := _protagonist_city()
	_player.points = PackedVector2Array([_city_pos(start_id)])
	_player.queue_redraw()
	_update_info("", start_id)
	_refresh_hint()


func _load_map_data() -> Dictionary:
	if not _map_data.is_empty():
		return _map_data
	var path := "res://data/world_map.json"
	if not FileAccess.file_exists(path):
		push_error("[WorldScreen] 缺少 data/world_map.json（先运行 scripts/build_world_map.py）")
		return {}
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
	if parsed is Dictionary:
		_map_data = parsed
	return _map_data


func _city_pos(cid: int) -> Vector2:
	if not _cities.has(cid):
		return Vector2.ZERO
	return Vector2(float(_cities[cid]["x"]), float(_cities[cid]["y"]))


func _city_dist(a: int, b: int) -> float:
	return _city_pos(a).distance_to(_city_pos(b))


func _protagonist_city() -> int:
	var gs := get_node_or_null("/root/GameState")
	if gs == null or not gs.is_started():
		return 0
	var p: Dictionary = gs.get_protagonist()
	var cid := int(p.get("city", 0))
	return cid if _cities.has(cid) else 0


# ── 交互：缩放 / 平移 / 点击 ───────────────────────────────
func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_WHEEL_UP and mb.pressed:
			_zoom_camera(1.12)
			get_viewport().set_input_as_handled()
		elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN and mb.pressed:
			_zoom_camera(1.0 / 1.12)
			get_viewport().set_input_as_handled()
		elif mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				_dragging = true
				_drag_pos = mb.position
			else:
				_dragging = false
				# 点击（非拖拽）→ 选城移动
				if _drag_dist(mb.position) < 6.0:
					_pick_city(get_global_mouse_position())
			get_viewport().set_input_as_handled()
	elif event is InputEventMouseMotion and _dragging:
		var mm := event as InputEventMouseMotion
		_world.position += mm.relative
		get_viewport().set_input_as_handled()


func _drag_dist(p: Vector2) -> float:
	return p.distance_to(_drag_pos)


func _zoom_camera(f: float) -> void:
	var z: Vector2 = _camera.zoom * f
	z.x = clampf(z.x, _ZOOM_MIN, _ZOOM_MAX)
	z.y = clampf(z.y, _ZOOM_MIN, _ZOOM_MAX)
	_camera.zoom = z


func _pick_city(world_pos: Vector2) -> void:
	var best := -1
	var best_d := _CLICK_R
	for cid in _cities:
		var d: float = _city_pos(cid).distance_to(world_pos)
		if d < best_d:
			best_d = d
			best = cid
	if best < 0:
		return
	_show_selection(best)
	_goto_city(best)


func _show_selection(cid: int) -> void:
	var sel: Node2D = $World/Selection
	sel.points = PackedVector2Array([_city_pos(cid)])
	sel.visible = true
	sel.queue_redraw()


# ── 寻路：Dijkstra（按道路网欧氏距离加权）──
func _goto_city(target: int) -> void:
	var start := _protagonist_city()
	if start == target:
		_update_info(_city_name(target), target)
		return
	if not _adj.has(start) or not _adj.has(target):
		_update_info(_city_name(target), target)
		return
	# Dijkstra
	var dist := {start: 0.0}
	var prev := {}
	var pq := [[0.0, start]]
	while not pq.is_empty():
		pq.sort_custom(func(a, b): return a[0] < b[0])
		var cur: Array = pq.pop_front()
		var dcur: float = cur[0]
		var u: int = cur[1]
		if u == target:
			break
		if dcur > dist.get(u, 1e18):
			continue
		for e in _adj.get(u, []):
			var nd: float = dcur + e["dist"]
			if nd < dist.get(int(e["to"]), 1e18):
				dist[int(e["to"])] = nd
				prev[int(e["to"])] = u
				pq.append([nd, int(e["to"])])
	if not prev.has(target):
		_update_info(_city_name(target), target)
		return
	# 还原路径
	var path: Array = [target]
	var cur2 := target
	while prev.has(cur2):
		cur2 = prev[cur2]
		path.push_front(cur2)
	_path = path
	_seg_from = _city_pos(int(_path[0]))
	_seg_to = _city_pos(int(_path[1]))
	_seg_progress = 0.0
	_moving = true
	_update_info(_city_name(int(_path[0])), int(_path[0]))


func _city_name(cid: int) -> String:
	if not _cities.has(cid):
		return "?"
	return str(_cities[cid]["name"])


# ── 移动：沿路径段平滑移动（真实感：速度 + 朝向）──
func _process(delta: float) -> void:
	if not _moving or _path.size() < 2:
		return
	_seg_progress += _SPEED * delta / maxf(_seg_from.distance_to(_seg_to), 1.0)
	if _seg_progress >= 1.0:
		_seg_progress = 1.0
		var arrived := int(_path[1])
		_player.points = PackedVector2Array([_city_pos(arrived)])
		_player.queue_redraw()
		_path.pop_front()
		if _path.size() >= 2:
			_seg_from = _city_pos(int(_path[0]))
			_seg_to = _city_pos(int(_path[1]))
			_seg_progress = 0.0
			_update_info(_city_name(arrived), arrived)
		else:
			_moving = false
			_update_info(_city_name(arrived), arrived)
		return
	var p: Vector2 = _seg_from.lerp(_seg_to, _seg_progress)
	_player.points = PackedVector2Array([p])
	# 朝向 = 移动方向
	_player.extra["facing"] = (_seg_to - _seg_from).angle()
	_player.queue_redraw()


func _update_info(cur_name: String, cid: int) -> void:
	if _info_label == null:
		return
	var gs := get_node_or_null("/root/GameState")
	var line := "所在地：%s" % cur_name
	if gs != null and gs.is_started():
		var st: Dictionary = gs.get_status()
		line = "%s　　%d 年 %d 月　金 %d" % [line, int(st.get("year", 0)), int(st.get("month", 0)), int(st.get("money", 0))]
	if _cities.has(cid):
		line += "　（%s）" % _province_name(int(_cities[cid]["province"]))
	_info_label.text = line


func _province_name(pid: int) -> String:
	var d := _load_map_data()
	var ps: Array = d.get("provinces", [])
	if pid >= 0 and pid < ps.size():
		return str(ps[pid]["name"])
	return "?"


func _refresh_hint() -> void:
	if _hint_label != null:
		_hint_label.text = "滚轮缩放 · 拖拽平移 · 点击城池移动"


func _on_back() -> void:
	get_tree().change_scene_to_file("res://scenes/screens/status_screen.tscn")
