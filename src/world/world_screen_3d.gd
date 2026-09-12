extends Node3D
## 3D 大地图主脚本：地形生成（高度图→三角网+顶点色）、相机（缩放/旋转/平移）、
## 点击拾取（运行时碰撞体）、寻路移动（沿道路折线）、国名/城名 LOD

const MAP_JSON := "res://data/world_map.json"
const HM_PATH := "res://data/heightmap.json"
const WorldItem3D := preload("res://src/world/WorldItem3D.gd")
const S := 0.25
const _SPEED := 130.0        # 3D 行走速度（单位/秒）
const _CLICK_R := 14.0       # 点击半径（3D 单位）
const _PICK_R := 12.0        # 拾取碰撞球半径

var _data: Dictionary = {}
var _cities: Array = []
var _roads: Array = []
var _adj: Dictionary = {}          # id -> [(to, road_index)]
var _city_node: Dictionary = {}    # id -> Node3D
var _city_pos2: Dictionary = {}    # id -> Vector2(2D px)
var _city_name: Dictionary = {}

# 相机
var _cam: Camera3D = null
var _target := Vector3(542, 0, 507)
var _dist := 700.0
var _yaw := 0.0
var _pitch := 55.0 * PI / 180.0
var _drag_btn := -1
var _drag_last := Vector2.ZERO

# 玩家
var _player: Node3D = null
var _moving := false
var _route: Array[Vector3] = []
var _route_i := 0


func _ready() -> void:
	_load_data()
	_build_terrain()
	_setup_cities()
	_cam = $Camera3D
	_player = $Player
	_set_player_pos(0)
	_update_cam()
	# UI
	var back: Button = $UI/BackBtn
	back.pressed.connect(func():
		get_tree().change_scene_to_file("res://scenes/screens/status_screen.tscn"))


func _load_data() -> void:
	var f := FileAccess.open(MAP_JSON, FileAccess.READ)
	_data = JSON.parse_string(f.get_as_text())
	_cities = _data["cities"]
	_roads = _data["roads"]
	for c in _cities:
		var cid: int = c["id"]
		_city_name[cid] = c["name"]
		_city_pos2[cid] = Vector2(c["x"], c["y"])
	# 邻接表（仅支线含 a/b 城对；干道为视觉用）
	for i in range(_roads.size()):
		var r: Dictionary = _roads[i]
		if r.get("kind", "") != "branch":
			continue
		var a: int = int(r["a"])
		var b: int = int(r["b"])
		if not _adj.has(a):
			_adj[a] = []
		if not _adj.has(b):
			_adj[b] = []
		_adj[a].append([b, i])
		_adj[b].append([a, i])


# ── 地形 ──────────────────────────────────────────────
func _build_terrain() -> void:
	var f := FileAccess.open(HM_PATH, FileAccess.READ)
	var hm: Dictionary = JSON.parse_string(f.get_as_text())
	var nw := int(hm["w"])
	var nh := int(hm["h"])
	var cell := float(hm["cell"])
	var o: Array = hm["origin"]
	var g: Array = hm["data"]
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for j in range(nh - 1):
		for i in range(nw - 1):
			var v00 := _hmv(g, i, j, o, cell)
			var v10 := _hmv(g, i + 1, j, o, cell)
			var v01 := _hmv(g, i, j + 1, o, cell)
			var v11 := _hmv(g, i + 1, j + 1, o, cell)
			var c00 := WorldItem3D.hm_color(v00.y)
			var c10 := WorldItem3D.hm_color(v10.y)
			var c01 := WorldItem3D.hm_color(v01.y)
			var c11 := WorldItem3D.hm_color(v11.y)
			# 两个三角形（对角分割）
			st.set_color(c00)
			st.add_vertex(v00)
			st.set_color(c10)
			st.add_vertex(v10)
			st.set_color(c01)
			st.add_vertex(v01)
			st.set_color(c01)
			st.add_vertex(v01)
			st.set_color(c10)
			st.add_vertex(v10)
			st.set_color(c11)
			st.add_vertex(v11)
	st.generate_normals()
	var mesh := st.commit()
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.roughness = 1.0
	mi.material_override = mat
	$Terrain.add_child(mi)


