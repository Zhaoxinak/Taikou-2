extends SceneTree
## HD-6 · 真实 GPU 基准 + 像素级视觉回归（**必须 GUI 实跑，勿用 --headless**）
##
## 无头模式是 dummy 渲染驱动，帧率/像素都没有意义；本脚本用真实渲染器跑：
##
##   1) **多分辨率 GPU 基准**：把每个画面塞进指定尺寸的 SubViewport（1920×1080 / 2560×1440 /
##      3840×2160），关 vsync，量 N 帧平均帧时间与等效 FPS。SubViewport 与物理窗口解耦，
##      故即使屏幕只有 2K 也能测到真实 4K 渲染成本。
##   2) **像素级视觉回归**：每档截图存 `_hd6_out/<档>_<画面>.png`，与 `baseline.json` 比对
##      sha256；不一致时降采样到 128×72 统计差异像素比例，超阈值即判回归。
##      首次运行自动建立基线（只记录不判失败）。
##
## 用法（GUI）：
##   Godot_v4.7.1-stable_win64_console.exe --script res://tools/_bench_hd6_gpu.gd
## 产物：`_hd6_out/*.png`、`_hd6_out/baseline.json`、`_hd6_out/bench.json`
##
## ⚠️ 主窗口自身也在渲染，会给所有档位叠加一份**相同的**固定开销（跨档对比仍有效）。

const TIERS := ["1080p", "2K", "4K"]
const TIER_SIZE := {
	"1080p": Vector2i(1920, 1080),
	"2K": Vector2i(2560, 1440),
	"4K": Vector2i(3840, 2160),
}
const SCENES := {
	"title": "res://scenes/main.tscn",
	"protagonist": "res://scenes/screens/protagonist_select.tscn",
	"status": "res://scenes/screens/status_screen.tscn",
	"command": "res://scenes/screens/command_screen.tscn",
	"world": "res://scenes/screens/world_screen.tscn",
	"battle": "res://scenes/screens/battle_screen.tscn",
}
const FRAMES := 30
const WARMUP := 5
const OUT_DIR := "res://_hd6_out/"
const DIFF_TOLERANCE := 0.02   # 降采样后差异像素比例上限 2%

var _fails: int = 0
var _baseline: Dictionary = {}
var _bench: Array = []


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
	# 关 vsync：否则所有档位都被刷新率封顶，测不出真实 GPU 成本
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)

	_ensure_dir()
	_load_baseline()
	var first_run: bool = _baseline.is_empty()

	for scene_key in SCENES:
		for tier in TIERS:
			var r: Dictionary = await _measure(scene_key, tier)
			if r.is_empty():
				continue
			_bench.append(r)

	_save_bench()
	if first_run:
		_save_baseline()
		print("")
		print("[i] 首次运行：已建立 %d 条视觉基线（%sbaseline.json）" % [_baseline.size(), OUT_DIR])
	else:
		_save_baseline()

	print("")
	print("=== HD-6 GPU 基准（%d 帧/档，vsync 关闭；GPU/CPU 为 RenderingServer 实测）===" % FRAMES)
	print("  %-12s %-8s %9s %8s %9s %8s %10s" %
		["画面", "档位", "墙钟ms", "FPS", "GPU ms", "CPU ms", "像素差异"])
	for r in _bench:
		print("  %-12s %-8s %9.2f %8.1f %9.3f %8.3f %10s" % [
			r["scene"], r["tier"], r["ms"], r["fps"], r["gpu_ms"], r["cpu_ms"],
			("基线" if bool(r.get("is_baseline", false)) else "%.2f%%" % (float(r["diff"]) * 100.0))])

	# 断言：视口尺寸正确 + **60FPS 预算**（一帧 16.67ms，GPU 实测须在内）
	const BUDGET_MS: float = 16.67
	for r in _bench:
		check(int(r["w"]) == int(TIER_SIZE[r["tier"]].x), "%s@%s 视口尺寸 = %s" %
			[r["scene"], r["tier"], r["tier"]])
		check(float(r["gpu_ms"]) < BUDGET_MS, "%s@%s GPU %.3f ms < 60FPS 预算 %.2f ms" %
			[r["scene"], r["tier"], float(r["gpu_ms"]), BUDGET_MS])
		if not bool(r.get("is_baseline", false)):
			check(float(r["diff"]) <= DIFF_TOLERANCE, "%s@%s 视觉差异 %.2f%% ≤ %.0f%%" %
				[r["scene"], r["tier"], float(r["diff"]) * 100.0, DIFF_TOLERANCE * 100.0])

	_finish(t0)


