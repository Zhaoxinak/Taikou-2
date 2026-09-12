extends Control
## 标题画面（自绘）：自绘面板 + 自绘「开始新游戏」「设置」按钮
## 全部度量取自 UiTheme（设计空间 1920×1080），由 canvas_items 自动跨分辨率缩放。
## 2026-09-12 重构：UI 预置在 scenes/main.tscn（编辑器可见），脚本只做 BGM、跳转与设置持久化。
## 2026-09-13 新增：设置面板（音量/窗口大小/全屏），user://settings.cfg 持久化。

const UiTheme = preload("res://src/ui/UiTheme.gd")
const SETTINGS_PATH := "user://settings.cfg"

var _settings_panel: Control = null

func _ready() -> void:
	# 铺满视口，子控件的 CENTER 锚点才有意义
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS
	_settings_panel = get_node_or_null("SettingsPanel")
	if _settings_panel != null:
		_settings_panel.settings_changed.connect(_on_settings_changed)
		_settings_panel.closed.connect(_on_settings_closed)
	_load_settings()
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


func _on_settings() -> void:
	if _settings_panel != null:
		_settings_panel.visible = true


func _on_settings_closed() -> void:
	pass


## 设置项任一改变 → 立即应用（音量实时、窗口即时）+ 写盘
func _on_settings_changed() -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio != null:
		audio.set_bgm_volume_db(linear_to_db(_settings_panel.bgm_volume))
		audio.set_sfx_volume_db(linear_to_db(_settings_panel.sfx_volume))
	var da := get_node_or_null("/root/DisplayAdapter")
	if da != null:
		if da.current_preset() != _settings_panel.res_preset:
			da.set_resolution_preset(_settings_panel.res_preset)
		if da.is_fullscreen() != _settings_panel.fullscreen:
			da.toggle_fullscreen()
	_save_settings()


# —— 设置持久化（user://settings.cfg）——

func _load_settings() -> void:
	if _settings_panel == null:
		return
	var cfg := ConfigFile.new()
	if cfg.load(SETTINGS_PATH) != OK:
		return
	if cfg.has_section_key("audio", "bgm_volume"):
		_settings_panel.bgm_volume = cfg.get_value("audio", "bgm_volume", 0.8)
	if cfg.has_section_key("audio", "sfx_volume"):
		_settings_panel.sfx_volume = cfg.get_value("audio", "sfx_volume", 0.8)
	if cfg.has_section_key("window", "resolution"):
		_settings_panel.res_preset = cfg.get_value("window", "resolution", "1080p")
	if cfg.has_section_key("window", "fullscreen"):
		_settings_panel.fullscreen = cfg.get_value("window", "fullscreen", false)
	# 启动即应用（音量 + 窗口）
	_on_settings_changed()


func _save_settings() -> void:
	if _settings_panel == null:
		return
	var cfg := ConfigFile.new()
	cfg.set_value("audio", "bgm_volume", _settings_panel.bgm_volume)
	cfg.set_value("audio", "sfx_volume", _settings_panel.sfx_volume)
	cfg.set_value("window", "resolution", _settings_panel.res_preset)
	cfg.set_value("window", "fullscreen", _settings_panel.fullscreen)
	cfg.save(SETTINGS_PATH)