func _hmv(g: Array, i: int, j: int, o: Array, cell: float) -> Vector3:
	var h2 := float(g[j][i])
	var x: float = (float(o[0]) + (i + 0.5) * cell) * S
	var z: float = (float(o[1]) + (j + 0.5) * cell) * S
	var h3 := h2 * S
	var v := Vector3(x, h3, z)
	v = v + Vector3(0, 0.05, 0)
	return v


# ── 城池：运行时碰撞体 + 城名 LOD ──────────────────────
func _setup_cities() -> void:
	for c in _cities:
		var cid: int = c["id"]
		var node := get_node_or_null("Cities/C%d_%s" % [cid, c["name"]])
		if node == null:
			continue
		_city_node[cid] = node
		# 拾取碰撞体
		var body := StaticBody3D.new()
		var shape := CollisionShape3D.new()
		var sph := SphereShape3D.new()
		sph.radius = _PICK_R
		shape.shape = sph
		body.add_child(shape)
		node.add_child(body)
		body.set_meta("city_id", cid)


## 城名标签 LOD：按相机距离显示
func _process_city_labels() -> void:
	var cam_pos: Vector3 = _cam.global_position
	for cid in _city_node:
		var node: Node3D = _city_node[cid]
		var lb := node.get_node_or_null("CityLabel")
		if lb == null:
			continue
		var d := node.global_position.distance_to(cam_pos)
		var rank: int = int(_city_rank(cid))
		var show := false
		if rank <= 1 and d < 500.0:
			show = true
		elif rank <= 3 and d < 300.0:
			show = true
		elif d < 160.0:
			show = true
		if lb.visible != show:
			lb.visible = show


func _city_rank(cid: int) -> int:
	for c in _cities:
		if c["id"] == cid:
			return int(c["rank"])
	return 2


# ── 相机控制 ──────────────────────────────────────────
func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.pressed:
			if mb.button_index == MOUSE_BUTTON_WHEEL_UP:
				_dist = clampf(_dist * 0.85, 70.0, 2200.0)
				_update_cam()
			elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
				_dist = clampf(_dist * 1.18, 70.0, 2200.0)
				_update_cam()
			elif mb.button_index == MOUSE_BUTTON_LEFT:
				_drag_btn = MOUSE_BUTTON_LEFT
				_drag_last = mb.position
			elif mb.button_index == MOUSE_BUTTON_RIGHT:
				_drag_btn = MOUSE_BUTTON_RIGHT
				_drag_last = mb.position
			elif mb.button_index == MOUSE_BUTTON_MIDDLE:
				_drag_btn = MOUSE_BUTTON_MIDDLE
				_drag_last = mb.position
		else:
			if mb.button_index == MOUSE_BUTTON_LEFT and _drag_btn == MOUSE_BUTTON_LEFT:
				# 点击（非拖拽）→ 拾取城池
				if _drag_last.distance_to(mb.position) < 6.0:
					_pick_city(mb.position)
			_drag_btn = -1
	elif event is InputEventMouseMotion:
		var mm := event as InputEventMouseMotion
		if _drag_btn == MOUSE_BUTTON_RIGHT:
			_yaw -= mm.relative.x * 0.005
			_pitch = clampf(_pitch + mm.relative.y * 0.005, 0.25, 1.35)
			_update_cam()
		elif _drag_btn == MOUSE_BUTTON_MIDDLE:
			_pan_camera(mm.relative)
		_drag_last = mm.position


