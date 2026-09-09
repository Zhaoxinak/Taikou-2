# _compile_all.gd — 全项目 GDScript 编译巡检（extends SceneTree）
#
# 遍历 res:// 下所有 .gd，用 load() 触发编译，收集任何编译失败（返回 null）。
# 目的：在 macOS 终于有 Godot 的情况下，一次性抓出所有 GDScript 4 语法不兼容
# （如 int(str,16) / Texture.FILTER_* / Variant 推断当错误 等），避免运行期才崩。
# 运行：Godot --headless --path <project> --script res://tools/_compile_all.gd

extends SceneTree

var _errs: Array = []
var _count: int = 0


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)


func _run() -> void:
	_scan("res://")
	if _errs.is_empty():
		print("\n[ALL COMPILE OK] 共编译 %d 个 .gd 文件，无语法错误" % _count)
		quit(0)
	else:
		print("\n[%d COMPILE FAIL] 共编译 %d 个文件" % [_errs.size(), _count])
		for e in _errs:
			push_error(e)
		quit(1)


func _scan(dir: String) -> void:
	var d := DirAccess.open(dir)
	if d == null:
		return
	d.list_dir_begin()
	var f := d.get_next()
	while f != "":
		if f == "." or f == "..":
			f = d.get_next()
			continue
		var p := dir.path_join(f)
		if d.current_is_dir():
			_scan(p)
		elif f.ends_with(".gd"):
			_count += 1
			var s := load(p)
			if s == null:
				_errs.append("COMPILE FAIL: " + p)
		f = d.get_next()
	d.list_dir_end()
