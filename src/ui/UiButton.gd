@tool
extends Control
## 自绘按钮：不依赖 Godot 默认 Theme，外观由 _draw() 全权绘制。
## ⚠️ 不用 class_name（无头模式不建类缓存），引用方 preload 本脚本。
## @tool：编辑器内实时绘制外观（场景化后可直接在编辑器查看）。

const UiTheme = preload("res://src/ui/UiTheme.gd")

## GAIJI autoload 节点缓存（按树查找，见 _gaiji_node）
var _gaiji_cache: Node = null
## 布局尺寸来自 UiTheme（设计空间 1920×1080），由 canvas_items 自动跨分辨率缩放。
##
## 视觉状态机抽成 static 纯函数（state_bg / state_edge），便于无头断言。

signal pressed

@export var text: String = "":
	set(v):
		text = v
		queue_redraw()

@export var enabled: bool = true:
	set(v):
		enabled = v
		mouse_filter = Control.MOUSE_FILTER_STOP if v else Control.MOUSE_FILTER_IGNORE
		queue_redraw()

## 字号（容器空间不足时可调小；默认 UiTheme.FONT_BODY）
var font_size: int = UiTheme.FONT_BODY:
	set(v):
		font_size = v
		queue_redraw()

# —— 高级文字效果（按钮默认开启细描边，在和风深底上更清晰）——
var outline_size: int = 2
var outline_color: Color = Color(0.0, 0.0, 0.0, 1.0)
var shadow_offset: Vector2 = Vector2(2, 2)
var shadow_color: Color = Color(0.0, 0.0, 0.0, 0.35)
var letter_spacing: float = 0.0
var gaiji_smooth: bool = false

var _hover: bool = false
var _down: bool = false


# —— 纯状态机（无渲染依赖，可无头测试）——
static func state_bg(p_enabled: bool, hover: bool, down: bool) -> Color:
	if not p_enabled:
		return UiTheme.C_BTN_OFF_BG
	if down:
		return UiTheme.C_BTN_DOWN
	if hover:
		return UiTheme.C_BTN_HOVER
	return UiTheme.C_BTN_BG


static func state_edge(p_enabled: bool) -> Color:
	return UiTheme.C_PANEL_EDGE if p_enabled else UiTheme.C_TEXT_OFF


static func state_text(p_enabled: bool) -> Color:
	return UiTheme.C_TEXT if p_enabled else UiTheme.C_TEXT_OFF


func _init() -> void:
	custom_minimum_size = Vector2(UiTheme.BTN_W, UiTheme.BTN_H)
	focus_mode = Control.FOCUS_ALL


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP if enabled else Control.MOUSE_FILTER_IGNORE
	mouse_entered.connect(func() -> void: _hover = true; queue_redraw())
	mouse_exited.connect(func() -> void: _hover = false; _down = false; queue_redraw())
	focus_entered.connect(queue_redraw)
	focus_exited.connect(queue_redraw)
	resized.connect(queue_redraw)


func _gui_input(event: InputEvent) -> void:
	if not enabled:
		return
	var mb := event as InputEventMouseButton
	if mb == null or mb.button_index != MOUSE_BUTTON_LEFT:
		return
	if mb.pressed:
		_down = true
		queue_redraw()
		accept_event()
	else:
		# 按下在本控件内即触发；移出控件时 mouse_exited 已把 _down 复位，
		# 因此「在控件外松开」不会误触发。
		if _down:
			_play_click()
			pressed.emit()
		_down = false
		queue_redraw()
		accept_event()


## 点击音效 id（原版 CLICK = 0；-1 关闭）。安全查找 autoload，缺失时静默跳过。
var click_sfx_id: int = 0


func _play_click() -> void:
	if click_sfx_id < 0:
		return
	var am := get_node_or_null("/root/AudioManager")
	if am != null:
		am.play_sfx(click_sfx_id)


func _draw() -> void:
	var r := Rect2(Vector2.ZERO, size)
	# 阴影（下移 4px，制造浮起感）
	draw_rect(Rect2(r.position + Vector2(0, 4), r.size), UiTheme.C_SHADOW)
	# 底 + 边
	draw_rect(r, state_bg(enabled, _hover or has_focus(), _down))
	draw_rect(r, state_edge(enabled), false, UiTheme.BORDER)

	# 居中文本（自绘，经 GAIJI 渲染层）
	var f := UiTheme.font()
	if f == null or text.is_empty():
		return
	var fs := font_size
	# 水平居中：以 r.size.x 为宽度 + CENTER 对齐；经 GAIJI 高级渲染层（描边/投影/富文本）
	# ⚠️ 不用 autoload 全局名 `Gaiji`（--script 下无法编译解析），按树查找 + 兜底原生绘制
	var fx: Node = _gaiji_node()
	if fx != null:
		fx.draw_string_fx(self, Vector2(0.0, UiTheme.baseline_y(text, size.y, fs)), text,
			f, fs, state_text(enabled), HORIZONTAL_ALIGNMENT_CENTER, size.x,
			outline_size, outline_color, shadow_offset, shadow_color, letter_spacing, gaiji_smooth)
	else:
		draw_string(f, Vector2(0.0, UiTheme.baseline_y(text, size.y, fs)), text,
			HORIZONTAL_ALIGNMENT_CENTER, size.x, fs, state_text(enabled))


## 取 GAIJI autoload 节点（按树查找，缓存）；不可用返回 null
func _gaiji_node() -> Node:
	if _gaiji_cache != null and is_instance_valid(_gaiji_cache):
		return _gaiji_cache
	if not is_inside_tree():
		return null
	_gaiji_cache = get_tree().root.get_node_or_null("/root/Gaiji")
	return _gaiji_cache
