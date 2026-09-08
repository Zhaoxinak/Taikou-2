# _test_ui_hd5.gd — HD-5 自绘 UI + 多分辨率适配 无头校验（extends SceneTree）
#
# 覆盖：UiTheme 设计空间/缩放比/档位、UiButton 自绘状态机与点击派发、
#       UiPanel 构造、标题画面改用自绘控件后的链路。
# 运行：Godot_v4.7.1/Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_ui_hd5.gd

extends SceneTree

const UiTheme = preload("res://src/ui/UiTheme.gd")
const UiPanel = preload("res://src/ui/UiPanel.gd")
const UiButton = preload("res://src/ui/UiButton.gd")
const UiLabel = preload("res://src/ui/UiLabel.gd")

var _fails: int = 0

func check(cond: bool, msg: String) -> void:
	if cond:
		print("[ok] " + msg)
	else:
		push_error("[FAIL] " + msg)
		_fails += 1

func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)


# —— 1) UiTheme：设计空间与多分辨率缩放 ——
func _test_theme() -> void:
	check(UiTheme.DESIGN == Vector2i(1920, 1080),
		"设计基准 = 1920×1080（与 project.godot viewport 一致）")

	# 缩放比（窗口 / 设计基准）
	check(is_equal_approx(UiTheme.scale_for(Vector2i(1920, 1080)), 1.0),
		"1080p → 缩放 1.000x")
	check(is_equal_approx(UiTheme.scale_for(Vector2i(2560, 1440)), 4.0 / 3.0),
		"2K    → 缩放 1.333x")
	check(is_equal_approx(UiTheme.scale_for(Vector2i(3840, 2160)), 2.0),
		"4K    → 缩放 2.000x")

	# 档位标签
	check(UiTheme.preset_label(Vector2i(1920, 1080)) == "1080p", "档位 1080p")
	check(UiTheme.preset_label(Vector2i(2560, 1440)) == "2K", "档位 2K")
	check(UiTheme.preset_label(Vector2i(3840, 2160)) == "4K", "档位 4K")

	# 字号层级单调（标题 > 小标题 > 正文 > 小字）
	check(UiTheme.FONT_TITLE > UiTheme.FONT_HEAD
		and UiTheme.FONT_HEAD > UiTheme.FONT_BODY
		and UiTheme.FONT_BODY > UiTheme.FONT_SMALL,
		"字号层级单调 (76/44/30/24)")

	# 字体可载入（CJK 必需）
	var f := UiTheme.font()
	check(f != null, "CJK 字体载入成功（NotoSansSC 或引擎回退）")
	check(UiTheme.text_size("织田信长", 30).x > 0, "字体可度量 CJK 文本宽度")
	check(UiTheme.baseline_y("织田信长", 72.0, 30) > 0, "垂直居中基线可计算")


# —— 2) UiButton 自绘状态机 ——
func _test_button_states() -> void:
	check(UiButton.state_bg(true, false, false) == UiTheme.C_BTN_BG, "常态底色")
	check(UiButton.state_bg(true, true, false) == UiTheme.C_BTN_HOVER, "悬停底色")
	check(UiButton.state_bg(true, true, true) == UiTheme.C_BTN_DOWN, "按下底色（优先于悬停）")
	check(UiButton.state_bg(false, true, true) == UiTheme.C_BTN_OFF_BG, "禁用底色（优先于一切）")
	check(UiButton.state_edge(true) == UiTheme.C_PANEL_EDGE, "启用金边")
	check(UiButton.state_edge(false) == UiTheme.C_TEXT_OFF, "禁用灰边")
	check(UiButton.state_text(true) == UiTheme.C_TEXT, "启用文字色")
	check(UiButton.state_text(false) == UiTheme.C_TEXT_OFF, "禁用文字色")


# —— 3) UiButton 点击派发 ——
func _test_button_input() -> void:
	var btn = UiButton.new()
	root.add_child(btn)
	btn.text = "开 始 新 游 戏"
	btn.size = Vector2(UiTheme.BTN_W, UiTheme.BTN_H)

	# ⚠️ GDScript lambda 捕获局部变量是按值传递的 → 必须用引用类型(Array)累加
	var hits: Array = [0]
	btn.pressed.connect(func() -> void: hits[0] += 1)

	var down := InputEventMouseButton.new()
	down.button_index = MOUSE_BUTTON_LEFT
	down.pressed = true
	var up := InputEventMouseButton.new()
	up.button_index = MOUSE_BUTTON_LEFT
	up.pressed = false

	btn._gui_input(down)
	btn._gui_input(up)
	check(hits[0] == 1, "按下+松开 → 触发 1 次 (got %d)" % hits[0])

	# 禁用后不再触发
	btn.enabled = false
	btn._gui_input(down)
	btn._gui_input(up)
	check(hits[0] == 1, "禁用后点击不触发 (got %d)" % hits[0])

	# 仅松开（未在本控件按下）不触发
	btn.enabled = true
	hits[0] = 0
	btn._down = false
	btn._gui_input(up)
	check(hits[0] == 0, "仅松开（未在控件内按下）不触发 (got %d)" % hits[0])

	btn.queue_free()


