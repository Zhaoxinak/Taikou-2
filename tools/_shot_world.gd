# _shot_world.gd — 渲染大地图截图（验收立体效果用，非交付物）
extends SceneTree

func _init() -> void:
	var ps: PackedScene = load("res://scenes/screens/world_screen.tscn")
	if ps == null:
		print("load fail")
		quit(1)
		return
	var w = ps.instantiate()
	root.add_child(w)
	await process_frame
	await process_frame
	await process_frame
	root.size = Vector2(1600, 1500)
	await process_frame
	var cam = w.get_node("Camera2D")
	cam.zoom = Vector2(2.0, 2.0)
	cam.position = Vector2(2624, 2326)  # 稻叶山（rank0 巨城）+ 周围城下町
	for i in range(10):
		await process_frame
	var img = root.get_viewport().get_texture().get_image()
	var ok = img.save_png("F:/Games/Taikou 2/tmp_world_preview.png")
	print("saved=", ok)
	cam.position = Vector2(3710, 2218)  # 江户（rank5 村庄）
	await process_frame
	await process_frame
	var img2 = root.get_viewport().get_texture().get_image()
	var ok2 = img2.save_png("F:/Games/Taikou 2/tmp_world_zoom1.png")
	print("saved2=", ok2)
	quit(0)
