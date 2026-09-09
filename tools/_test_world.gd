extends SceneTree
## 大地图（方案 B）逻辑测试：world_map.gd 纯函数 + GameState 大地图方法。
## 触发：process_frame 后 _run（autoload 已就绪，可直接用 GameState/GameData）。
## 不依赖 UI；逻辑验证另由 scripts/_test_world_mirror.py 实跑（本机 --script 失效时走此替代链路）。

const WorldMapRef = preload("res://src/core/world_map.gd")

var _pass := 0
var _fail := 0


func _init() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)


func _approx(a: Vector2, b: Vector2, tol := 0.5) -> bool:
	return abs(a.x - b.x) <= tol and abs(a.y - b.y) <= tol


func _chk(name: String, cond: bool) -> void:
	if cond:
		_pass += 1
		print("  PASS  ", name)
	else:
		_fail += 1
		printerr("  FAIL  ", name)


func _run() -> void:
	var view := Rect2(0, 64, 1920, 960)
	# —— project 角点 ——
	_chk("project 原点", _approx(WorldMapRef.project(Vector2.ZERO, 1820, 1120, view), Vector2(180, 64)))
	_chk("project 右下角", _approx(WorldMapRef.project(Vector2(1820, 1120), 1820, 1120, view), Vector2(1740, 1024)))
	# —— unproject 是 project 的逆 ——
	var p := WorldMapRef.project(Vector2(500, 300), 1820, 1120, view)
	var u := WorldMapRef.unproject(p, 1820, 1120, view)
	_chk("unproject 往返", _approx(u, Vector2(500, 300)))
	# —— clamp_pos 边界 ——
	_chk("clamp 上限", WorldMapRef.clamp_pos(Vector2(99999, -50), 1820, 1120) == Vector2(1820, 0))
	# —— step 步长与 clamp ——
	_chk("step 自原点", WorldMapRef.step(Vector2.ZERO, 1, 1, 1820, 1120) == Vector2(36, 36))
	_chk("step 越界 clamp", WorldMapRef.step(Vector2(1810, 1110), 1, 1, 1820, 1120) == Vector2(1820, 1120))
	# —— nearest ——
	var positions := {0: Vector2(0, 0), 1: Vector2(100, 100), 2: Vector2(1000, 1000)}
	_chk("nearest 近 0", WorldMapRef.nearest(Vector2(5, 5), positions) == 0)
	_chk("nearest 近 2", WorldMapRef.nearest(Vector2(990, 990), positions) == 2)
	_chk("nearest 空", WorldMapRef.nearest(Vector2.ZERO, {}) == -1)
	# —— GameState 大地图方法（不依赖 started）——
	# ⚠️ --script 模式下 autoload 不是全局标识符，必须 root.get_node 取
	var gs = root.get_node("/root/GameState")
	var gd = root.get_node("/root/GameData")
	_chk("默认未进城", gs.current_castle == -1)
	gs.move_player(1, 0)
	_chk("move_player 改变坐标", gs.player_map_pos.x == 36)
	gs.enter_castle(0)
	_chk("enter_castle 设城", gs.current_castle == 0)
	_chk("enter_castle 移到城坐标", gs.player_map_pos == gd.get_castle_pos(0))
	var n: int = gs.nearest_castle()
	_chk("nearest_castle 有效 id", n >= 0)
	gs.enter_world()
	_chk("enter_world 回野外", gs.current_castle == -1)

	print("WORLD TEST: pass=%d fail=%d" % [_pass, _fail])
	quit(_fail if _fail > 0 else 0)
