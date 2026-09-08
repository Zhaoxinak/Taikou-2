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
		draw_string(f, Vector2(0.0, y + UiTheme.baseline_y(ln, lh, font_size)), ln,
			h_align, size.x, font_size, color)
		y += lh
