# _test_world_screen.gd — 大地图场景化验证：全元素 item 节点数 / 玩家初始化 / 寻路 / 移动
# 运行：Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_world_screen.gd
extends SceneTree

var _fails := 0

func check(cond: bool, msg: String) -> void:
	if cond:
		print("[ok] " + msg)
	else:
		_fails += 1
		push_error("[FAIL] " + msg)


func _init() -> void:
	var ps: PackedScene = load("res://scenes/screens/world_screen.tscn")
	check(ps != null, "world_screen.tscn 可加载")
	if ps == null:
		quit(1)
		return
	var w = ps.instantiate()
	check(w != null, "world_screen 可实例化")
	root.add_child(w)
	await process_frame
	await process_frame
	if w.get_script() == null:
		push_error("[FAIL] world_screen.gd 脚本未加载（场景挂载失败），中止测试")
		quit(1)
		return

	# —— 元素 item 节点数（编辑器可见、可归类）——
	check(w.get_node_or_null("World/Cities") != null, "Cities 分组存在")
	check(w.get_node_or_null("World/Cities").get_child_count() == 200, "城市 item 200 (got %d)" % w.get_node_or_null("World/Cities").get_child_count())
	check(w.get_node_or_null("World/Land").get_child_count() == 9, "陆地多边形 item 9 (8 陆地+海面, got %d)" % w.get_node_or_null("World/Land").get_child_count())
	check(w.get_node_or_null("World/Rivers").get_child_count() == 20, "河流 item 20 (got %d)" % w.get_node_or_null("World/Rivers").get_child_count())
	check(w.get_node_or_null("World/Mountains/Ranges").get_child_count() == 11, "山系 item 11 (got %d)" % w.get_node_or_null("World/Mountains/Ranges").get_child_count())
	check(w.get_node_or_null("World/Mountains/Peaks").get_child_count() == 19, "山峰 item 19 (got %d)" % w.get_node_or_null("World/Mountains/Peaks").get_child_count())
	check(w.get_node_or_null("World/Roads/Trunk").get_child_count() == 8, "干道 item 8 (got %d)" % w.get_node_or_null("World/Roads/Trunk").get_child_count())
	check(w.get_node_or_null("World/Roads/Branch").get_child_count() >= 290, "支线 item ≥290 (got %d)" % w.get_node_or_null("World/Roads/Branch").get_child_count())
	check(w.get_node_or_null("World/Sights").get_child_count() == 32, "景点 item 32 (got %d)" % w.get_node_or_null("World/Sights").get_child_count())
	check(w.get_node_or_null("World/Provinces").get_child_count() == 49, "国名 item 49 (got %d)" % w.get_node_or_null("World/Provinces").get_child_count())

	# —— 玩家初始化（未开局 → 三户 id0，坐标随投影放大动态断言）——
	var player = w.get_node_or_null("World/Player")
	check(player != null, "玩家节点存在")
	var p0: Vector2 = player.points[0] if player != null and player.points.size() > 0 else Vector2.ZERO
	var home: Vector2 = w._city_pos(0)
	check(p0.distance_to(home) < 5.0, "玩家初始在主角城(三户) (%s ≈ %s)" % [p0, home])

	# —— 寻路：三户(0) → 八户(1)（相邻）——
	w._goto_city(1)
	check(w._path.size() >= 2, "寻路路径非空 (0→1, 长度 %d)" % w._path.size())

	# —— 移动：推进 0.5s，玩家应已离开起点 ——
	var before: Vector2 = player.points[0] if player.points.size() > 0 else Vector2.ZERO
	for i in 60:
		await process_frame
	var after: Vector2 = player.points[0] if player.points.size() > 0 else Vector2.ZERO
	check(after.distance_to(before) > 1.0, "玩家已沿道路移动 (%.1fpx)" % after.distance_to(before))

	# —— UI 层 ——
	check(w.get_node_or_null("UI/BackBtn") != null, "返回按钮预置")
	check(w.get_node_or_null("UI/InfoPanel") != null, "信息面板预置")
	check(w.get_node_or_null("Camera2D") != null, "相机预置")

	print("")
	if _fails == 0:
		print("[WORLD PASS] 大地图全部断言通过 ✅")
		quit(0)
	else:
		push_error("[WORLD FAIL] %d 项断言失败 ❌" % _fails)
		quit(1)
