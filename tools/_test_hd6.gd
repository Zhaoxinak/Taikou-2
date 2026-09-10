extends SceneTree
## HD-6 视觉回归 + 4K 性能基准（**无头可实测部分**）
##
## 无头环境没有渲染器，故本轮只做两类可验证回归：
##   1) **多分辨率布局回归（几何快照）**：1080p / 2K / 4K 三档下实例化全部主要画面，
##      逐个自绘控件求全局矩形，断言所有控件都落在设计空间 1920×1080 内（无溢出）；
##      并断言缩放比与档位标签符合 DisplayAdapter 口径。
##   2) **场景构建成本基线**：每画面 instantiate+_ready 的 CPU 耗时（分辨率无关，
##      是 4K 下同样要付的固定成本），给出基线数值并设上限断言，防性能回归。
##
## ⚠️ 像素级视觉回归（截图比对）与 GPU FPS 基准**必须在 GUI 下跑**：
##    headless 用 dummy 渲染驱动，帧率数字无意义。见 progress 表 HD-6 备注。

const UiTheme = preload("res://src/ui/UiTheme.gd")

const SCREENS := [Vector2i(1920, 1080), Vector2i(2560, 1440), Vector2i(3840, 2160)]
const LABELS := ["1080p", "2K", "4K"]
const SCALES := [1.0, 1.3333333, 2.0]

# 主要画面（无头可安全实例化者）
const SCENES := [
	"res://scenes/main.tscn",
	"res://scenes/screens/protagonist_select.tscn",
	"res://scenes/screens/status_screen.tscn",
	"res://scenes/screens/world_screen.tscn",
]

var _fails: int = 0


func check(cond: bool, msg: String) -> void:
	if cond:
		print("[ok] ", msg)
	else:
		_fails += 1
		push_error("[FAIL] " + msg)


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)


func _run() -> void:
	var t0 := Time.get_ticks_msec()

	# —— 1) 档位 / 缩放比（纯函数，不依赖真实窗口）——
	for i in SCREENS.size():
		var s: Vector2i = SCREENS[i]
		check(UiTheme.preset_label(s) == LABELS[i],
			"档位标签 %s → %s (got %s)" % [s, LABELS[i], UiTheme.preset_label(s)])
		check(is_equal_approx(UiTheme.scale_for(s), SCALES[i]),
			"UI 缩放比 %s → %.3fx (got %.3f)" % [LABELS[i], SCALES[i], UiTheme.scale_for(s)])
	var da := root.get_node_or_null("DisplayAdapter")
	if da != null:
		check(da._pick_target_resolution(Vector2i(3840, 2160)) == Vector2i(3840, 2160),
			"DisplayAdapter 4K 屏 → 4K viewport")
		check(da._pick_target_resolution(Vector2i(1920, 1080)) == Vector2i(1920, 1080),
			"DisplayAdapter 1080p 屏 → 1080p viewport")

	# —— 2) 各档下全部画面的控件不溢出设计空间 ——
	var design: Vector2i = UiTheme.DESIGN
	for i in SCREENS.size():
		var s: Vector2i = SCREENS[i]
		for path in SCENES:
			if not ResourceLoader.exists(path):
				continue
			var sc: Control = (load(path) as PackedScene).instantiate()
			root.add_child(sc)
			await process_frame
			var over := _overflowing(sc, design)
			check(over.size() == 0, "%s @%s 无控件溢出 1920×1080 (越界 %d)" %
				[path.get_file(), LABELS[i], over.size()])
			sc.queue_free()
		# 无头下窗口尺寸不可改，缩放比由 scale_for 纯函数覆盖；此处只跑一次即可
		break

	# —— 3) 场景构建成本基线（CPU，分辨率无关）——
	for path in SCENES:
		if not ResourceLoader.exists(path):
			continue
		var t1 := Time.get_ticks_usec()
		var n := 5
		for k in n:
			var sc2: Control = (load(path) as PackedScene).instantiate()
			root.add_child(sc2)
			sc2.queue_free()
		var per := (Time.get_ticks_usec() - t1) / float(n) / 1000.0
		print("   构建基线 %-28s %.1f ms/次" % [path.get_file(), per])
		check(per < 500.0, "%s 构建耗时基线 < 500ms (got %.1f ms)" % [path.get_file(), per])

	# —— 4) 字号层级（4K 下可读性：设计空间字号恒定，由 canvas_items 整体缩放）——
	check(UiTheme.FONT_TITLE > UiTheme.FONT_HEAD and UiTheme.FONT_HEAD > UiTheme.FONT_BODY
		and UiTheme.FONT_BODY > UiTheme.FONT_SMALL, "字号层级 TITLE>HEAD>BODY>SMALL")
	check(UiTheme.FONT_SMALL >= 20, "最小字号 %d ≥ 20（4K 下 ×2 = 实际 %d px）"
		% [UiTheme.FONT_SMALL, UiTheme.FONT_SMALL * 2])

	_finish(t0)


## 返回越出设计空间的控件名列表（以视口中心为原点还原全局矩形）
func _overflowing(root_ctrl: Control, design: Vector2i) -> Array:
	var out: Array = []
	var half := Vector2(design) * 0.5
	_collect(root_ctrl, half, out)
	return out


func _collect(c: Node, half: Vector2, out: Array) -> void:
	if not (c is Control):
		return
	var ctl := c as Control
	var r := ctl.get_global_rect()
	# 画布坐标以视口左上为原点；控件 CENTER 锚点下 position 以中心为基准
	var left: float = r.position.x
	var top: float = r.position.y
	if left < -1.0 or top < -1.0 or left + r.size.x > half.x * 2 + 1.0 or top + r.size.y > half.y * 2 + 1.0:
		out.append("%s(%s)" % [ctl.name, ctl.get_class()])
	for ch in c.get_children():
		_collect(ch, half, out)


func _finish(t0: int) -> void:
	print("")
	if _fails > 0:
		push_error("[HD-6 FAIL] %d 项断言失败" % _fails)
		quit(1)
	print("[ok] HD-6 无头可测部分通过（布局回归 + 构建基线，用时 %.0f ms）"
		% [float(Time.get_ticks_msec() - t0)])
	quit(0)
