extends SceneTree
## 大地图（复刻原版）逻辑测试：world_map.gd 纯函数 + GameState 大地图方法。
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
	var mw := 48.0
	var mh := 36.0
	# —— project 角点（48×36 网格，等比 fit 到 1920×960）——
	var s: float = minf(view.size.x / mw, view.size.y / mh)
	var off := view.position + Vector2((view.size.x - mw * s), (view.size.y - mh * s)) * 0.5
	_chk("project 原点", _approx(WorldMapRef.project(Vector2.ZERO, mw, mh, view), off))
	_chk("project 右下角", _approx(WorldMapRef.project(Vector2(mw, mh), mw, mh, view), off + Vector2(mw, mh) * s))
	# —— unproject 是 project 的逆 ——
	var p := WorldMapRef.project(Vector2(30, 20), mw, mh, view)
	var u := WorldMapRef.unproject(p, mw, mh, view)
	_chk("unproject 往返", _approx(u, Vector2(30, 20)))
	# —— clamp_pos 边界 ——
	_chk("clamp 上限", WorldMapRef.clamp_pos(Vector2(99999, -50), mw, mh) == Vector2(mw, 0))
	# —— step：1 格 = 1 逻辑单位（复刻原版逐格移动）——
	_chk("step 自原点", WorldMapRef.step(Vector2.ZERO, 1, 1, mw, mh) == Vector2(1, 1))
	_chk("step 越界 clamp", WorldMapRef.step(Vector2(47.5, 35.5), 1, 1, mw, mh) == Vector2(mw, mh))
	# —— move_towards：朝目标走 1 格 / 到达 ——
	var mt := WorldMapRef.move_towards(Vector2(0, 0), Vector2(10, 0), mw, mh)
	_chk("move_towards 走 1 格", _approx(mt, Vector2(1, 0), 0.01))
	var mt2 := WorldMapRef.move_towards(Vector2(9.8, 0), Vector2(10, 0), mw, mh)
	_chk("move_towards 到达钳制", mt2 == Vector2(10, 0))
	# —— within_enter：1.6 格阈值（原版相邻即询问）——
	_chk("within_enter 近", WorldMapRef.within_enter(Vector2(0, 0), Vector2(1.5, 0)))
	_chk("within_enter 远", not WorldMapRef.within_enter(Vector2(0, 0), Vector2(5, 0)))
	# —— path_cells / travel_days ——
	var cells := WorldMapRef.path_cells(Vector2(0, 0), Vector2(4, 3), mw, mh)
	_chk("path_cells 端点数", cells.size() == 6)
	_chk("travel_days 格数", WorldMapRef.travel_days(Vector2(0, 0), Vector2(5, 0)) == 5)
	# —— nearest ——
	var positions := {0: Vector2(0, 0), 1: Vector2(100, 100), 2: Vector2(1000, 1000)}
	_chk("nearest 近 0", WorldMapRef.nearest(Vector2(5, 5), positions) == 0)
	_chk("nearest 近 2", WorldMapRef.nearest(Vector2(990, 990), positions) == 2)
	_chk("nearest 空", WorldMapRef.nearest(Vector2.ZERO, {}) == -1)
	# —— GameState 大地图方法（不依赖 started）——
	var gs = root.get_node("/root/GameState")
	var gd = root.get_node("/root/GameData")
	_chk("默认未进城", gs.current_castle == -1)
	# 逐格移动推进 1 天
	var day0: int = int(gs.day)
	var pos0: Vector2 = gs.player_map_pos
	gs.move_player(1, 0)
	_chk("move_player 走 1 格", _approx(gs.player_map_pos, pos0 + Vector2(1, 0), 0.01))
	_chk("move_player 推进 1 天", gs.day == ((day0) % 30) + 1 or gs.day != day0)
	# 自动移动
	var tgt: Vector2 = gs.player_map_pos + Vector2(3, 0)
	var guard := 0
	while not gs.move_player_towards(tgt) and guard < 10:
		guard += 1
	_chk("move_player_towards 到达", gs.player_map_pos.distance_to(tgt) <= 0.01)
	# 坐船：把主角挪到港町 124（大坂）坐标上
	gs.player_map_pos = gd.get_castle_pos(124)
	var res: Dictionary = gs.travel_by_sea(160)
	_chk("坐船 124→160 ok", res.get("ok", false) == true)
	_chk("nearest_port 124", gs.nearest_port() == 124)
	_chk("坐船推进天数", int(res.get("days", 0)) >= 1)
	_chk("坐船后体力 ≤20", int(gs.get_status().get("stamina", 999)) <= 20)
	_chk("坐船后到达 160", gs.player_map_pos.distance_to(gd.get_castle_pos(160)) <= 0.01)
	# 非港町不能坐船
	gs.player_map_pos = gd.get_castle_pos(66)
	var bad: Dictionary = gs.travel_by_sea(124)
	_chk("非港町拒绝坐船", bad.get("ok", true) == false)
	# 航线不存在
	gs.player_map_pos = gd.get_castle_pos(124)
	var no_r: Dictionary = gs.travel_by_sea(195)
	_chk("无航线拒绝", no_r.get("ok", true) == false)
	gs.enter_world()
	_chk("enter_world 回野外", gs.current_castle == -1)

	print("WORLD TEST: pass=%d fail=%d" % [_pass, _fail])
	quit(_fail if _fail > 0 else 0)
