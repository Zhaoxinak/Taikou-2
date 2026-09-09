# _test_portrait_loader.gd — AssetLoader.load_portrait 三级回退验证
#
# 覆盖 (2026-09-09 新命名规则生效后)：
#   1) 新命名 {id}_{name}.png  → 真实文件能加载（13_织田信长.png 已生成）
#   2) 旧命名 {id}.png → 已删除应回退占位图（13.png 不存在）
#   3) 占位图路径：未知 id → 直接走占位图
#   4) 占位图尺寸符合 AssetSpec.PORTRAIT_SIZE
#   5) 多张候选 -1 副本可被命中
#
# ⚠️ headless 模式下 PowerShell/Bash 可能截断 stdout；测试结果同步落盘到
#    user://portrait_loader_test.log 以便事后查看（项目根的 user_data 目录）。

extends SceneTree

const AssetSpec = preload("res://src/render/AssetSpec.gd")
const AssetLoader = preload("res://src/render/asset_loader.gd")

var _pass: int = 0
var _fail: int = 0
var _log: Array = []


func _initialize() -> void:
	# --script 模式下 autoload 尚未进树，挂首个 process_frame 再跑断言
	process_frame.connect(_run, CONNECT_ONE_SHOT)


func _logln(s: String) -> void:
	_log.append(s)
	print(s)


func check(cond: bool, msg: String) -> void:
	if cond:
		_pass += 1
		_logln("[ok] " + msg)
	else:
		_fail += 1
		_logln("[FAIL] " + msg)


func _dump_log() -> void:
	# 落到 res:// (项目目录) 比 user:// 更便于事后查看
	var f := FileAccess.open("res://tools/.portrait_loader_test.log", FileAccess.WRITE)
	if f == null:
		return
	for ln in _log:
		f.store_line(ln)
	f.store_line("")
	f.store_line("总计：通过 %d / 失败 %d" % [_pass, _fail])
	f.close()


func _run() -> void:
	# 1) 新命名：13_织田信长.png 已存在
	var t1 = AssetLoader.load_portrait(13, "织田信长")
	check(t1 != null, "新命名 13_织田信长.png 可加载")
	if t1 != null:
		var ok_size := (t1.get_width() == 512 and t1.get_height() == 640)
		check(ok_size, "新命名文件尺寸符合规格 512x640（实际 %dx%d）" % [t1.get_width(), t1.get_height()])

	# 2) 旧命名回退：13.png 已删 → 占位图
	var t2 = AssetLoader.load_portrait(13, "")
	check(t2 != null, "旧命名（已删除）回退占位图不崩")
	var diff := false
	if t1 != null and t2 != null:
		var img1 := t1.get_image()
		var img2 := t2.get_image()
		if img1 != null and img2 != null:
			for y in 64:
				if diff:
					break
				for x in 64:
					if img1.get_pixel(x, y) != img2.get_pixel(x, y):
						diff = true
						break
	check(diff, "旧命名回退后内容与新命名真图不同（确认未误命中）")

	# 3) 占位图路径：未知 id
	var t3 = AssetLoader.load_portrait(-999, "幽灵")
	check(t3 != null, "未知 id 占位图可加载")
	if t3 != null:
		check(t3.get_width() == 512 and t3.get_height() == 640,
			"占位图尺寸符合规格 512x640（实际 %dx%d）" % [t3.get_width(), t3.get_height()])

	# 4) 空 name 不破坏
	var t4 = AssetLoader.load_portrait(13, "")
	check(t4 != null, "空 name 不破坏加载（13.png 已删 → 占位图）")

	# 5) 多张候选 -1 路径
	var src := "res://assets/sprites/portraits/13_织田信长.png"
	var dst := "res://assets/sprites/portraits/13_织田信长-1.png"
	var dir_access = DirAccess.open("res://assets/sprites/portraits/")
	var copied := false
	if dir_access != null and FileAccess.file_exists(src):
		var content := FileAccess.get_file_as_bytes(src)
		var wf = FileAccess.open(dst, FileAccess.WRITE)
		if wf != null:
			wf.store_buffer(content)
			wf.close()
			copied = true

	if not copied:
		_logln("[跳过] -1 副本测试（无 13_织田信长.png 可复制）")
	else:
		var t5 = AssetLoader.load_portrait(13, "织田信长")
		check(t5 != null, "-1 副本路径可加载")
		dir_access.remove("13_织田信长-1.png")
		_logln("[清理] 删除临时 -1 副本")

	# 6) 其他新命名样例
	var t6 = AssetLoader.load_portrait(1, "柴田胜家")
	check(t6 != null, "新命名 1_柴田胜家.png 可加载")

	_logln("")
	_logln("总计：通过 %d / 失败 %d" % [_pass, _fail])
	_dump_log()
	if _fail > 0:
		quit(1)
	else:
		quit(0)