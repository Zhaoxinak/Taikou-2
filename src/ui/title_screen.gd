extends Control
## 标题画面（HD-5 自绘）：自绘面板 + 自绘「开始新游戏」按钮
##
## 全部度量取自 UiTheme（设计空间 1920×1080），由 canvas_items 自动跨分辨率缩放，
## 不再有硬编码 font_size / 像素偏移（旧实现 font_size=28 在 4K 下不会缩放）。

const UiTheme = preload("res://src/ui/UiTheme.gd")
const UiPanel = preload("res://src/ui/UiPanel.gd")
const UiButton = preload("res://src/ui/UiButton.gd")

const _PANEL_SIZE := Vector2(760, 400)


func _ready() -> void:
	# 铺满视口，子控件的 CENTER 锚点才有意义
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS
	_build()


func _build() -> void:
	# —— 中央面板（自绘：深褐底 + 金边 + 标题栏）——
	var panel := UiPanel.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.size = _PANEL_SIZE
	panel.position = -_PANEL_SIZE * 0.5
	panel.title = "太 阁 立 志 传 2"
	add_child(panel)

	# —— 开始按钮（自绘，含 hover / pressed / disabled 三态）——
	var btn := UiButton.new()
	btn.set_anchors_preset(Control.PRESET_CENTER)
	btn.size = Vector2(UiTheme.BTN_W, UiTheme.BTN_H)
	btn.position = Vector2(-UiTheme.BTN_W * 0.5, _PANEL_SIZE.y * 0.5 - UiTheme.BTN_H - UiTheme.PAD_LG)
	btn.text = "开 始 新 游 戏"
	btn.pressed.connect(_on_start)
	add_child(btn)


func _on_start() -> void:
	get_tree().change_scene_to_file("res://scenes/screens/protagonist_select.tscn")
