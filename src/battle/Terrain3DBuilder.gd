# Terrain3DBuilder.gd — 把 HJMAPDAT 的 19×40 地形网格变成 3D 网格（HD-1 里程碑）
#
# 数据源：data/battles.json（由 scripts/export_for_godot.py 从 HJMAPDAT.DAT 导出）
#   结构：battles[battle_id]["terrain"] = 19 行 × 40 列，每格 {code, type, mod}
#
# 地形类型（实测 11 种 + 1 未知）
#   平地 55 / 荒地 48 / 草地 81 / 森林 98 / 河流 197 / 城 87 /
#   空 148 / ?F 19 / 阵 18 / 山地 6 / 桥 3        （第 0 战统计）
#
# 用法
# ----
#   var battles := JSON.parse_string(FileAccess.get_file_as_string("res://../data/battles.json"))
#   var terrain := Terrain3DBuilder.build(battles[0]["terrain"])
#   add_child(terrain)

class_name Terrain3DBuilder
extends RefCounted

const GRID_W := 40          # 列数
const GRID_H := 19          # 行数
const TILE_SIZE := 1.0      # 每格世界单位

# 地形 → 高度（HD-2D 的体积感来源）
const HEIGHT_BY_TYPE := {
	"平地": 0.00,
	"荒地": 0.06,
	"草地": 0.02,
	"森林": 0.35,
	"河流": -0.18,
	"城":   0.85,
	"空":  -0.35,
	"?F":   0.00,   # 未知地形，按平地处理
	"阵":   0.12,
	"山地": 1.30,
	"桥":   0.02,
}

# 地形 → 顶点色（HD-2D 浓郁色调）
const COLOR_BY_TYPE := {
	"平地": Color(0.42, 0.52, 0.28),
	"荒地": Color(0.56, 0.48, 0.30),
	"草地": Color(0.32, 0.58, 0.26),
	"森林": Color(0.16, 0.38, 0.16),
	"河流": Color(0.18, 0.38, 0.62),
	"城":   Color(0.58, 0.52, 0.44),
	"空":   Color(0.10, 0.12, 0.18),
	"?F":   Color(0.45, 0.45, 0.45),
	"阵":   Color(0.62, 0.28, 0.22),
	"山地": Color(0.44, 0.40, 0.34),
	"桥":   Color(0.50, 0.38, 0.24),
}

const DEFAULT_HEIGHT := 0.0
const DEFAULT_COLOR  := Color(0.45, 0.45, 0.45)


# 公开：查询单格地形高度（供单位 sprite 摆放复用）
static func cell_height(cell: Variant) -> float:
	if cell is Dictionary:
		return HEIGHT_BY_TYPE.get(cell.get("type", ""), DEFAULT_HEIGHT)
	return DEFAULT_HEIGHT


# 构建 3D 地形
static func build(terrain_rows: Array) -> Node3D:
	var root := Node3D.new()
	root.name = "BattleTerrain"

	var rows: int = terrain_rows.size()
	if rows == 0:
		push_warning("[Terrain3DBuilder] 空地形数据")
		return root
	var cols: int = (terrain_rows[0] as Array).size()

	# 预计算高度图（侧壁需要查询邻居）
	var heights: Array = []
	for z in rows:
		var row: Array = []
		for x in cols:
			row.append(_height_at(terrain_rows, x, z))
		heights.append(row)

	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	for z in rows:
		for x in cols:
			var h: float = heights[z][x]
			var c: Color = _color_at(terrain_rows, x, z)
			_add_top_face(st, x, z, h, c)
			_add_side_walls(st, x, z, h, c, heights, rows, cols)

	st.generate_normals()

	var mi := MeshInstance3D.new()
	mi.name = "TerrainMesh"
	mi.mesh = st.commit()
	mi.material_override = _terrain_material()
	mi.cast_shadow  = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	mi.gi_mode      = GeometryInstance3D.GI_MODE_STATIC
	root.add_child(mi)
	return root


# 查询指定格高度（安全边界）
static func _height_at(terrain_rows: Array, x: int, z: int) -> float:
	if z < 0 or z >= terrain_rows.size():
		return DEFAULT_HEIGHT
	var row := terrain_rows[z] as Array
	if x < 0 or x >= row.size():
		return DEFAULT_HEIGHT
	var cell: Dictionary = row[x]
	return HEIGHT_BY_TYPE.get(cell.get("type", ""), DEFAULT_HEIGHT)


static func _color_at(terrain_rows: Array, x: int, z: int) -> Color:
	if z < 0 or z >= terrain_rows.size():
		return DEFAULT_COLOR
	var row := terrain_rows[z] as Array
	if x < 0 or x >= row.size():
		return DEFAULT_COLOR
	var cell: Dictionary = row[x]
	return COLOR_BY_TYPE.get(cell.get("type", ""), DEFAULT_COLOR)


