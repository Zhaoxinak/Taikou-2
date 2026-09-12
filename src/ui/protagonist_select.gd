extends Control
## 主角选择（自绘）：列出 6 名可选主角（is_selectable），点选即开局进入状态画面
##
## 布局全在 UiTheme 设计空间；废除旧实现的硬编码 font_size(32/22) 与像素偏移。
## ⚠️ VBoxContainer 保持为**根的直接子节点**（UI 流程测试按此结构遍历按钮）。
## 2026-09-12 重构：UI 预置在 scenes/screens/protagonist_select.tscn（6 个主角槽），
## 脚本只填充文本与绑定 pid。

const UiTheme = preload("res://src/ui/UiTheme.gd")
const ConstsRef = preload("res://src/core/Consts.gd")

@onready var _list: VBoxContainer = $Panel/List


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS
	_fill_slots()


## 按 is_selectable 顺序把 6 个预置槽位填上主角名，并绑定点击事件。
func _fill_slots() -> void:
	var officers: Array = GameData._loader.officers.values() if GameData._loader != null else []
	var selectable: Array = []
	for o in officers:
		if o is Dictionary and bool(o.get("is_selectable", false)):
			selectable.append(o)
	selectable.sort_custom(func(a, b): return int(a["id"]) < int(b["id"]))

	for i in mini(selectable.size(), _list.get_child_count()):
		var o: Dictionary = selectable[i]
		var pid := int(o["id"])
		var rank: int = int(o.get("rank", 0))
		var rank_name: String = ConstsRef.RANK_NAMES[rank] if rank < ConstsRef.RANK_NAMES.size() else "?"
		var b: Control = _list.get_child(i)
		b.text = "%s%s　（%s / #%-3d）" % [o.get("surname", ""), o.get("given", ""), rank_name, pid]
		b.pressed.connect(_on_pick.bind(pid))


func _on_pick(pid: int) -> void:
	if not GameState.start_new_game(pid):
		return
	get_tree().change_scene_to_file("res://scenes/screens/status_screen.tscn")
