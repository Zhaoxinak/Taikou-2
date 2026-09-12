# _test_scene_load.gd — 场景化重构验证：全部 .tscn 可加载实例化，控件节点可数、可归类
# 运行：Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_scene_load.gd
extends SceneTree

var _fails := 0

func check(cond: bool, msg: String) -> void:
	if cond:
		print("[ok] " + msg)
	else:
		_fails += 1
		push_error("[FAIL] " + msg)


func _init() -> void:
	var scenes := {
		"res://scenes/main.tscn": "标题",
		"res://scenes/screens/protagonist_select.tscn": "主角选择",
		"res://scenes/screens/status_screen.tscn": "状态",
		"res://scenes/screens/command_screen.tscn": "主命",
		"res://scenes/screens/castle_town.tscn": "城下町",
		"res://scenes/screens/diplomacy_screen.tscn": "外交一览",
		"res://scenes/screens/battle_screen.tscn": "合战",
		"res://scenes/screens/world_screen.tscn": "大地图",
	}
	for path in scenes:
		var ps: PackedScene = load(path)
		check(ps != null, "场景可加载 %s (%s)" % [scenes[path], path])
		if ps == null:
			continue
		var inst := ps.instantiate()
		check(inst != null, "场景可实例化 %s" % scenes[path])
		if inst == null:
			continue
		root.add_child(inst)
		# 等待一帧让 @onready / _ready 跑完
		await process_frame
		# 统计该场景下的自绘控件节点（UiButton/UiLabel/UiPanel 通过脚本路径判定）
		var btn := 0
		var lbl := 0
		var pnl := 0
		for c in _all_nodes(inst):
			var s: Script = c.get_script()
			if s == null:
				continue
			var p := s.resource_path
			if p.ends_with("UiButton.gd"):
				btn += 1
			elif p.ends_with("UiLabel.gd"):
				lbl += 1
			elif p.ends_with("UiPanel.gd"):
				pnl += 1
		print("  %s: UiButton %d / UiLabel %d / UiPanel %d" % [scenes[path], btn, lbl, pnl])
		check(btn + lbl + pnl > 0, "%s 含自绘 UI 节点（编辑器可见）" % scenes[path])
		inst.queue_free()
		await process_frame

	print("")
	if _fails == 0:
		print("[SCENE LOAD PASS] 全部场景加载正常 ✅")
		quit(0)
	else:
		push_error("[SCENE LOAD FAIL] %d 项失败 ❌" % _fails)
		quit(1)


func _all_nodes(n: Node) -> Array:
	var out: Array = [n]
	for c in n.get_children():
		out.append_array(_all_nodes(c))
	return out
