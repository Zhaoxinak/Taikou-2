extends Control
## 标题画面（自绘）：自绘面板 + 自绘「开始新游戏」按钮
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
	_start_bgm()


## 标题 BGM：CD 轨 1。
## 依据：原版「BGM 槽位 → 轨号 = 槽位 + 2」（0x498eb8），故槽位 0 起于轨 2 ——
##   **轨 1 不在常规 BGM 槽位体系内**，推定为 OP / 标题曲（时长 76.7s，与 BGM 同量级）。
## ⚠️ 原版「场景 → 槽位」调度表走虚表间接派发（播放函数 0 直接调用者），需 emu 钩
##   CdPlay 的 caller 才能闭合；此处只接标题曲，进游戏后沿用（CD-DA 本就跨场景连续播放）。
func _start_bgm() -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio == null:
		return
	audio.play_bgm_track(1)


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