func _measure(scene_key: String, tier: String) -> Dictionary:
	var path: String = SCENES[scene_key]
	if not ResourceLoader.exists(path):
		return {}
	_ensure_session()
	var size: Vector2i = TIER_SIZE[tier]
	var sv := SubViewport.new()
	sv.size = size
	sv.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	sv.transparent_bg = false
	sv.disable_3d = false
	root.add_child(sv)
	# 开 GPU/CPU 计时：wall-clock 只量到 CPU 侧（GPU 异步），真实渲染成本要看这里
	RenderingServer.viewport_set_measure_render_time(sv.get_viewport_rid(), true)

	var sc: Node = (load(path) as PackedScene).instantiate()
	sv.add_child(sc)

	# 预热（首个画面含着色器编译，不能计入）
	for i in WARMUP:
		await process_frame
	await _draw_frames(3)

	var t1 := Time.get_ticks_usec()
	for i in FRAMES:
		await process_frame
		await _draw_frames(1)
	var elapsed := (Time.get_ticks_usec() - t1) / 1000.0
	var ms := elapsed / float(FRAMES)
	var rid := sv.get_viewport_rid()
	var gpu_ms := RenderingServer.viewport_get_measured_render_time_gpu(rid)
	var cpu_ms := RenderingServer.viewport_get_measured_render_time_cpu(rid)

	var img := sv.get_texture().get_image()
	var out := {}
	if img != null:
		var fname := "%s_%s.png" % [tier, scene_key]
		var fpath := OUT_DIR + fname
		img.save_png(fpath)
		var abs_path := ProjectSettings.globalize_path(fpath)
		var sha := FileAccess.get_sha256(abs_path)
		var is_base := not _baseline.has(fname)
		var diff := 0.0
		if is_base:
			img.save_png(OUT_DIR + "baseline_" + fname)   # 首跑：存基线副本供日后比对
		elif str(_baseline[fname]) != sha:
			diff = _diff_ratio(abs_path, fname)
		_baseline[fname] = sha
		out = {"scene": scene_key, "tier": tier, "ms": round(ms * 100.0) / 100.0,
			"fps": round((1000.0 / maxf(ms, 0.0001)) * 10.0) / 10.0,
			"gpu_ms": round(gpu_ms * 1000.0) / 1000.0,
			"cpu_ms": round(cpu_ms * 1000.0) / 1000.0,
			"w": img.get_width(), "h": img.get_height(), "file": fname,
			"diff": diff, "is_baseline": is_base}

	sc.queue_free()
	sv.queue_free()
	await process_frame
	return out


## 强制若干次绘制（部分场景非每帧更新）
func _draw_frames(n: int) -> void:
	for i in n:
		RenderingServer.force_draw()


## 确保有游戏会话：状态/大地图画面靠 GameState 出数据，无会话则信息区空白
func _ensure_session() -> void:
	var gs := root.get_node_or_null("GameState")
	if gs == null:
		return
	if gs.get_status().is_empty():
		gs.start_new_game(13)   # 织田信长


func _diff_ratio(cur_abs: String, fname: String) -> float:
	"""与基线比较：降采样到 128×72 后统计差异像素比例"""
	var base_abs := ProjectSettings.globalize_path(OUT_DIR + "baseline_" + fname)
	if not FileAccess.file_exists(base_abs):
		return 0.0
	var a := Image.load_from_file(base_abs)
	var b := Image.load_from_file(cur_abs)
	if a == null or b == null:
		return 0.0
	a.resize(128, 72, Image.INTERPOLATE_NEAREST)
	b.resize(128, 72, Image.INTERPOLATE_NEAREST)
	var n := a.get_width() * a.get_height()
	var diff := 0
	for y in a.get_height():
		for x in a.get_width():
			var pa := a.get_pixel(x, y)
			var pb := b.get_pixel(x, y)
			if abs(pa.r - pb.r) > 0.02 or abs(pa.g - pb.g) > 0.02 or abs(pa.b - pb.b) > 0.02:
				diff += 1
	return float(diff) / float(n)


func _ensure_dir() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))


func _load_baseline() -> void:
	var p := ProjectSettings.globalize_path(OUT_DIR + "baseline.json")
	if not FileAccess.file_exists(p):
		return
	var f := FileAccess.open(p, FileAccess.READ)
	if f == null:
		return
	var parsed = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) == TYPE_DICTIONARY:
		_baseline = parsed


func _save_baseline() -> void:
	var p := ProjectSettings.globalize_path(OUT_DIR + "baseline.json")
	var f := FileAccess.open(p, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify(_baseline, "\t"))
	f.close()


func _save_bench() -> void:
	var p := ProjectSettings.globalize_path(OUT_DIR + "bench.json")
	var f := FileAccess.open(p, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify(_bench, "\t"))
	f.close()


func _finish(t0: int) -> void:
	print("")
	if _fails > 0:
		push_error("[HD-6 GPU FAIL] %d 项断言失败" % _fails)
		quit(1)
	print("[ok] HD-6 GPU 基准 + 视觉回归完成（用时 %.1f s）" % [float(Time.get_ticks_msec() - t0) / 1000.0])
	quit(0)
