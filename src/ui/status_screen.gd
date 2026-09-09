extends Control
## 状态画面（HD-5 自绘）：五维 / 技能 / 職位 / 忠诚 / 体力 / 年月
## 主命：修行（10 技能各一钮，封顶 3）/ 休养（回满体力）；每次主命推进 1 月。
##
## 布局全在 UiTheme 设计空间（1920×1080），废除旧实现的硬编码 font_size(30/20) 与像素偏移。
## 2026-09-09 修正：改为 VBoxContainer 主布局，避免旧版手动 position + Container 混用导致的
## 技能按钮错位、底部按钮不可见/无法点击问题；同时保留键盘兜底（Esc/Enter/Space）。
##
## ⚠️ 对外契约保持不变：`_info` / `_stat`（均有 `.text`）、`_skill_buttons`（有 `.text`）、
##    `_on_train(idx)` / `_on_rest()` / `_on_back()` —— UI 流程测试依赖这些名字。

const UiTheme = preload("res://src/ui/UiTheme.gd")
const UiPanel = preload("res://src/ui/UiPanel.gd")
const UiButton = preload("res://src/ui/UiButton.gd")
const UiLabel = preload("res://src/ui/UiLabel.gd")
const ConstsRef = preload("res://src/core/Consts.gd")

# 自绘文本（平替原 Godot Label，保留 .text 契约）——故意不标类型，便于动态访问自定义属性
var _info
var _stat
var _skill_buttons: Array = []

const _PANEL := Vector2(1240, 820)
const _CONTENT_W := 1120.0
const _CONTENT_TOP := 64.0   # 标题栏高度 + 留白

# 帮助栏（MSGX 原版说明文接 UI）
var _help
const _HELP_HINT := "将鼠标移到技能上，可查看原版说明（MSGX）；Enter/Space=休养，Esc=回标题"
# 技能槽顺序（Consts.SKILL_NAMES）→ MSGX 文本 id（§MESSAGE1 帮助文 7..16）
#   口才7 马术8 算术9 剑术12 忍术15 兵法13 洋枪14 筑城16 礼法10 茶道11
const _SKILL_MSGX: Array[int] = [7, 8, 9, 12, 15, 13, 14, 16, 10, 11]


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS
	_build()
	_refresh()


func _build() -> void:
	# —— 自绘面板（背景 + 标题栏）——
	var panel := UiPanel.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.size = _PANEL
	panel.position = -_PANEL * 0.5
	panel.title = "状 态"
	add_child(panel)

	# —— 主内容区：VBoxContainer，避免旧版手动 position 与 Container 布局冲突 ——
	var vbox := VBoxContainer.new()
	vbox.set_anchors_preset(Control.PRESET_CENTER)
	vbox.size = Vector2(_CONTENT_W, _PANEL.y - _CONTENT_TOP - 20)
	vbox.position = Vector2(-_CONTENT_W * 0.5, -_PANEL.y * 0.5 + _CONTENT_TOP)
	vbox.add_theme_constant_override("separation", 14)
	add_child(vbox)

	# —— 顶行：姓名 / 職位 / 年月 ——
	_info = UiLabel.new()
	_info.custom_minimum_size = Vector2(0, 52)
	_info.font_size = UiTheme.FONT_HEAD
	_info.h_align = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(_info)

	# —— 五维 / 忠诚 / 体力 / 功勲（多行自绘）——
	_stat = UiLabel.new()
	_stat.custom_minimum_size = Vector2(0, 260)
	_stat.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_stat.font_size = UiTheme.FONT_BODY
	vbox.add_child(_stat)

	# —— 10 技能按钮（5×2 网格）——
	var grid := GridContainer.new()
	grid.columns = 5
	grid.custom_minimum_size = Vector2(0, 136)
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	grid.add_theme_constant_override("h_separation", 10)
	grid.add_theme_constant_override("v_separation", 10)
	vbox.add_child(grid)

	for k in ConstsRef.SKILL_NAMES.size():
		var b := UiButton.new()
		b.font_size = UiTheme.FONT_SMALL
		b.custom_minimum_size = Vector2(0, 58)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.pressed.connect(_on_train.bind(k))
		b.mouse_entered.connect(_show_skill_help.bind(k))
		b.mouse_exited.connect(_reset_help)
		grid.add_child(b)
		_skill_buttons.append(b)

	# —— 休养 / 回标题 ——
	var row2 := HBoxContainer.new()
	row2.custom_minimum_size = Vector2(0, 64)
	row2.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row2.add_theme_constant_override("separation", 16)
	vbox.add_child(row2)

	var rest_btn := UiButton.new()
	rest_btn.text = "休养（体力回满）"
	rest_btn.font_size = UiTheme.FONT_SMALL
	rest_btn.custom_minimum_size = Vector2(0, 58)
	rest_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rest_btn.pressed.connect(_on_rest)
	row2.add_child(rest_btn)

	var back_btn := UiButton.new()
	back_btn.text = "回标题"
	back_btn.font_size = UiTheme.FONT_SMALL
	back_btn.custom_minimum_size = Vector2(0, 58)
	back_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	back_btn.pressed.connect(_on_back)
	row2.add_child(back_btn)

	var world_btn := UiButton.new()
	world_btn.text = "外出（大地图）"
	world_btn.font_size = UiTheme.FONT_SMALL
	world_btn.custom_minimum_size = Vector2(0, 58)
	world_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	world_btn.pressed.connect(_on_go_world)
	row2.add_child(world_btn)

	# —— 底部帮助栏（MSGX 说明文渲染）——
	_help = UiLabel.new()
	_help.custom_minimum_size = Vector2(0, 44)
	_help.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_help.font_size = UiTheme.FONT_SMALL
	vbox.add_child(_help)
	_reset_help()


