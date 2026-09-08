# battle_screen.gd — 合战场景逻辑（HD-1 地形 + HD-2 单位 sprite）
#
# 挂到 scenes/screens/battle_screen.tscn（Node3D 根，含 Camera3D + DirectionalLight3D）。
# _ready 时：用 Terrain3DBuilder 把第 battle_id 战的 19×40 地形变成 3D 网格（HD-1），
# 再用 UnitSprite 在部署图每个左右军格上摆一个 billboard 像素 sprite（HD-2，占位图，HD-4 就位自动换真图）。
#
# 数据：data/battles.json（terrain 19×40，deploy 19×40 ASCII：左军 {/,1,7,9} / 右军 {+,-,3,5}）。

extends Node3D

const Terrain3DBuilder = preload("res://src/battle/Terrain3DBuilder.gd")
const UnitSprite = preload("res://src/render/UnitSprite.gd")
const AssetLoader = preload("res://src/render/asset_loader.gd")

const LEFT_ARMY_CHARS := ["/", "1", "7", "9"]
const RIGHT_ARMY_CHARS := ["+", "-", "3", "5"]

@export var battle_id: int = 0
@export var unit_pixel_size: float = 0.02

var _battles: Array = []


func _ready() -> void:
	var path := "res://data/battles.json"
	if not FileAccess.file_exists(path):
		push_error("[BattleScreen] 缺少 %s（先运行 scripts/export_for_godot.py）" % path)
		return
	_battles = JSON.parse_string(FileAccess.get_file_as_string(path))
	if _battles == null or _battles.size() == 0:
		push_error("[BattleScreen] battles.json 解析失败")
		return
	if battle_id < 0 or battle_id >= _battles.size():
		push_error("[BattleScreen] battle_id 越界: %d" % battle_id)
		return
	_build_battle(battle_id)


func _build_battle(bid: int) -> void:
	var b: Dictionary = _battles[bid]

	# —— HD-1：3D 地形 ——
	var terrain_node := Terrain3DBuilder.build_from_battle(_battles, bid)
	add_child(terrain_node)

	# —— HD-2：单位 sprite（billboard + NEAREST，占位图回退）——
	var units_root := Node3D.new()
	units_root.name = "Units"
	add_child(units_root)

	var terrain: Array = b.get("terrain", [])
	var deploy: Array = b.get("deploy", [])
	var tex: Texture2D = AssetLoader.load_unit_texture(-1)
	var y := 0
	for row in deploy:
		var x := 0
		for ch in row:
			var side := -1
			if ch in LEFT_ARMY_CHARS:
				side = 0
			elif ch in RIGHT_ARMY_CHARS:
				side = 1
			if side >= 0:
				var cell: Variant = terrain[y][x] if (y < terrain.size() and x < terrain[y].size()) else null
				var h: float = Terrain3DBuilder.cell_height(cell)
				var pos: Vector3 = UnitSprite.grid_to_world(x, y, h + 0.5)
				var tint: Color = Color(1.0, 0.82, 0.82, 1.0) if side == 1 else Color(0.85, 1.0, 0.85, 1.0)
				var s: Sprite3D = UnitSprite.make(tex, pos, unit_pixel_size, tint)
				units_root.add_child(s)
			x += 1
		y += 1

	print("[BattleScreen] 战图 %d 已构建：地形网格 + %d 个单位 sprite（占位图，HD-4 就位自动替换）" % [bid, units_root.get_child_count()])
