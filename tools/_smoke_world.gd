extends SceneTree
## 大地图交互冒烟：加载 world_screen → 模拟点击移动（自动移动）→ 验证时间推进 →
## 挪到港町验证坐船 → 打印 HUD 状态。纯 headless 不可渲染，这里验证逻辑链路。

var _frame := 0
var _ws: Node = null
var _phase := 0

func _init() -> void:
	process_frame.connect(_tick)

var _gs: Node = null
var _gd: Node = null

func _tick() -> void:
	_frame += 1
	if _frame == 1:
		_gs = root.get_node("/root/GameState")
		_gd = root.get_node("/root/GameData")
		var scene: PackedScene = load("res://scenes/screens/world_screen.tscn")
		_ws = scene.instantiate()
		root.add_child(_ws)
		return
	if _frame < 30:
		return
	match _phase:
		0:
			# 主角初始在三户（城0）。点击自动移动到江户（城33 坐标）
			var jp: Vector2 = _gd.get_castle_pos(33)
			_ws._move_target = jp
			print("PHASE0 目标=江户 ", jp, " 起点=", _gs.player_map_pos, " 日期=", _gs.year, "/", _gs.month, "/", _gs.day)
			_phase = 1
		1:
			if _ws._move_target == Vector2.INF:
				print("PHASE1 到达！位置=", _gs.player_map_pos, " 日期=", _gs.year, "/", _gs.month, "/", _gs.day, " 体力=", int(_gs.get_status().get("stamina", -1)))
				# 到达江户附近 → 最近城应为 33 或邻近
				print("  nearest=", _gs.nearest_castle(), " (期望江户 33 或邻近)")
				# 挪到港町 124（大坂）旁，验证坐船菜单与乘船
				_gs.player_map_pos = _gd.get_castle_pos(124) + Vector2(0.5, 0)
				_ws._update_nearest()
				print("  nearest(大坂旁)=", _ws._nearest_id, " 是港=", _gd.is_port_city(_ws._nearest_id))
				_ws._toggle_sea_menu()
				print("  坐船菜单=", _ws._sea_menu)
				_phase = 2
		2:
			if not _ws._sea_menu.is_empty() and _ws._sea_menu.size() > 0:
				var before := [_gs.year, _gs.month, _gs.day]
				var res: Dictionary = _gs.travel_by_sea(160)
				print("PHASE2 乘船124→160 res=", res, " 日期 ", before, "→", [_gs.year, _gs.month, _gs.day], " 体力=", int(_gs.get_status().get("stamina", -1)))
				print("  到达=", _gs.player_map_pos, " 最近城=", _gs.nearest_castle(), " (期望160)")
			_phase = 3
		3:
			print("SMOKE DONE")
			quit(0)
