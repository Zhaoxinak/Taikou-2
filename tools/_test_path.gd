extends SceneTree
## 验证 BFS 陆地寻路：三户(东北海岸) → 内陆城，检查路径所有格均为陆地

var _done := false

func _init() -> void:
	process_frame.connect(_tick)

func _tick() -> void:
	if _done:
		return
	_done = true
	var WorldMapRef = load("res://src/core/world_map.gd")
	var WorldTerrain = load("res://src/core/world_terrain.gd")
	# 需要 GameData autoload 载入
	var gd: Object = root.get_node("GameData")
	var ms: Vector2 = gd.get_map_size()
	var checks := [
		["三户→江户", Vector2(44.24, 3.92), gd.get_castle_pos(12)],
		["三户→二条", Vector2(44.24, 3.92), gd.get_castle_pos(82)],
		["大阪→鹿儿岛", gd.get_castle_pos(124), gd.get_castle_pos(195)],
		["海上目标吸附", Vector2(20.0, 2.0), Vector2(20.0, 2.0)],
	]
	for ck in checks:
		var from: Vector2 = ck[1]
		var to: Vector2 = ck[2]
		var path: PackedVector2Array = WorldMapRef.find_path(from, to, ms.x, ms.y, WorldTerrain.type_at)
		var bad := 0
		var sea_cells := 0
		for i in range(path.size()):
			var p: Vector2 = path[i]
			var gx := clampi(int(floor(p.x)), 0, int(ms.x) - 1)
			var gy := clampi(int(floor(p.y)), 0, int(ms.y) - 1)
			var t: int = WorldTerrain.type_at(int(gx * 256.0 / 48.0), int(gy * 192.0 / 36.0))
			if t == 0:
				sea_cells += 1
			if i > 0 and path[i].distance_to(path[i - 1]) > 1.05:
				bad += 1
		print("%s: path=%d 海格=%d 超步长=%d" % [ck[0], path.size(), sea_cells, bad])
	quit(0)
