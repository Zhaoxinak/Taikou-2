extends Control
## 自绘面板：和风深褐底 + 金边；可选标题栏（左侧金竖条 + 标题文字）。
## ⚠️ 不用 class_name（无头模式不建类缓存），引用方 preload 本脚本。

const UiTheme = preload("res://src/ui/UiTheme.gd")
## 所有度量来自 UiTheme（设计空间），跨分辨率自动缩放。

@export var title: String = "":
	set(v):
		title = v
		queue_redraw()

## 标题栏高度（0 = 不画标题栏）
@export var title_height: int = 0:
	set(v):
		title_height = v
		queue_redraw()

const TITLE_BAR_H := 56


func _init() -> void:
	custom_minimum_size = Vector2(UiTheme.PANEL_MIN_W, 120)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _ready() -> void:
	resized.connect(queue_redraw)


func _draw() -> void:
	var r := Rect2(Vector2.ZERO, size)
	# 阴影
	draw_rect(Rect2(r.position + Vector2(0, 6), r.size), UiTheme.C_SHADOW)
	# 底 + 金边
	draw_rect(r, UiTheme.C_PANEL_BG)
	draw_rect(r, UiTheme.C_PANEL_EDGE, false, UiTheme.BORDER)

	if title.is_empty():
		return

	var bar_h: float = float(title_height if title_height > 0 else TITLE_BAR_H)
	# 标题栏分隔线
	draw_line(Vector2(UiTheme.PAD_SM, bar_h), Vector2(size.x - UiTheme.PAD_SM, bar_h),
		UiTheme.C_PANEL_EDGE, 1.0)
	# 左侧金竖条（和风书签）
	draw_rect(Rect2(UiTheme.PAD_SM, bar_h * 0.5 - 14.0, 6.0, 28.0), UiTheme.C_ACCENT)
	# 标题文字
	var f := UiTheme.font()
	if f == null:
		return
	var fs := UiTheme.FONT_HEAD
	var x := UiTheme.PAD_SM + 18.0
	draw_string(f, Vector2(x, UiTheme.baseline_y(title, bar_h, fs)), title,
		HORIZONTAL_ALIGNMENT_LEFT, size.x - x - UiTheme.PAD_SM, fs, UiTheme.C_TEXT)