# —— 4) UiPanel 构造 ——
func _test_panel() -> void:
	var p = UiPanel.new()
	root.add_child(p)
	p.size = Vector2(760, 400)
	p.title = "太 阁 立 志 传 2"
	check(p.title == "太 阁 立 志 传 2", "面板标题可设置")
	check(p.title_height == 0, "默认标题栏高度 0（走 UiPanel.TITLE_BAR_H）")
	check(UiPanel.TITLE_BAR_H > 0, "标题栏常量 > 0 (got %d)" % UiPanel.TITLE_BAR_H)
	p.queue_free()


# —— 5) 标题画面改用自绘控件 ——
func _test_title_screen() -> void:
	var title: Control = (load("res://scenes/main.tscn") as PackedScene).instantiate()
	root.add_child(title)
	current_scene = title
	await process_frame
	await process_frame

	var n_panel := 0
	var n_btn := 0
	var btn_text := ""
	for c in title.get_children():
		if c is UiPanel:
			n_panel += 1
		if c is UiButton:
			n_btn += 1
			btn_text = str(c.get("text"))
	check(n_panel == 1, "标题画面含 1 个自绘面板 (got %d)" % n_panel)
	check(n_btn == 1, "标题画面含 1 个自绘按钮 (got %d)" % n_btn)
	check(btn_text.contains("开 始"), "自绘按钮文本 = %s" % btn_text)

	# 点击 → 跳转主角选择（链路不变）
	var target: Node = null
	for c in title.get_children():
		if c is UiButton:
			target = c
	target.pressed.emit()
	await process_frame
	await process_frame
	check(current_scene != null and current_scene.name == "ProtagonistSelect",
		"自绘按钮点击 → 主角选择 (%s)" % (current_scene.name if current_scene != null else "null"))


# —— 6) UiLabel 自绘多行文本 ——
func _test_label() -> void:
	var l = UiLabel.new()
	root.add_child(l)
	l.size = Vector2(400, 120)
	l.text = "织田信长\n大名"
	check(l.text == "织田信长\n大名", "UiLabel 多行文本可设置")
	check(l.line_spacing > 1.0, "UiLabel 行距倍率 > 1 (got %.2f)" % l.line_spacing)
	check(UiTheme.text_size("织田信长", l.font_size).x > 0, "UiLabel 文本可度量")
	l.queue_free()


# —— 递归统计自绘控件 / 原生控件（计数器用 Array 传引用）——
func _count(node: Node, ui_btn: Array, native: Array, panel: Array, label: Array) -> void:
	for c in node.get_children():
		if c is UiButton:
			ui_btn[0] += 1
		elif c is Button:
			native[0] += 1
		if c is UiPanel:
			panel[0] += 1
		if c is UiLabel:
			label[0] += 1
		_count(c, ui_btn, native, panel, label)


# —— 7) 主角选择 / 状态画面 已改为自绘控件 ——
func _test_converted_screens() -> void:
	# 主角选择：1 面板 + 6 自绘按钮，0 个原生 Button
	var psel: Control = (load("res://scenes/screens/protagonist_select.tscn") as PackedScene).instantiate()
	root.add_child(psel)
	await process_frame
	var ub := [0]
	var nb := [0]
	var pn := [0]
	var lb := [0]
	_count(psel, ub, nb, pn, lb)
	check(pn[0] >= 1, "主角选择含自绘面板 (got %d)" % pn[0])
	check(ub[0] == 6, "主角选择含 6 个自绘按钮 (got %d)" % ub[0])
	check(nb[0] == 0, "主角选择已无原生 Button (got %d)" % nb[0])
	psel.queue_free()

	# 状态画面：需先开局（未开局 _refresh 会跳回标题）
	var gs = root.get_node("/root/GameState")
	gs.start_new_game(13)
	ub = [0]; nb = [0]; pn = [0]; lb = [0]
	var status: Control = (load("res://scenes/screens/status_screen.tscn") as PackedScene).instantiate()
	root.add_child(status)
	await process_frame
	_count(status, ub, nb, pn, lb)
	check(pn[0] >= 1, "状态画面含自绘面板 (got %d)" % pn[0])
	check(ub[0] == 12, "状态画面含 12 个自绘按钮 (10 技能+休养+回标题, got %d)" % ub[0])
	check(nb[0] == 0, "状态画面已无原生 Button (got %d)" % nb[0])
	check(lb[0] == 3, "状态画面含 3 个自绘文本 _info/_stat/_help (got %d)" % lb[0])
	# 对外契约仍在
	check(str(status._info.get("text")).contains("织田信长"), "_info.text 契约保持")
	check(str(status._stat.get("text")).contains("魅力"), "_stat.text 契约保持")
	check(str(status._help.get("text")).contains("MSGX"), "_help.text 帮助栏就位")
	check(status._skill_buttons.size() == 10, "_skill_buttons 仍为 10 (got %d)" % status._skill_buttons.size())
	status.queue_free()


func _run() -> void:
	_test_theme()
	_test_button_states()
	_test_button_input()
	_test_panel()
	_test_label()
	await _test_title_screen()
	await _test_converted_screens()

	print("")
	if _fails == 0:
		print("[HD-5 PASS] 全部断言通过 ✅")
		quit(0)
	else:
		push_error("[HD-5 FAIL] %d 项断言失败 ❌" % _fails)
		quit(1)