# 顶面（水平四边形，法线朝上）
static func _add_top_face(st: SurfaceTool, x: int, z: int, h: float, c: Color) -> void:
	var x0 := float(x) * TILE_SIZE
	var z0 := float(z) * TILE_SIZE
	var x1 := x0 + TILE_SIZE
	var z1 := z0 + TILE_SIZE

	st.set_normal(Vector3.UP)
	st.set_color(c)

	st.set_uv(Vector2(0, 0)); st.add_vertex(Vector3(x0, h, z0))
	st.set_uv(Vector2(1, 0)); st.add_vertex(Vector3(x1, h, z0))
	st.set_uv(Vector2(1, 1)); st.add_vertex(Vector3(x1, h, z1))

	st.set_uv(Vector2(0, 0)); st.add_vertex(Vector3(x0, h, z0))
	st.set_uv(Vector2(1, 1)); st.add_vertex(Vector3(x1, h, z1))
	st.set_uv(Vector2(0, 1)); st.add_vertex(Vector3(x0, h, z1))


# 侧壁：只画朝东(+x) 与朝南(+z)，避免相邻格重复绘制
static func _add_side_walls(st: SurfaceTool, x: int, z: int, h: float, c: Color,
		heights: Array, rows: int, cols: int) -> void:
	var x0 := float(x) * TILE_SIZE
	var z0 := float(z) * TILE_SIZE
	var x1 := x0 + TILE_SIZE
	var z1 := z0 + TILE_SIZE

	# 暗化侧壁（模拟阴影，增强 HD-2D 体积感）
	var side_c := c * 0.65

	# 东邻（+x）
	if x + 1 < cols:
		var hn: float = heights[z][x + 1]
		if hn < h:
			_add_quad_x(st, x1, z0, z1, hn, h, side_c)
	elif h > 0.0:
		_add_quad_x(st, x1, z0, z1, 0.0, h, side_c)

	# 南邻（+z）
	if z + 1 < rows:
		var hs: float = heights[z + 1][x]
		if hs < h:
			_add_quad_z(st, x0, x1, z1, hs, h, side_c)
	elif h > 0.0:
		_add_quad_z(st, x0, x1, z1, 0.0, h, side_c)


# 垂直于 X 轴的墙面（位于 x 平面）
static func _add_quad_x(st: SurfaceTool, x: float, z0: float, z1: float,
		h_low: float, h_high: float, c: Color) -> void:
	st.set_normal(Vector3(1, 0, 0))
	st.set_color(c)
	st.set_uv(Vector2(0, h_low));  st.add_vertex(Vector3(x, h_low,  z0))
	st.set_uv(Vector2(1, h_low));  st.add_vertex(Vector3(x, h_low,  z1))
	st.set_uv(Vector2(1, h_high)); st.add_vertex(Vector3(x, h_high, z1))

	st.set_uv(Vector2(0, h_low));  st.add_vertex(Vector3(x, h_low,  z0))
	st.set_uv(Vector2(1, h_high)); st.add_vertex(Vector3(x, h_high, z1))
	st.set_uv(Vector2(0, h_high)); st.add_vertex(Vector3(x, h_high, z0))


# 垂直于 Z 轴的墙面（位于 z 平面）
static func _add_quad_z(st: SurfaceTool, x0: float, x1: float, z: float,
		h_low: float, h_high: float, c: Color) -> void:
	st.set_normal(Vector3(0, 0, 1))
	st.set_color(c)
	st.set_uv(Vector2(0, h_low));  st.add_vertex(Vector3(x0, h_low,  z))
	st.set_uv(Vector2(1, h_low));  st.add_vertex(Vector3(x1, h_low,  z))
	st.set_uv(Vector2(1, h_high)); st.add_vertex(Vector3(x1, h_high, z))

	st.set_uv(Vector2(0, h_low));  st.add_vertex(Vector3(x0, h_low,  z))
	st.set_uv(Vector2(1, h_high)); st.add_vertex(Vector3(x1, h_high, z))
	st.set_uv(Vector2(0, h_high)); st.add_vertex(Vector3(x0, h_high, z))


# 地形材质（顶点色作为 albedo）
static func _terrain_material() -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.vertex_color_use_as_albedo = true
	m.roughness = 0.88
	m.metallic  = 0.0
	m.cull_mode = BaseMaterial3D.CULL_DISABLED   # 双面：防止侧壁在低角度消失
	return m


# 便捷：从 battles.json 的第 n 战构建
static func build_from_battle(battles: Array, battle_id: int) -> Node3D:
	if battle_id < 0 or battle_id >= battles.size():
		push_error("[Terrain3DBuilder] battle_id 越界: %d" % battle_id)
		return Node3D.new()
	return build(battles[battle_id].get("terrain", []))
