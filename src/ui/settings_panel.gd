extends Control
## 设置面板：音乐/音效音量 + 窗口大小档位 + 全屏开关
## 自绘面板背景；子控件全部为编辑器可见的 item（UiButton / UiLabel）。
## 设计空间 1920×1080，canvas_items 自动跨分辨率缩放。
## ⚠️ 不用 class_name（无头模式不建类缓存）。

const UiTheme = preload("res://src/ui/UiTheme.gd")

## 设置变化（音量/分辨率/全屏任一改变）→ 由 title_screen 应用 + 持久化
signal settings_changed
signal closed

## 0.0..1.0 线性音量（面板与 AudioManager 的 dB 互转由 title_screen 负责）
var bgm_volume: float = 0.8:
	set(v):
		bgm_volume = clampf(v, 0.0, 1.0)
		_refresh()
var sfx_volume: float = 0.8:
	set(v):
		sfx_volume = clampf(v, 0.0, 1.0)
		_refresh()
var fullscreen: bool = false:
	set(v):
		fullscreen = v
		_refresh()
var res_preset: String = "1080p":
	set(v):
		res_preset = v
		_refresh()

const _STEP := 0.05   # 音量步进 5%

var _bgm_val: Control = null
var _sfx_val: Control = null
var _res_1080: Control = null
var _res_2k: Control = null
var _res_4k: Control = null
var _fs_btn: Control = null


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	_bgm_val = get_node_or_null("BgmVal")
	_sfx_val = get_node_or_null("SfxVal")
	_res_1080 = get_node_or_null("Res1080")
	_res_2k = get_node_or_null("Res2K")
	_res_4k = get_node_or_null("Res4K")
	_fs_btn = get_node_or_null("FullscreenBtn")
	_refresh()
	_connect_buttons()


func _connect_buttons() -> void:
	_bind("BgmMinus", _on_bgm_minus)
	_bind("BgmPlus", _on_bgm_plus)
	_bind("SfxMinus", _on_sfx_minus)
	_bind("SfxPlus", _on_sfx_plus)
	_bind("Res1080", func() -> void: _set_res("1080p"))
	_bind("Res2K", func() -> void: _set_res("2K"))
	_bind("Res4K", func() -> void: _set_res("4K"))
	_bind("FullscreenBtn", _on_fullscreen)
	_bind("CloseBtn", _on_close)


func _bind(node_name: String, fn: Callable) -> void:
	var b := get_node_or_null(node_name)
	if b != null and b.has_signal("pressed"):
		b.pressed.connect(fn)


func _on_bgm_minus() -> void:
	bgm_volume = maxf(0.0, bgm_volume - _STEP)
	settings_changed.emit()
func _on_bgm_plus() -> void:
	bgm_volume = minf(1.0, bgm_volume + _STEP)
	settings_changed.emit()
func _on_sfx_minus() -> void:
	sfx_volume = maxf(0.0, sfx_volume - _STEP)
	settings_changed.emit()
func _on_sfx_plus() -> void:
	sfx_volume = minf(1.0, sfx_volume + _STEP)
	settings_changed.emit()
func _set_res(p: String) -> void:
	res_preset = p
	settings_changed.emit()
func _on_fullscreen() -> void:
	fullscreen = not fullscreen
	settings_changed.emit()
func _on_close() -> void:
	visible = false
	closed.emit()


func _refresh() -> void:
	if _bgm_val != null:
		_bgm_val.text = "%d%%" % int(round(bgm_volume * 100.0))
	if _sfx_val != null:
		_sfx_val.text = "%d%%" % int(round(sfx_volume * 100.0))
	_set_btn_text(_res_1080, "1080p", res_preset == "1080p")
	_set_btn_text(_res_2k, "2K", res_preset == "2K")
	_set_btn_text(_res_4k, "4K", res_preset == "4K")
	if _fs_btn != null:
		_fs_btn.text = "全 屏：%s" % ("开" if fullscreen else "关")
	queue_redraw()


## 档位按钮：选中项加"▸"标记
func _set_btn_text(btn: Control, base: String, active: bool) -> void:
	if btn == null:
		return
	btn.text = ("▸ " if active else "  ") + base


## 自绘面板底（和风深褐 + 金边 + 标题）
func _draw() -> void:
	var r := Rect2(Vector2.ZERO, size)
	draw_rect(Rect2(r.position + Vector2(0, 6), r.size), UiTheme.C_SHADOW)
	draw_rect(r, UiTheme.C_PANEL_BG)
	draw_rect(r, UiTheme.C_PANEL_EDGE, false, UiTheme.BORDER)
	# 标题
	var f := UiTheme.font()
	if f == null:
		return
	var fs := UiTheme.FONT_HEAD
	var x := UiTheme.PAD_LG + 8.0
	draw_string(f, Vector2(x, UiTheme.baseline_y("设 置", 84.0, fs)), "设 置",
		HORIZONTAL_ALIGNMENT_LEFT, size.x - x * 2.0, fs, UiTheme.C_ACCENT)
	draw_line(Vector2(UiTheme.PAD_LG, 96.0), Vector2(size.x - UiTheme.PAD_LG, 96.0),
		UiTheme.C_PANEL_EDGE, 1.0)