## 键盘兜底：即使鼠标/按钮焦点异常也能操作。
## 若当前焦点在某按钮上，Enter/Space 留给该按钮（未来 UiButton 接键盘时避免重复触发）。
func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_ESCAPE:
				accept_event()
				_on_back()
			KEY_ENTER, KEY_KP_ENTER, KEY_SPACE:
				var focus_owner := get_viewport().gui_get_focus_owner()
				if focus_owner != null and is_ancestor_of(focus_owner):
					return
				accept_event()
				_on_rest()
			KEY_G:
				accept_event()
				_on_go_world()


## 悬停技能 → 显示该技能的原版 MSGX 说明文
func _show_skill_help(k: int) -> void:
	if k < 0 or k >= _SKILL_MSGX.size():
		_reset_help()
		return
	var txt := GameData.get_text(int(_SKILL_MSGX[k]))
	if txt.is_empty():
		_reset_help()
		return
	_help.text = "【%s】%s" % [ConstsRef.SKILL_NAMES[k], txt]


func _reset_help() -> void:
	_help.text = _HELP_HINT


func _on_train(idx: int) -> void:
	var r: Dictionary = GameState.train_skill(idx)
	if not bool(r.get("ok", false)):
		_info.text = "修行失败：%s" % String(r.get("reason", "?"))
	_refresh()


func _on_rest() -> void:
	GameState.rest()
	_refresh()


func _on_back() -> void:
	get_tree().change_scene_to_file("res://scenes/main.tscn")


## 外出 → 大地图（方案 B 主循环打通点）
func _on_go_world() -> void:
	GameState.enter_world()
	get_tree().change_scene_to_file("res://scenes/screens/world_screen.tscn")


func _refresh() -> void:
	var st: Dictionary = GameState.get_status()
	if st.is_empty():
		get_tree().change_scene_to_file("res://scenes/main.tscn")
		return
	_info.text = "%s　%s　%d 年 %d 月" % [
		st["name"], st["rank_name"], int(st["year"]), int(st["month"])]
	var lines: Array = []
	var f: Dictionary = st["forces"]
	for k in ConstsRef.FORCE_NAMES.size():
		lines.append("%s %d" % [ConstsRef.FORCE_CN[k], int(f.get(ConstsRef.FORCE_NAMES[k], 0))])
	lines.append("忠诚 %d" % int(st["loyalty"]))
	lines.append("体力 %d/%d" % [int(st["stamina"]), int(st["stamina_max"])])
	lines.append("功勲 %d" % int(st["merit"]))
	_stat.text = "\n".join(PackedStringArray(lines)) + "\n"
	for k in _skill_buttons.size():
		var lv := int(st["skill_levels"][k])
		var b = _skill_buttons[k]
		b.text = "%s %d/3" % [ConstsRef.SKILL_NAMES[k], lv]
		# UiButton 用 enabled（而非 Godot Button 的 disabled）
		b.enabled = lv < ConstsRef.SKILL_CAP
