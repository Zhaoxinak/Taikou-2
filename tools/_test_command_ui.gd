extends SceneTree
## 主命执行画面（command_screen）无头校验 —— 填补「主命执行 仅占位，待实现」缺口
##
## 覆盖：
##   1) 12 主命按钮齐备 + 谋略(11) 因无静态模型置灰（不做假）
##   2) 内政类主命（开垦 4）点击 → 推进 1 月 + 结果区显示精确 delta
##   3) 外交类主命（进贡 7）→ 目标国选择模式；自国按钮禁用；选国后执行
##   4) 被拒（如 bad_target / dispatch_blocked）不消耗月份
##   5) 状态画面新增「执行主命」入口按钮

const UiButton = preload("res://src/ui/UiButton.gd")
const UiLabel = preload("res://src/ui/UiLabel.gd")

var _fails: int = 0


func check(cond: bool, msg: String) -> void:
	if cond:
		print("[ok] ", msg)
	else:
		_fails += 1
		push_error("[FAIL] " + msg)


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)


func _run() -> void:
	var t0 := Time.get_ticks_msec()
	var gs := root.get_node_or_null("GameState")
	if gs == null:
		check(false, "GameState autoload 缺失")
		quit(1)
		return
	gs.start_new_game(13)   # 织田信长

	var sc: Control = (load("res://scenes/screens/command_screen.tscn") as PackedScene).instantiate()
	root.add_child(sc)
	await process_frame

	# —— 1) 12 主命按钮 ——
	check(sc._cmd_buttons.size() == 12, "12 主命按钮 (got %d)" % sc._cmd_buttons.size())
	var names: Array = gs.COMMAND_NAMES
	check(str(sc._cmd_buttons[0].text) == names[0], "按钮 0 = %s" % names[0])
	check(str(sc._cmd_buttons[6].text) == "筑城", "按钮 6 = 筑城")
	check(not bool(sc._cmd_buttons[11].enabled),
		"谋略(11) 因无静态关系模型置灰（不做假）")
	check(bool(sc._cmd_buttons[4].enabled), "开垦(4) 可点击")

	# —— 2) 内政类：开垦 ——
	var st0: Dictionary = gs.get_status()
	var m0 := int(st0["month"])
	var y0 := int(st0["year"])
	sc._on_command(4)
	var st1: Dictionary = gs.get_status()
	check(int(st1["month"]) == (m0 % 12) + 1 or int(st1["year"]) != y0,
		"开垦推进 1 月 (%d/%d → %d/%d)" % [y0, m0, int(st1["year"]), int(st1["month"])])
	var msg1 := str(sc._msg.text)
	check(msg1.contains("开垦农田") and msg1.contains("成功"), "结果区显示「开垦农田 成功」(%s)" % msg1.left(40))
	check(msg1.contains("+"), "结果区含 delta 数值 (%s)" % msg1.left(60))

	# —— 3) 谋略：占位且不耗时 ——
	var st2: Dictionary = gs.get_status()
	sc._on_command(11)
	var st3: Dictionary = gs.get_status()
	check(int(st3["month"]) == int(st2["month"]), "谋略被拒 ⇒ 不消耗月份")
	check(str(sc._msg.text).contains("未能执行"), "谋略显示未能执行 (%s)" % str(sc._msg.text).left(40))

	# —— 4) 外交类：进贡需选目标国 ——
	sc._on_command(7)
	check(bool(sc._prov_panel.visible), "进贡(7) 打开目标国选择器")
	check(sc._prov_buttons.size() == 49, "49 个目标国按钮 (got %d)" % sc._prov_buttons.size())
	var my: int = gs.protagonist_province()
	check(my >= 0, "自国省 id 可解析 (got %d)" % my)
	check(not bool(sc._prov_buttons[my].enabled), "自国按钮禁用（不可对自己外交）")

	# 选一个非自国 → 执行（成功或被拒都不应崩，且结果区有反馈）
	var other: int = 0 if my != 0 else 1
	var st4: Dictionary = gs.get_status()
	sc._on_pick_province(other)
	check(not bool(sc._prov_panel.visible), "选国后选择器关闭")
	var msg2 := str(sc._msg.text)
	check(msg2.contains("进贡"), "结果区反馈进贡 (%s)" % msg2.left(50))
	var st5: Dictionary = gs.get_status()
	var advanced: bool = int(st5["month"]) != int(st4["month"])
	if msg2.contains("未能执行"):
		check(not advanced, "进贡被拒 ⇒ 不消耗月份")
	else:
		check(advanced, "进贡成功 ⇒ 消耗 1 月")
		check(msg2.contains("目标国"), "结果区含目标国外交/主从变化")

	# —— 5) 状态画面入口 ——
	var ssc: Control = (load("res://scenes/screens/status_screen.tscn") as PackedScene).instantiate()
	root.add_child(ssc)
	await process_frame
	var found: Array = [false]   # ⚠️ GDScript 基本类型按值传参，须用数组回传
	_walk(ssc, found)
	check(bool(found[0]), "状态画面含「执行主命」入口按钮")

	_finish(t0)


func _walk(n: Node, found: Array) -> void:
	for c in n.get_children():
		var t: String = str(c.get("text"))
		if t.contains("执行主命"):
			found[0] = true
		_walk(c, found)


func _finish(t0: int) -> void:
	print("")
	if _fails > 0:
		push_error("[COMMAND UI FAIL] %d 项断言失败" % _fails)
		quit(1)
	print("[ok] 主命执行画面校验通过（用时 %.0f ms）" % [float(Time.get_ticks_msec() - t0)])
	quit(0)
