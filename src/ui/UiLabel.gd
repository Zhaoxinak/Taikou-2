extends Control
## HD-5 自绘文本：多行（\n）文本由 _draw() 自行排版，不依赖 Godot 默认 Label/Theme。
## ⚠️ 不用 class_name（无头模式不建类缓存），引用方 preload 本脚本。
##
## 保留 `text` 属性名，便于平替原 Godot `Label`（状态画面的 _info / _stat 即如此替换）。

const UiTheme = preload("res://src/ui/UiTheme.gd")

var text: String = "":
	set(v):
		text = v
		queue_redraw()

var font_size: int = UiTheme.FONT_BODY:
	set(v):
		font_size = v
		queue_redraw()

var color: Color:
	set(v):
		color = v
		queue_redraw()

var h_align: HorizontalAlignment = HORIZONTAL_ALIGNMENT_LEFT:
	set(v):
		h_align = v
		queue_redraw()

## 行距倍率（相对字号）
var line_spacing: float = 1.35

# —— 高级文字效果（默认关闭；设 >0 / 非零即启用）——
## 描边：在文字四周描边，提升在复杂背景上的可读性（常见于和风/策略游戏 UI）
var outline_size: int = 0
var outline_color: Color = Color(0.0, 0.0, 0.0, 1.0)
## 投影：整体偏移副本（零向量 = 关闭）
var shadow_offset: Vector2 = Vector2.ZERO
var shadow_color: Color = Color(0.0, 0.0, 0.0, 0.0)
## 字间距
var letter_spacing: float = 0.0
## 外字位图线性插值（放大更柔和；默认保持像素锐利）
var gaiji_smooth: bool = false


func _init() -> void:
	color = UiTheme.C_TEXT
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _ready() -> void:
	resized.connect(queue_redraw)


func _draw() -> void:
	var f := UiTheme.font()
	if f == null or text.is_empty():
		return
	var lines := text.split("\n")
	var lh: float = font_size * line_spacing
	var y: float = 0.0
	for ln in lines:
		var base_y := y + UiTheme.baseline_y(ln, lh, font_size)
		# 经 GAIJI 高级渲染层：无外字/无效果时纯原生绘制（零回归），否则启用描边/投影/富文本
		Gaiji.draw_string_fx(self, Vector2(0.0, base_y), ln, f, font_size, color, h_align, size.x,
			outline_size, outline_color, shadow_offset, shadow_color, letter_spacing, gaiji_smooth)
		y += lh
