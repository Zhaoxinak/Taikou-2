extends SceneTree
## 全模块编译探针：逐个 preload src/ 下每个 .gd，暴露「项目级 --check-only 漏检」的语法错误。
##
## 背景：--check-only 只解析被场景/autoload 引用到的脚本；像 council.gd 这类
## 仅被测试引用的模块若含语法错误，项目校验照样报「零错误」——直到实跑才炸。
## 本探针填补该盲区。
##
## 运行：Godot --headless --script res://tools/_test_all_compile.gd

var _ok := 0
var _bad := 0


func _run() -> void:
	var files := _list_gd("res://src")
	files.sort()
	print("扫描 src/ 下 %d 个 .gd" % files.size())
	for f in files:
		var res = load(f)
		if res == null:
			_bad += 1
			print("  [FAIL] ", f)
		else:
			_ok += 1
	print("\nRESULT: %d ok / %d fail" % [_ok, _bad])
	quit(0 if _bad == 0 else 1)


func _list_gd(dir_path: String) -> Array:
	var out: Array = []
	var d := DirAccess.open(dir_path)
	if d == null:
		return out
	d.list_dir_begin()
	var n := d.get_next()
	while n != "":
		if n.begins_with("."):
			n = d.get_next(); continue
		var full := dir_path.path_join(n)
		if d.current_is_dir():
			out.append_array(_list_gd(full))
		elif n.ends_with(".gd"):
			out.append(full)
		n = d.get_next()
	d.list_dir_end()
	return out


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)
