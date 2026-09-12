extends Control
## 标题画面（自绘）：自绘面板 + 自绘「开始新游戏」按钮
## 全部度量取自 UiTheme（设计空间 1920×1080），由 canvas_items 自动跨分辨率缩放。
## 2026-09-12 重构：UI 预置在 scenes/main.tscn（编辑器可见），脚本只做 BGM 与跳转。

const UiTheme = preload("res://src/ui/UiTheme.gd")

func _ready() -> void:
	# 铺满视口，子控件的 CENTER 锚点才有意义
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS
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


func _on_start() -> void:
	get_tree().change_scene_to_file("res://scenes/screens/protagonist_select.tscn")
