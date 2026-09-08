extends Control
## 主角选择（HD-5 自绘）：列出 6 名可选主角（is_selectable），点选即开局进入状态画面
##
## 布局全在 UiTheme 设计空间；废除旧实现的硬编码 font_size(32/22) 与像素偏移。
## ⚠️ VBoxContainer 保持为**根的直接子节点**（UI 流程测试按此结构遍历按钮）。

const UiTheme = preload("res://src/ui/UiTheme.gd")
const UiPanel = preload("res://src/ui/UiPanel.gd")
const UiButton = preload("res://src/ui/UiButton.gd")
const ConstsRef = preload("res://src/core/Consts.gd")

const _PANEL := Vector2(880, 660)
const _LIST_W := 760.0


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS
	_build()


func _build() -> void:
	# —— 自绘面板（背景 + 标题栏）——
	var panel := UiPanel.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.size = _PANEL
	panel.position = -_PANEL * 0.5
	panel.title = "选 择 主 角"
	add_child(panel)

	# —— 主角列表（VBox + 自绘按钮）——
	var list := VBoxContainer.new()
	list.set_anchors_preset(Control.PRESET_CENTER)
	list.size = Vector2(_LIST_W, 520)
	list.position = Vector2(-_LIST_W * 0.5, -_PANEL.y * 0.5 + 60)
	list.add_theme_constant_override("separation", 12)
	add_child(list)

	var officers: Array = GameData._loader.officers.values() if GameData._loader != null else []
	var selectable: Array = []
	for o in officers:
		if o is Dictionary and bool(o.get("is_selectable", false)):
			selectable.append(o)
	selectable.sort_custom(func(a, b): return int(a["id"]) < int(b["id"]))

	for o in selectable:
		var pid := int(o["id"])
		var rank: int = int(o.get("rank", 0))
		var rank_name: String = ConstsRef.RANK_NAMES[rank] if rank < ConstsRef.RANK_NAMES.size() else "?"
		var b := UiButton.new()
		b.text = "%s%s　（%s / #%-3d）" % [o.get("surname", ""), o.get("given", ""), rank_name, pid]
		b.font_size = UiTheme.FONT_SMALL
		b.custom_minimum_size = Vector2(0, 58)
		b.pressed.connect(_on_pick.bind(pid))
		list.add_child(b)


func _on_pick(pid: int) -> void:
	if not GameState.start_new_game(pid):
		return
	get_tree().change_scene_to_file("res://scenes/screens/status_screen.tscn")