func _pan_camera(rel: Vector2) -> void:
	var fwd := (_target - _cam.global_position).normalized()
	var right := fwd.cross(Vector3.UP).normalized()
	var up := right.cross(fwd).normalized()
	var k := _dist * 0.0012
	_target += (-right * rel.x + up * rel.y) * k
	_update_cam()


func _update_cam() -> void:
	var cp := _target + Vector3(
		sin(_yaw) * cos(_pitch), sin(_pitch), cos(_yaw) * cos(_pitch)) * _dist
	_cam.global_position = cp
	_cam.look_at(_target, Vector3.UP)


## 屏幕点 → 射线与 y=0 平面交点（粗略地形拾取）
func _pick_city(sp: Vector2) -> void:
	var origin := _cam.project_ray_origin(sp)
	var dir := _cam.project_ray_normal(sp)
	if absf(dir.y) < 1e-5:
		return
	var t := -origin.y / dir.y
	if t < 0.0:
		return
	var hit := origin + dir * t
	var best_id := -1
	var best_d := 1e9
	for cid in _city_pos2:
		var p3v: Vector3 = (_city_node[cid] as Node3D).global_position
		var d := Vector2(p3v.x - hit.x, p3v.z - hit.z).length()
		if d < _CLICK_R and d < best_d:
			best_d = d
			best_id = cid
	if best_id >= 0:
		_start_move(best_id)


# ── 寻路 + 移动 ───────────────────────────────────────
func _start_move(target_id: int) -> void:
	var start := 0  # 玩家当前城 id（简化：从初始城开始；后续可加"最近城"）
	var path := _find_path(start, target_id)
	if path.size() < 2:
		return
	var route: Array[Vector3] = []
	for k in range(path.size() - 1):
		var a: int = path[k]
		var b: int = path[k + 1]
		var seg := _road_points(a, b)
		if seg.is_empty():
			route.append(_city_node[b].global_position)
			continue
		for p2 in seg:
			route.append(WorldItem3D.to3(p2) + Vector3(0, 1.0, 0))
	_route = route
	_route_i = 0
	_moving = true


func _road_points(a: int, b: int) -> PackedVector2Array:
	for r in _roads:
		if r.get("kind", "") != "branch":
			continue
		if (int(r["a"]) == a and int(r["b"]) == b) or (int(r["a"]) == b and int(r["b"]) == a):
			return r["points"]
	return PackedVector2Array()


func _find_path(from_id: int, to_id: int) -> Array:
	var dist: Dictionary = {from_id: 0.0}
	var prev: Dictionary = {}
	var done := {}
	var cur := from_id
	while cur != to_id:
		done[cur] = true
		var best := -1
		var best_d := 1e18
		for nb in _adj.get(cur, []):
			var nid: int = nb[0]
			if done.has(nid):
				continue
			var nd: float = dist.get(cur, 1e9) + 1.0
			if nd < dist.get(nid, 1e18):
				dist[nid] = nd
				prev[nid] = cur
			if dist[nid] < best_d:
				best_d = dist[nid]
				best = nid
		if best < 0:
			return [from_id]
		cur = best
	var path: Array = [to_id]
	var v := to_id
	while prev.has(v):
		v = prev[v]
		path.append(v)
	path.reverse()
	return path


func _process(delta: float) -> void:
	if _moving and _route_i < _route.size():
		var cur := _player.global_position
		var target_p: Vector3 = _route[_route_i]
		var step := _SPEED * delta
		if cur.distance_to(target_p) <= step:
			_player.global_position = target_p
			_route_i += 1
			if _route_i >= _route.size():
				_moving = false
		else:
			var dirv := (target_p - cur).normalized()
			_player.global_position = cur + dirv * step
	_process_city_labels()


func _set_player_pos(cid: int) -> void:
	var p2: Vector2 = _city_pos2.get(cid, Vector2(4301, 58))
	_player.global_position = WorldItem3D.to3(p2) + Vector3(0, 1.6, 0)
