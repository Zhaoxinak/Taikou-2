extends SceneTree
## 世界地图截图工具：加载 world_screen 场景，等数据载入后截图保存 PNG
## 用法：Godot --path . --script res://tools/_shot_world.gd

var _frame := 0

func _init() -> void:
	process_frame.connect(_tick)

func _tick() -> void:
	_frame += 1
	if _frame == 1:
		var scene: PackedScene = load("res://scenes/screens/world_screen.tscn")
		root.add_child(scene.instantiate())
		return
	if _frame < 30:
		return
	var img := root.get_viewport().get_texture().get_image()
	img.save_png("user://world_shot.png")
	print("SHOT SAVED: ", ProjectSettings.globalize_path("user://world_shot.png"))
	quit(0)
