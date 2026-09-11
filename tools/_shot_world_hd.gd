extends SceneTree
## tools/_shot_world_hd.gd — 大地图 HD-2D 移动序列验证（无头，横屏 1920×1080）
## 玩家从酒田港(30.3,15.3) 沿陆路向东南内陆(29.7,16.1) 行走，途经鮭延/新发田方向

var _frame := 0
var _inst: Node = null
var _saved := 0

func _init() -> void:
	process_frame.connect(_tick)

func _tick() -> void:
	_frame += 1
	if _frame == 1:
		root.size = Vector2i(1920, 1080)
		await process_frame
		root.get_node("/root/GameState").month = 4
		root.get_node("/root/GameState").day = 15
		var packed: PackedScene = load("res://scenes/screens/world_screen.tscn")
		_inst = packed.instantiate()
		root.add_child(_inst)
		return
	if _frame == 20:
		# 初始在酒田港附近，等相机稳定
		root.get_node("/root/GameState").player_map_pos = Vector2(30.3, 15.3)
		return
	if _frame == 30:
		_snap("m1")
		# 开始向东南内陆行走
		_inst._begin_move(Vector2(29.7, 16.1))
		return
	if _frame >= 30 and _frame % 12 == 0 and _saved < 4:
		_saved += 1
		_snap("m%d" % (_saved + 1))
	if _frame == 120:
		quit(0)

func _snap(tag: String) -> void:
	await process_frame
	await process_frame
	var img := root.get_viewport().get_texture().get_image()
	img.save_png("user://hd_w_%s.png" % tag)
	print("[shot] 保存 hd_w_%s.png" % tag)
