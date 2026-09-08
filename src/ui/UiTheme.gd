extends RefCounted
## HD-5 自绘 UI 基座：分辨率无关度量 + 和风调色板 + 字体加载
##
## ⚠️ 不用 class_name（--script 无头模式不建全局类缓存），跨文件一律 preload：
##    const UiTheme = preload("res://src/ui/UiTheme.gd")
##
## 设计基准 = 1920×1080（= project.godot 的 viewport_width/height）。
## 工程用 `window/stretch/mode = canvas_items` + `aspect = expand`，
## 因此所有 UI 只要在「设计空间」布局，引擎就会按窗口自动缩放并保持矢量锐利：
##
##   1080p (1920×1080) → 1.000x
##   2K    (2560×1440) → 1.333x
##   4K    (3840×2160) → 2.000x
##
## ⇒ 绝不要为某个分辨率硬编码像素/字号（旧 title_screen 的 font_size=28 即反例）。
##   ui_scale() 仅供日志/校验；布局一律用本文件的常量。

# —— 设计基准 ——
const DESIGN := Vector2i(1920, 1080)

# —— 字号（设计空间）——
const FONT_TITLE := 76
const FONT_HEAD  := 44
const FONT_BODY  := 30
const FONT_SMALL := 24

# —— 间距 ——
const PAD_SM := 10
const PAD_MD := 18
const PAD_LG := 30

# —— 描边 / 控件尺寸 ——
const BORDER   := 3
const BTN_W    := 360
const BTN_H    := 72
const PANEL_MIN_W := 480

# —— 和风调色板（深褐底 + 金边 + 米白字）——
const C_PANEL_BG   := Color(0.102, 0.071, 0.047, 0.90)
const C_PANEL_EDGE := Color(0.784, 0.635, 0.353, 1.0)
const C_BTN_BG     := Color(0.180, 0.125, 0.075, 0.95)
const C_BTN_HOVER  := Color(0.290, 0.204, 0.118, 0.97)
const C_BTN_DOWN   := Color(0.060, 0.040, 0.024, 1.0)
const C_BTN_OFF_BG := Color(0.140, 0.140, 0.140, 0.70)
const C_TEXT       := Color(0.949, 0.894, 0.784, 1.0)
const C_TEXT_OFF   := Color(0.541, 0.510, 0.463, 1.0)
const C_ACCENT     := Color(0.851, 0.702, 0.416, 1.0)
const C_SHADOW     := Color(0.0, 0.0, 0.0, 0.45)

# —— 字体缓存 ——
static var _font: Font = null
static var _font_tried: bool = false

## 纯函数：给定窗口尺寸返回 UI 缩放比（可无头断言，不依赖真实窗口）
static func scale_for(win: Vector2i) -> float:
	if win.x <= 0:
		return 1.0
	return float(win.x) / float(DESIGN.x)

## 当前实际 UI 缩放比（窗口 / 设计基准）
static func ui_scale() -> float:
	return scale_for(DisplayServer.window_get_size())

## 分辨率档位标签（与 DisplayAdapter 口径一致：按高度）
static func preset_label(win: Vector2i) -> String:
	if win.y >= 2160: return "4K"
	if win.y >= 1440: return "2K"
	return "1080p"

## 载入并缓存 CJK 字体；失败回退到引擎默认字体（返回非 null，保证 draw_string 可用）
##
## ⚠️ 用 FontFile.load_dynamic_font(绝对路径) 而非 ResourceLoader.load(res://...)：
##    后者依赖 .import 产物的导入缓存，未导入过的工程会加载失败并静默回退到无 CJK 的
##    默认字体（中文/日文全变方框）。直接按绝对路径载入 TTF 可绕过导入缓存。
static func font() -> Font:
	if _font != null:
		return _font
	if _font_tried:
		return ThemeDB.fallback_font
	_font_tried = true
	const P := "res://assets/fonts/NotoSansSC-Regular.ttf"
	var fp := ProjectSettings.globalize_path(P)
	if FileAccess.file_exists(fp):
		var ff := FontFile.new()
		if ff.load_dynamic_font(fp) == OK:
			_font = ff
			return _font
	push_warning("[UiTheme] CJK 字体载入失败，回退引擎默认字体（中文可能显示为方框）: %s" % fp)
	return ThemeDB.fallback_font

## 文本尺寸（设计空间），供自绘居中排版
static func text_size(s: String, font_size: int) -> Vector2:
	var f := font()
	if f == null or s.is_empty():
		return Vector2.ZERO
	return f.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size)

## 垂直居中基线 y：让 s 在高度 h 内视觉居中
static func baseline_y(s: String, h: float, font_size: int) -> float:
	var f := font()
	if f == null:
		return h * 0.5
	return (h - (f.get_ascent(font_size) + f.get_descent(font_size))) * 0.5 + f.get_ascent(font_size)
