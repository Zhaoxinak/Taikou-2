# _test_battle_scene.gd — 验证 HD-1/HD-2 接入 battle_screen.tscn 能无错构建（extends SceneTree）
#
# 加载 scenes/screens/battle_screen.tscn，实例化并把第 0 战跑 _ready，
# 确认：地形网格 MeshInstance3D 已建、单位 sprite 已摆、无运行时错误。
#
# 运行：Godot_v4.7.1/Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_battle_scene.gd

extends SceneTree

func _initialize() -> void:
	var scene_path := "res://scenes/screens/battle_screen.tscn"
	if not ResourceLoader.exists(scene_path):
		push_error("缺少场景 %s" % scene_path)
		quit(1)
	var scene: PackedScene = load(scene_path)
	var inst := scene.instantiate()
	root.add_child(inst)

	# _ready 已在 add_child 时触发，等待一帧确保完成
	await create_timer(0.1).timeout

	var terrain: Node = inst.get_node_or_null("BattleTerrain")
	var units: Node = inst.get_node_or_null("Units")
	var terrain_ok := terrain != null and terrain.get_child_count() > 0
	var units_ok := units != null and units.get_child_count() > 0
	print("[BattleScene] 地形网格节点: %s (子节点 %d)" % [str(terrain), inst.get_child_count() if terrain else 0])
	if terrain != null:
		for c in terrain.get_children():
			print("   terrain child: %s" % c.name)
	print("[BattleScene] 单位 sprite 数: %d" % (units.get_child_count() if units else 0))

	if not terrain_ok or not units_ok:
		push_error("HD-1/HD-2 接入失败：terrain_ok=%s units_ok=%s" % [terrain_ok, units_ok])
		quit(1)
	print("[ok] HD-1 地形 + HD-2 单位 sprite 接入 battle_screen.tscn 成功（首帧 HD-2D 合战可渲染）")
	quit(0)
