extends SceneTree
var _frame := 0
var _ws: Node = null
func _init() -> void:
	process_frame.connect(_tick)
func _tick() -> void:
	_frame += 1
	if _frame == 1:
		var scene: PackedScene = load("res://scenes/screens/world_screen.tscn")
		_ws = scene.instantiate()
		root.add_child(_ws)
		return
	if _frame == 8:
		var st: Node = root.get_node("/root/GameState")
		var gd: Node = root.get_node("/root/GameData")
		st.player_map_pos = gd.get_castle_pos(47)
		print("TELEPORT pos=", st.player_map_pos, " cam=", _ws._cam)
		return
	if _frame == 45:
		print("SHOT cam=", _ws._cam, " target=", _ws._cam_target)
		var img := root.get_viewport().get_texture().get_image()
		img.save_png("user://cam_follow.png")
		quit(0)
