extends SceneTree
## 天气效果截图：临时把天气设为 雨/雪 后截大地图（并刷新 HUD 显示）
## 用法：Godot --path . --script res://tools/_shot_weather.gd -- rain|snow
## 截图存 user://weather_shot_<mode>.png

var _frame := 0
var _mode := "rain"
var _ws: Node = null

func _init() -> void:
	for a in OS.get_cmdline_user_args():
		_mode = str(a)
	process_frame.connect(_tick)

func _tick() -> void:
	_frame += 1
	if _frame == 1:
		var scene: PackedScene = load("res://scenes/screens/world_screen.tscn")
		_ws = scene.instantiate()
		root.add_child(_ws)
		return
	if _frame == 3:
		var st: Node = root.get_node("/root/GameState")
		st.weather.set_weather(3 if _mode == "snow" else 2)
		if _ws != null and _ws.has_method("_refresh_hud"):
			_ws.call("_refresh_hud")
		return
	if _frame < 30:
		return
	var img := root.get_viewport().get_texture().get_image()
	img.save_png("user://weather_shot_%s.png" % _mode)
	print("WEATHER SHOT: ", _mode)
	quit(0)
