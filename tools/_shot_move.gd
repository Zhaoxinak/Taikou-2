extends SceneTree
## 平滑移动验证截图：开局后让玩家自动走向最近城方向，移动中段截图，
## 检查小人是否位于格子中间（而非跳格突变）
## 用法：Godot --path . --script res://tools/_shot_move.gd

var _frame := 0
var _ws: Node = null
var _moved := false
var _gs: Node = null

func _init() -> void:
	process_frame.connect(_tick)

func _tick() -> void:
	_frame += 1
	if _frame == 1:
		_gs = root.get_node("GameState")
		var scene: PackedScene = load("res://scenes/screens/world_screen.tscn")
		_ws = scene.instantiate()
		root.add_child(_ws)
		return
	if _frame < 30:
		return
	# 触发一次向最近城移动（自动寻路开始行走）
	if not _moved:
		_moved = true
		_ws.set("_move_target", Vector2(_gs.player_map_pos.x - 3.0, _gs.player_map_pos.y + 2.0))
	# 移动中段截图（约 0.4s 后，应处于第一格→第二格之间）
	for f in [38, 42, 46, 50, 54, 60]:
		if _frame == f:
			print("F", f, " pos=", _gs.player_map_pos, " draw=", _ws.get("_draw_pos"), " prog=", _ws.get("_move_prog"), " tgt=", _ws.get("_move_target"))
	if _frame == 90:
		print("F90 pos=", _gs.player_map_pos, " draw=", _ws.get("_draw_pos"), " prog=", _ws.get("_move_prog"), " tgt=", _ws.get("_move_target"), " from=", _ws.get("_move_from"), " to=", _ws.get("_move_to"))
	if _frame == 120:
		var img := root.get_viewport().get_texture().get_image()
		img.save_png("user://move_end.png")
		print("END pos=", _gs.player_map_pos, " draw=", _ws.get("_draw_pos"), " prog=", _ws.get("_move_prog"), " tgt=", _ws.get("_move_target"))
		quit(0)
