# DisplayAdapter.gd — 多分辨率运行时适配（★ M0 基础设施）
#
# 设计目标
# --------
# 复刻画面在 1080p / 2K / 4K 下都保持锐利：
#   - 内部逻辑坐标系 640×400（保持原版构图与 UI 锚点）
#   - 启动时检测屏幕原生分辨率，自动选最佳 viewport
#   - 素材按 6x (3840×2400) 准备，运行时按屏幕缩放
#
# 缩放比（内容清晰度）
# --------------------
#   1080p (1920×1080) : 1920/640 = 3.0x  → 6x 素材缩 0.5x  ✓ 锐利
#   2K    (2560×1440) : 2560/640 = 4.0x  → 6x 素材缩 0.667x ✓ 锐利
#   4K    (3840×2160) : 3840/640 = 6.0x  → 6x 素材原生     ✓ 锐利
#
# 用法
# ----
# 1. project.godot 注册为 autoload: `DisplayAdapter="*res://src/core/DisplayAdapter.gd"`
# 2. 任何 UI 元素都按 640×400 逻辑坐标布局，Godot stretch 模式自动缩放
# 3. 6x 资源按 1:1 设置 Sprite2D.texture，scale 仍为 1.0（Godot 会按 viewport/640 缩放）
#
# 注意
# ----
# - 16:9 屏幕下，逻辑 640×400 (16:10) 内容会有左右黑边（aspect=expand 下不会有，但比例会变）
#   → 当前用 aspect=expand（UI 居中，背景延伸）；如想保 16:10 比例改 aspect=keep

extends Node

# 逻辑分辨率（原版 640×400，16:10）
const LOGICAL_SIZE := Vector2i(640, 400)
const LOGICAL_ASPECT := 1.6   # 640/400

# 目标分辨率档位（按高度选）
const PRESET_1080P := Vector2i(1920, 1080)
const PRESET_2K    := Vector2i(2560, 1440)
const PRESET_4K    := Vector2i(3840, 2160)

# 6x 重制素材目标尺寸（保证 4K 下原生锐利）
const HD_TILE      := Vector2i(96, 96)        # 原 16×16 ×6
const HD_PORTRAIT  := Vector2i(384, 480)      # 原 64×80 ×6
const HD_BG        := Vector2i(3840, 2400)    # 原 640×400 ×6

# 运行时状态
var viewport_size: Vector2i = Vector2i.ZERO
var scale_factor: float = 1.0
var resolution_label: String = ""


func _ready() -> void:
	# 必须在任何 UI 加载前设定
	process_mode = Node.PROCESS_MODE_ALWAYS
	viewport_size = _pick_target_resolution(DisplayServer.screen_get_size())
	_apply_viewport(viewport_size)
	_log_resolution()


# 根据屏幕原生分辨率选最佳 viewport
# 优先匹配屏幕高度 → 4K > 2K > 1080p
func _pick_target_resolution(screen: Vector2i) -> Vector2i:
	var h := screen.y
	if h >= 2160:
		resolution_label = "4K"
		return PRESET_4K
	if h >= 1440:
		resolution_label = "2K"
		return PRESET_2K
	resolution_label = "1080p"
	return PRESET_1080P


# 应用 viewport + 记录缩放比
func _apply_viewport(target: Vector2i) -> void:
	var win := get_window()
	win.size = target
	# viewport 跟随窗口
	scale_factor = target.x / float(LOGICAL_SIZE.x)
	print("[DisplayAdapter] 选定 %s viewport=%s, 逻辑=%s, 缩放=%.2fx" %
		[resolution_label, target, LOGICAL_SIZE, scale_factor])


# 全屏切换（Alt+Enter 等价）
func toggle_fullscreen() -> void:
	var win := get_window()
	win.mode = Window.MODE_FULLSCREEN if win.mode != Window.MODE_FULLSCREEN else Window.MODE_WINDOWED


func is_fullscreen() -> bool:
	return get_window().mode == Window.MODE_FULLSCREEN


# 按档位切换窗口分辨率（1080p / 2K / 4K），设置界面调用
func set_resolution_preset(preset: String) -> void:
	var target: Vector2i
	match preset:
		"4K":
			target = PRESET_4K
			resolution_label = "4K"
		"2K":
			target = PRESET_2K
			resolution_label = "2K"
		_:
			target = PRESET_1080P
			resolution_label = "1080p"
	_apply_viewport(target)


func current_preset() -> String:
	return resolution_label


# 供 HUD 调用的便捷查询
func is_4k() -> bool: return resolution_label == "4K"
func is_2k() -> bool: return resolution_label == "2K"


# 逻辑坐标 → 屏幕坐标（一般不需要，Godot 自动处理）
func to_screen(p: Vector2) -> Vector2:
	return p * scale_factor


# 屏幕坐标 → 逻辑坐标（处理鼠标点击时用）
func to_logical(p: Vector2) -> Vector2:
	return p / scale_factor


func _log_resolution() -> void:
	var screen := DisplayServer.screen_get_size()
	print("[DisplayAdapter] 屏幕原生=%s, 缩放比=%.2fx, 推荐素材倍率=6x" %
		[screen, scale_factor])
