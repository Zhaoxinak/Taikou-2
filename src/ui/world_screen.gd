extends Control
## 大地图（复刻原版 · 像素风打磨版）
##
## 主循环：状态画面 → 大地图 → 逐格/点击移动 → 进城 / 坐船跨海
##   · 移动方式（原版）：
##       - 鼠标左键点击地图任意处 → 主角沿直线自动移动（每格推进天数，晴 1 / 雨雪 2）
##       - T 打开城町一览表 → 选城自动前往（原版「町/城移動」指令）
##       - 方向键 / WASD 逐格移动（也推进时间）
##       - 移动中按 Esc 停止；雨雪天行走变慢（豪雨時機動力が鈍る）
##   · 接近城（距离 ≤ ENTER_DIST）→ 高亮 + 底部提示，Enter 进城（城下町）
##   · 港町（沿海町城）→ 底部出现「坐船」提示，按 B 打开航线列表
##   · 天气：刻刻変化（原版 counter%4==0 每 4 天 tick）；HUD 显示 晴/曇/雨/雪，
##     雨雪天全屏粒子 + 季节陆地色调（冬雪灰 / 春新绿 / 夏深绿 / 秋枯黄）
##   · 背景 = 原版风日本列岛：海洋波纹 + 季节陆地 + 白色道路网 + 山形符号 + 城点分级
##   · 主角 = 像素武士小人（4 朝向行走动画）
##
## 布局在设计空间 1920×1080；地图可视区为去掉顶部/底部 HUD 的矩形。

const UiTheme = preload("res://src/ui/UiTheme.gd")
const UiLabel = preload("res://src/ui/UiLabel.gd")
const WorldMapRef = preload("res://src/core/world_map.gd")
const CastleTown = preload("res://src/ui/castle_town.gd")
const JapanMap = preload("res://src/ui/japan_map.gd")
const WeatherRef = preload("res://src/core/weather.gd")

const HUD_TOP := 64.0
const HUD_BOTTOM := 56.0
const MAP_VIEW := Rect2(0, HUD_TOP, 1920, 1080 - HUD_TOP - HUD_BOTTOM)
const MOVE_TICK := 0.25            # 自动移动每格间隔（秒；雨雪天 ×1.6 变慢）
const WALK_FRAME_TICK := 0.12      # 走路动画帧切换
const CAM_ZOOM := 2.4              # 镜头聚焦倍率（全图 1280×960 → 3072×2304，视口看 20×15 格）

# —— 季节陆地 / 海洋色调（原版大地图：绿陆蓝海，随季节微调）——
const LAND_COLORS := [
	Color(0.66, 0.72, 0.70, 1),   # 冬（12,1,2）雪灰
	Color(0.62, 0.72, 0.44, 1),   # 春 新绿
	Color(0.49, 0.62, 0.35, 1),   # 夏 深绿
	Color(0.68, 0.55, 0.33, 1),   # 秋 枯黄
]
const LAND_EDGE := Color(0.24, 0.30, 0.24, 1)
const SEA_COLORS := [
	Color(0.42, 0.58, 0.70, 1),   # 冬
	Color(0.50, 0.66, 0.78, 1),   # 春
	Color(0.45, 0.62, 0.76, 1),   # 夏
	Color(0.44, 0.58, 0.66, 1),   # 秋
]
const SEA_RIPPLE := Color(1, 1, 1, 0.10)
const ROAD_COLOR := Color(0.93, 0.90, 0.82, 0.55)

# 城点样式（原版：町城红块 / 军事城白点 / 港町白块+锚）
const TOWN_COLOR := Color(0.78, 0.24, 0.18, 1)
const MIL_COLOR := Color(0.86, 0.88, 0.90, 0.9)
const PORT_COLOR := Color(0.55, 0.85, 1.0, 1)
const NEAR_COLOR := Color(1.0, 0.92, 0.45, 1)

var _hud_top: CanvasItem
var _hud_bottom: CanvasItem
var _entered_castle: int = -1      # 进城 overlay 中显示的城 id（-1=未进城）
var _nearest_id: int = -1
var _castle_town: Control = null   # 城下町交互 UI（进城时挂载，离城时置 null）

var _move_target: Vector2 = Vector2.INF   # 点击自动移动目标（INF=未在移动）
var _move_timer: float = 0.0
var _cam := Vector2.ZERO            # 镜头左上角（全图屏幕像素坐标）
var _cam_target := Vector2.ZERO
var _walk_frame := 0
var _walk_timer := 0.0
var _face := Vector2(0, 1)               # 主角朝向（下=默认）
var _sea_menu: Array = []                # 坐船菜单（可达港 [{to,days}]），空=未打开
var _sea_sel: int = 0
var _msg: String = ""
var _town_list := false                  # 城町一览表打开
var _tl_scroll := 0
var _tl_sel := 0
var _tl_items: Array = []                # 城町一览表 [{id, name, prov}]
var _tl_provs: Array = []                # 一览表国分组标题
var _roads: Array = []                   # 道路网 [[Vector2, Vector2], ...] 逻辑坐标


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS
	var bg := ColorRect.new()
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bg.color = Color(0.05, 0.10, 0.14, 1)
	bg.show_behind_parent = true
	add_child(bg)
	_hud_top = _make_label()
	_hud_top.custom_minimum_size = Vector2(1880, HUD_TOP - 12)
	_hud_top.position = Vector2(20, 6)
	add_child(_hud_top)
	_hud_bottom = _make_label()
	_hud_bottom.custom_minimum_size = Vector2(1880, HUD_BOTTOM - 10)
	_hud_bottom.position = Vector2(20, 1080 - HUD_BOTTOM + 4)
	_hud_bottom.font_size = UiTheme.FONT_SMALL
	add_child(_hud_bottom)
	_set_initial_pos()
	_build_roads()
	_build_town_list()
	_update_nearest()
	_refresh_hud()
	_snap_cam()
	queue_redraw()


func _set_initial_pos() -> void:
	# 若主角尚未落点（开局），放到其所在/默认城坐标
	if GameState.player_map_pos == Vector2.ZERO and GameData.has_castle_map():
		var home := 0 if GameState.current_castle < 0 else GameState.current_castle
		GameState.player_map_pos = GameData.get_castle_pos(home)


func _make_label() -> CanvasItem:
	var l = UiLabel.new()
	l.font_size = UiTheme.FONT_BODY
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func _build_roads() -> void:
	## 道路网：同国最近 2 城连线（无向边，跨海自动断开——四国/九州不走陆路）
	if not GameData.has_castle_map():
		return
	var positions: Dictionary = GameData.get_castle_positions()
	var edges := {}
	for id in positions.keys():
		var prov: int = int(GameData.get_castle(int(id)).get("province", 255))
		var mine: Vector2 = positions[id]
		var cands := []
		for j in positions.keys():
			if j == id:
				continue
			if int(GameData.get_castle(int(j)).get("province", 255)) != prov:
				continue
			var d: float = mine.distance_to(positions[j])
			if d < 4.0:
				cands.append([d, j])
		cands.sort()
		var take: int = mini(2, cands.size())
		for k in range(take):
			var a: int = int(id)
			var b: int = int(cands[k][1])
			var key: String = "%d_%d" % [mini(a, b), maxi(a, b)]
			edges[key] = true
	_roads = []
	for key in edges.keys():
		var parts: PackedStringArray = key.split("_")
		_roads.append([positions[int(parts[0])], positions[int(parts[1])]])


func _build_town_list() -> void:
	## 城町一览表：92 町城 + 港町，按国分组
	_tl_items = []
	var rows := []
	for id in GameData.get_castle_positions().keys():
		var cid := int(id)
		if GameData.get_castle_has_town(cid) or GameData.is_port_city(cid):
			var c: Dictionary = GameData.get_castle(cid)
			rows.append({"id": cid, "name": str(c.get("name", "")), "prov": int(c.get("province", 255))})
	rows.sort_custom(func(a, b):
		var pa: int = int(a["prov"])
		var pb: int = int(b["prov"])
		if pa != pb:
			return pa < pb
		return str(a["name"]) < str(b["name"]))
	_tl_items = rows


func _refresh_hud() -> void:
	var st: Dictionary = GameState.get_status()
	var name_s: String = str(st.get("name", "")) if not st.is_empty() else ""
	var loc := "野外"
	if _entered_castle >= 0:
		loc = "【城下】" + str(GameData.get_castle(_entered_castle).get("name", ""))
	elif GameState.current_castle >= 0:
		loc = str(GameData.get_castle(GameState.current_castle).get("name", ""))
	var sp := ""
	var port_id := GameState.nearest_port()
	if port_id >= 0:
		sp = "（港町 %s）" % GameData.get_castle(port_id).get("name", "")
	var wname: String = GameState.weather.weather_name()
	var wmark := "☀" if wname == "晴" else ("◐" if wname == "曇" else ("☂" if wname == "雨" else "❄"))
	var seas := WeatherRef.season_of(GameState.month)
	var sname: String = WeatherRef.SEASON_NAMES[seas]
	_hud_top.text = "%s　%d 年 %d 月 %d 日（%s）　所在：%s%s　体力 %d/%d　天气 %s%s" % [
		name_s, GameState.year, GameState.month, GameState.day, sname, loc, sp,
		int(st.get("stamina", 0)), int(st.get("stamina_max", 100)), wmark, wname,
	]
	if _entered_castle >= 0:
		_hud_bottom.text = "Esc 返回大地图"
	elif _town_list:
		_hud_bottom.text = "城町一览表（↑↓ 选择，Enter 自动前往，T/Esc 关闭）"
	elif not _sea_menu.is_empty():
		_hud_bottom.text = _sea_hint()
	elif _move_target != Vector2.INF:
		_hud_bottom.text = "正在移动…（Esc 停止）"
	elif _nearest_id >= 0:
		var near_name: String = GameData.get_castle(_nearest_id).get("name", "")
		var extra := ""
		if GameState.nearest_port() >= 0:
			extra = "　·　B 坐船"
		_hud_bottom.text = "点击/T 城町一览移动　·　Enter 进入 %s%s　·　Esc 回状态画面" % [near_name, extra]
	else:
		_hud_bottom.text = "点击/T 城町一览移动　·　Esc 回状态画面"


func _sea_hint() -> String:
	var items := []
	for i in range(_sea_menu.size()):
		var r: Dictionary = _sea_menu[i]
		var mark := "▶" if i == _sea_sel else " "
		items.append("%s%d.%s（%d日）" % [mark, i + 1, GameData.get_castle(int(r["to"])).get("name", ""), int(r["days"])])
	return "坐船：%s　（↑↓ 选择，Enter 乘船，B/Esc 关闭）" % "　".join(items)


func _move_speed() -> float:
	## 天气影响行走节奏（雨雪变慢，豪雨機動力が鈍る）
	return 1.6 if GameState.weather.get_weather() >= WeatherRef.RAIN else 1.0


func _process(delta: float) -> void:
	_update_cam(delta)
	# 走路动画
	if _move_target != Vector2.INF and _entered_castle < 0:
		_walk_timer += delta
		if _walk_timer >= WALK_FRAME_TICK:
			_walk_timer = 0.0
			_walk_frame ^= 1
	else:
		_walk_frame = 0
	if _move_target == Vector2.INF or _entered_castle >= 0:
		return
	_move_timer -= delta
	if _move_timer > 0.0:
		return
	_move_timer = MOVE_TICK * _move_speed()
	var before: Vector2 = GameState.player_map_pos
	var arrived: bool = GameState.move_player_towards(_move_target)
	var diff := GameState.player_map_pos - before
	if diff.length() > 0.01:
		_face = diff.normalized()
	_update_nearest()
	_refresh_hud()
	queue_redraw()
	if arrived:
		_move_target = Vector2.INF


## 逻辑坐标 → 屏幕坐标（含镜头偏移与聚焦倍率）
func _scr(ms: Vector2, lp: Vector2) -> Vector2:
	return WorldMapRef.project(lp, ms.x, ms.y, MAP_VIEW) * CAM_ZOOM - _cam


## 镜头平滑跟随玩家（原版相机逐格平移质感）
func _update_cam(delta: float) -> void:
	var ms := GameData.get_map_size()
	var p: Vector2 = WorldMapRef.project(GameState.player_map_pos, ms.x, ms.y, MAP_VIEW) * CAM_ZOOM
	var full_w: float = MAP_VIEW.size.x * CAM_ZOOM
	var full_h: float = MAP_VIEW.size.y * CAM_ZOOM
	_cam_target = Vector2(
		clampf(p.x - MAP_VIEW.size.x / 2.0, 0, full_w - MAP_VIEW.size.x),
		clampf(p.y - MAP_VIEW.size.y / 2.0, 0, full_h - MAP_VIEW.size.y))
	_cam = _cam.lerp(_cam_target, minf(1.0, delta * 8.0))


## 镜头瞬移到玩家（开局 / 乘船跨海后）
func _snap_cam() -> void:
	var ms := GameData.get_map_size()
	var p: Vector2 = WorldMapRef.project(GameState.player_map_pos, ms.x, ms.y, MAP_VIEW) * CAM_ZOOM
	var full_w: float = MAP_VIEW.size.x * CAM_ZOOM
	var full_h: float = MAP_VIEW.size.y * CAM_ZOOM
	_cam_target = Vector2(
		clampf(p.x - MAP_VIEW.size.x / 2.0, 0, full_w - MAP_VIEW.size.x),
		clampf(p.y - MAP_VIEW.size.y / 2.0, 0, full_h - MAP_VIEW.size.y))
	_cam = _cam_target


func _update_nearest() -> void:
	_nearest_id = WorldMapRef.nearest(GameState.player_map_pos, GameData.get_castle_positions()) if GameData.has_castle_map() else -1


func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		accept_event()
		if _entered_castle >= 0 or not _sea_menu.is_empty() or _town_list:
			return
		var target := WorldMapRef.unproject((event.position + _cam) / CAM_ZOOM, GameData.get_map_size().x, GameData.get_map_size().y, MAP_VIEW)
		target = WorldMapRef.clamp_pos(target, GameData.get_map_size().x, GameData.get_map_size().y)
		_move_target = target
		_move_timer = 0.0
		_msg = ""
		_refresh_hud()
		return
	if event is InputEventKey:
		var ek := event as InputEventKey
		if ek.pressed and not ek.echo:
			match ek.keycode:
				KEY_ESCAPE:
					accept_event()
					if _entered_castle >= 0 or _castle_town != null:
						_exit_castle()
					elif _town_list:
						_town_list = false
						_refresh_hud()
					elif not _sea_menu.is_empty():
						_sea_menu = []
						_refresh_hud()
					elif _move_target != Vector2.INF:
						_move_target = Vector2.INF
						_refresh_hud()
					else:
						get_tree().change_scene_to_file("res://scenes/screens/status_screen.tscn")
					return
				KEY_ENTER, KEY_KP_ENTER, KEY_SPACE:
					accept_event()
					if _entered_castle < 0 and _town_list:
						_travel_to_selected_town()
					elif _entered_castle < 0 and not _sea_menu.is_empty():
						_travel_selected()
					elif _entered_castle < 0 and _nearest_id >= 0 and _sea_menu.is_empty():
						_enter_castle(_nearest_id)
					return
				KEY_T:
					accept_event()
					if _entered_castle < 0 and _sea_menu.is_empty():
						_town_list = not _town_list
						if _town_list:
							_move_target = Vector2.INF
						_refresh_hud()
					return
				KEY_B:
					accept_event()
					if _entered_castle < 0 and _sea_menu.is_empty() and not _town_list:
						_toggle_sea_menu()
					return
				KEY_UP, KEY_W:
					if _town_list:
						accept_event(); _tl_sel = maxi(0, _tl_sel - 1); _clamp_tl_scroll()
					elif not _sea_menu.is_empty():
						accept_event(); _sea_sel = (_sea_sel - 1 + _sea_menu.size()) % _sea_menu.size(); _refresh_hud()
					else:
						_move_target = Vector2.INF
						_move(0, -1)
				KEY_DOWN, KEY_S:
					if _town_list:
						accept_event(); _tl_sel = mini(_tl_items.size() - 1, _tl_sel + 1); _clamp_tl_scroll()
					elif not _sea_menu.is_empty():
						accept_event(); _sea_sel = (_sea_sel + 1) % _sea_menu.size(); _refresh_hud()
					else:
						_move_target = Vector2.INF
						_move(0, 1)
				KEY_LEFT, KEY_A:
					_move_target = Vector2.INF
					_move(-1, 0)
				KEY_RIGHT, KEY_D:
					_move_target = Vector2.INF
					_move(1, 0)


func _clamp_tl_scroll() -> void:
	# 一览表可视 12 行
	var page := 12
	if _tl_sel < _tl_scroll:
		_tl_scroll = _tl_sel
	elif _tl_sel >= _tl_scroll + page:
		_tl_scroll = _tl_sel - page + 1
	_refresh_hud()


func _travel_to_selected_town() -> void:
	if _tl_items.is_empty():
		return
	var row: Dictionary = _tl_items[_tl_sel]
	var pos: Vector2 = GameData.get_castle_pos(int(row["id"]))
	_move_target = pos
	_town_list = false
	_move_timer = 0.0
	_refresh_hud()


func _move(dx: int, dy: int) -> void:
	if _entered_castle >= 0:
		return
	var before: Vector2 = GameState.player_map_pos
	GameState.move_player(dx, dy)
	var diff := GameState.player_map_pos - before
	if diff.length() > 0.01:
		_face = diff.normalized()
	_walk_frame = 1
	_update_nearest()
	_refresh_hud()
	queue_redraw()


func _toggle_sea_menu() -> void:
	var port_id := GameState.nearest_port()
	if port_id < 0:
		return
	var routes: Array = GameData.get_sea_routes_from(port_id)
	if routes.is_empty():
		return
	_sea_menu = []
	for r in routes:
		_sea_menu.append({"to": int(r["to"]), "days": int(r["days"])})
	_sea_sel = 0
	_refresh_hud()


func _travel_selected() -> void:
	var r: Dictionary = _sea_menu[_sea_sel]
	var res: Dictionary = GameState.travel_by_sea(int(r["to"]))
	if res.get("ok", false):
		_msg = "乘船 %d 日到达 %s（体力降至 20）" % [int(res["days"]), GameData.get_castle(int(r["to"])).get("name", "")]
		_sea_menu = []
		_move_target = Vector2.INF
		_update_nearest()
		_snap_cam()
	else:
		_msg = "无法乘船：%s" % str(res.get("reason", ""))
	_refresh_hud()
	queue_redraw()


func _enter_castle(cid: int) -> void:
	GameState.enter_castle(cid)
	_entered_castle = cid
	_move_target = Vector2.INF
	if _castle_town == null:
		_castle_town = CastleTown.new()
		_castle_town.castle_id = cid
		_castle_town.callback_exit = _exit_castle
		add_child(_castle_town)
	_refresh_hud()
	queue_redraw()


func _exit_castle() -> void:
	if _castle_town != null:
		_castle_town.queue_free()
		_castle_town = null
	_entered_castle = -1
	GameState.leave_to_world()
	_update_nearest()
	_refresh_hud()
	queue_redraw()


func _lord_name(lord_id: int) -> String:
	if lord_id >= 65535 or lord_id < 0:
		return "无"
	var o: Dictionary = GameData.get_officer(lord_id)
	if o.is_empty():
		return "无(%d)" % lord_id
	return str(o.get("surname", "")) + str(o.get("given", ""))


# =====================================================================
# 绘制（原版像素风）
# =====================================================================

func _draw() -> void:
	if not GameData.has_castle_map():
		return
	var ms := GameData.get_map_size()
	var positions: Dictionary = GameData.get_castle_positions()
	_draw_sea(ms)
	_draw_japan_bg(ms)
	_draw_roads(ms)
	_draw_mountains(ms)
	_draw_castles(ms, positions)
	_draw_player(ms)
	if not _sea_menu.is_empty():
		_draw_sea_menu(ms)
	if _town_list:
		_draw_town_list(ms)
	if _msg != "":
		draw_string(UiTheme.font(), Vector2(60, HUD_TOP + 48), _msg, HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_BODY, Color(1.0, 0.9, 0.6, 1))
	_draw_weather_fx(ms)
	if _entered_castle >= 0 and _castle_town == null:
		_draw_castle_overlay(GameData.get_castle(_entered_castle))


func _season() -> int:
	return WeatherRef.season_of(GameState.month)


func _draw_sea(ms: Vector2) -> void:
	# 海洋底色（原版蓝海）
	var sea: Color = SEA_COLORS[_season()]
	draw_rect(MAP_VIEW, sea)
	# 波纹：几条水平淡线
	var off: float = fmod(Time.get_ticks_msec() / 900.0, 40.0)
	for i in range(14):
		var y: float = MAP_VIEW.position.y + 40 + i * 72 + off
		if y > MAP_VIEW.end.y - 20:
			y = MAP_VIEW.position.y + 20 + i * 72 + off
		draw_line(Vector2(MAP_VIEW.position.x, y), Vector2(MAP_VIEW.end.x, y), SEA_RIPPLE, 2.0)


func _draw_japan_bg(ms: Vector2) -> void:
	# 注：不做顶点裁剪（会破坏环完整性导致 triangulation failed），
	# 整环绘制，视口外部分由 canvas 自动裁剪
	var polys: Array = JapanMap.polygons()
	var land: Color = LAND_COLORS[_season()]
	for i in range(polys.size()):
		var pts := polys[i] as PackedVector2Array
		var scr := PackedVector2Array()
		for p in pts:
			scr.append(_scr(ms, p))
		draw_colored_polygon(scr, land)
		draw_polyline(scr + PackedVector2Array([scr[0]]), LAND_EDGE, 3.0)


func _draw_roads(ms: Vector2) -> void:
	var view := MAP_VIEW.grow(30)
	for e in _roads:
		var a: Vector2 = _scr(ms, e[0])
		var b: Vector2 = _scr(ms, e[1])
		if not (view.has_point(a) or view.has_point(b)):
			continue
		draw_line(a, b, ROAD_COLOR, 3.0)


func _draw_mountains(ms: Vector2) -> void:
	var land_dark := Color(0.30, 0.24, 0.18, 1)
	var view := MAP_VIEW.grow(40)
	for m in JapanMap.mountains():
		var lp: Vector2 = JapanMap.mountain_pos(m)
		var sp: Vector2 = _scr(ms, lp)
		if not view.has_point(sp):
			continue
		var w: float = 19.0
		var h: float = 22.0
		draw_colored_polygon(PackedVector2Array([sp + Vector2(-w, h * 0.4), sp + Vector2(0, -h), sp + Vector2(w, h * 0.4)]), land_dark)
		draw_colored_polygon(PackedVector2Array([sp + Vector2(-w, h * 0.4), sp + Vector2(0, -h), sp + Vector2(w, h * 0.4)]), Color(1, 1, 1, 0.22))


func _draw_castles(ms: Vector2, positions: Dictionary) -> void:
	var drawn_names: Array = []   # [Rect2] 已绘城名包围盒（避让用）
	var view := MAP_VIEW.grow(60)
	var font_sz: float = UiTheme.FONT_SMALL * 1.65
	for id in positions.keys():
		var lp: Vector2 = positions[id]
		var sp: Vector2 = _scr(ms, lp)
		var near: bool = (id == _nearest_id)
		var cid := int(id)
		var has_town: bool = GameData.get_castle_has_town(cid)
		var is_port: bool = GameData.is_port_city(cid)
		if not view.has_point(sp):
			continue
		var col: Color
		var size: float
		if near:
			col = NEAR_COLOR
			size = 10.0
		elif is_port:
			col = PORT_COLOR
			size = 8.0
		elif has_town:
			col = TOWN_COLOR
			size = 8.0
		else:
			col = MIL_COLOR
			size = 4.5
		# 城点：町城/港町方块，军事城小点
		if has_town or is_port or near:
			draw_rect(Rect2(sp - Vector2(size, size), Vector2(size * 2, size * 2)), col)
		else:
			draw_circle(sp, size, col)
		# 城名：町城 / 港町 / 最近城（简单避让：右侧 → 上方 → 下方 → 跳过）
		if near or has_town or is_port:
			var cname: String = str(GameData.get_castle(cid).get("name", ""))
			var name_w: float = float(cname.length()) * font_sz * 0.62
			var cand := [
				Rect2(sp + Vector2(size + 3, 8), Vector2(name_w, 34)),
				Rect2(sp + Vector2(-name_w * 0.4, -size - 28), Vector2(name_w, 34)),
				Rect2(sp + Vector2(-name_w * 0.4, size + 26), Vector2(name_w, 34)),
			]
			var placed := false
			for cand_rect in cand:
				var clash := false
				for r in drawn_names:
					if r.intersects(cand_rect):
						clash = true
						break
				if not clash:
					draw_string(UiTheme.font(), cand_rect.position + Vector2(0, 27), cname, HORIZONTAL_ALIGNMENT_LEFT, -1, font_sz, col)
					drawn_names.append(cand_rect)
					placed = true
					break
			if not placed and near:
				# 最近城必须显示：强制画在点上方并登记
				var forced := Rect2(sp + Vector2(-name_w * 0.4, -size - 28), Vector2(name_w, 34))
				draw_string(UiTheme.font(), forced.position + Vector2(0, 27), cname, HORIZONTAL_ALIGNMENT_LEFT, -1, font_sz, col)
				drawn_names.append(forced)
		# 港町锚标（小三角）
		if is_port and not near:
			draw_colored_polygon(PackedVector2Array([
				sp + Vector2(0, 12), sp + Vector2(5, 21), sp + Vector2(-5, 21),
			]), PORT_COLOR)


func _draw_player(ms: Vector2) -> void:
	var psp: Vector2 = _scr(ms, GameState.player_map_pos)
	_draw_pixel_samurai(psp, _face, _walk_frame)


## 像素武士小人（16×20 逻辑像素，4 朝向 + 2 走路帧；随镜头放大）
func _draw_pixel_samurai(center: Vector2, face: Vector2, frame: int) -> void:
	draw_set_transform(center, 0.0, Vector2(CAM_ZOOM, CAM_ZOOM))
	var skin := Color(0.92, 0.78, 0.62, 1)
	var hair := Color(0.16, 0.13, 0.11, 1)
	var robe := Color(0.20, 0.26, 0.36, 1)      # 藏青和服
	var belt := Color(0.90, 0.86, 0.78, 1)
	var pant := Color(0.24, 0.22, 0.20, 1)
	var accent := Color(0.78, 0.24, 0.18, 1)    # 朱红点缀
	var x := center.x - 8.0
	var y := center.y - 9.0
	var flip := face.x < -0.1
	var horiz: bool = abs(face.x) > abs(face.y)

	if horiz:
		# 侧面：窄胴 + 单髻
		draw_rect(Rect2(x + (3 if flip else 5), y, 8, 6), skin)          # 头
		draw_rect(Rect2(x + (2 if flip else 4), y - 3, 4, 4), hair)      # 髻
		draw_rect(Rect2(x + (2 if flip else 3), y + 6, 10, 8), robe)     # 胴
		draw_rect(Rect2(x + (1 if flip else 2), y + 7, 11, 2), belt)     # 腰带
		if frame == 0:
			draw_rect(Rect2(x + (3 if flip else 5), y + 14, 3, 5), pant)
			draw_rect(Rect2(x + (7 if flip else 9), y + 14, 3, 5), pant)
		else:
			draw_rect(Rect2(x + (1 if flip else 3), y + 14, 3, 5), pant)
			draw_rect(Rect2(x + (9 if flip else 11), y + 14, 3, 5), pant)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		return
	# 正面（下）/背面（上）
	var back: bool = face.y < -0.1
	draw_rect(Rect2(x + 4, y, 8, 7), hair if back else skin)            # 头
	draw_rect(Rect2(x + 5, y - 3, 6, 4), hair)                           # 髻
	if not back:
		draw_rect(Rect2(x + 5, y + 1, 3, 3), skin)                       # 髻下前发
	draw_rect(Rect2(x + 2, y + 7, 12, 9), robe)                          # 胴
	draw_rect(Rect2(x + 1, y + 8, 14, 2), belt)                          # 腰带
	draw_rect(Rect2(x + 5, y + 12, 6, 2), accent)                        # 肩带/饰
	if frame == 0:
		draw_rect(Rect2(x + 3, y + 16, 4, 5), pant)
		draw_rect(Rect2(x + 9, y + 16, 4, 5), pant)
	else:
		draw_rect(Rect2(x + 1, y + 16, 4, 5), pant)
		draw_rect(Rect2(x + 11, y + 16, 4, 5), pant)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)


func _draw_weather_fx(ms: Vector2) -> void:
	var w: int = GameState.weather.get_weather()
	if w == WeatherRef.RAIN:
		# 雨：细斜线帘幕（随时间流动，原版雨丝感）
		var t: float = fmod(Time.get_ticks_msec() / 60.0, 48.0)
		var col := Color(0.60, 0.75, 0.92, 0.20)
		for sx in range(-80, 2000, 48):
			var x0 := float(sx) - t
			draw_line(Vector2(x0, MAP_VIEW.position.y), Vector2(x0 - 22, MAP_VIEW.end.y), col, 1.5)
		# 顶部暗化
		draw_rect(Rect2(MAP_VIEW.position, Vector2(1920, 30)), Color(0.1, 0.15, 0.25, 0.22))
	elif w == WeatherRef.SNOW:
		# 雪：白点飘落（确定性伪随机位置）
		var t: float = Time.get_ticks_msec() / 5000.0
		for i in range(46):
			var sx: float = fmod(float(i * 137 + 53), 1920.0)
			var sy: float = fmod(float(i * 89 + 31) + t * 34.0, 960.0) + MAP_VIEW.position.y
			draw_circle(Vector2(sx, sy), 1.6, Color(1, 1, 1, 0.6))
	elif w == WeatherRef.CLOUDY:
		# 阴：顶部轻灰
		draw_rect(Rect2(MAP_VIEW.position, Vector2(1920, 22)), Color(0.6, 0.62, 0.66, 0.18))


func _draw_sea_menu(ms: Vector2) -> void:
	var panel := Rect2(560, 300, 800, 60 + _sea_menu.size() * 52)
	draw_rect(panel, Color(0.08, 0.10, 0.12, 0.96))
	draw_rect(panel, Color(0.42, 0.80, 0.95, 0.9), false, 2)
	var y: float = panel.position.y + 40
	draw_string(UiTheme.font(), Vector2(panel.position.x + 30, y - 12), "【%s · 坐船】" % GameData.get_castle(GameState.nearest_port()).get("name", ""),
		HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_BODY, Color(0.42, 0.80, 0.95, 1))
	for i in range(_sea_menu.size()):
		var r: Dictionary = _sea_menu[i]
		var line := "%d. %s（%d 日）" % [i + 1, GameData.get_castle(int(r["to"])).get("name", ""), int(r["days"])]
		if i == _sea_sel:
			line = "▶ " + line
			draw_string(UiTheme.font(), Vector2(panel.position.x + 30, y), line, HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_BODY, Color(1.0, 0.9, 0.5, 1))
		else:
			draw_string(UiTheme.font(), Vector2(panel.position.x + 30, y), line, HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_BODY, UiTheme.C_TEXT)
		y += 52


func _draw_town_list(ms: Vector2) -> void:
	var panel := Rect2(560, 120, 800, 820)
	draw_rect(panel, Color(0.09, 0.11, 0.13, 0.97))
	draw_rect(panel, Color(0.78, 0.63, 0.35, 1), false, 2)
	draw_string(UiTheme.font(), Vector2(panel.position.x + 30, panel.position.y + 36), "【城町一览表】",
		HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_BODY, Color(0.92, 0.80, 0.50, 1))
	var page := 12
	var y: float = panel.position.y + 70
	var cur_prov := -1
	for i in range(_tl_scroll, mini(_tl_items.size(), _tl_scroll + page)):
		var row: Dictionary = _tl_items[i]
		var prov: int = int(row["prov"])
		var prov_name: String = str(GameData.get_province(prov).get("name", "")) if GameData.get_province(prov).size() > 0 else "—"
		if prov != cur_prov:
			cur_prov = prov
			draw_string(UiTheme.font(), Vector2(panel.position.x + 30, y), "◆ %s" % prov_name,
				HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_SMALL, Color(0.72, 0.68, 0.58, 1))
			y += 30
		var line := "%s　%s" % [str(row["name"]), prov_name]
		if i == _tl_sel:
			draw_string(UiTheme.font(), Vector2(panel.position.x + 30, y), "▶ " + str(row["name"]),
				HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_BODY, Color(1.0, 0.9, 0.5, 1))
		else:
			draw_string(UiTheme.font(), Vector2(panel.position.x + 30, y), str(row["name"]),
				HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_BODY, UiTheme.C_TEXT)
		y += 34
	if _tl_items.size() > page:
		draw_string(UiTheme.font(), Vector2(panel.position.x + 600, panel.position.y + 36),
			"%d/%d" % [_tl_sel + 1, _tl_items.size()], HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_SMALL, Color(0.7, 0.7, 0.7, 1))


func _draw_castle_overlay(c: Dictionary) -> void:
	var pid: int = int(c.get("province", 255))
	var p: Dictionary = GameData.get_province(pid)
	var panel := Rect2(430, 280, 1060, 460)
	draw_rect(panel, Color(0.10, 0.07, 0.05, 0.96))
	draw_rect(panel, Color(0.78, 0.63, 0.35, 1), false, 3)
	var lines := PackedStringArray([
		"【%s】" % str(c.get("name", "")),
		"国：%s" % str(p.get("name", "") if not p.is_empty() else "—"),
		"城主：%s" % _lord_name(int(c.get("f0a", 65535))),
		"兵力 %d　米 %d　金 %d" % [int(c.get("gunryo", 0)), int(c.get("kome", 0)), int(c.get("shikin", 0))],
		"農 %d　商 %d　石高 %d" % [int(c.get("nousang", 0)), int(c.get("minkok", 0)), int(c.get("seisan", 0))],
		"",
		"（城下町设施已接入 castle_town.gd；剧情推进待实现）",
	])
	var y: float = panel.position.y + 44
	for ln in lines:
		draw_string(UiTheme.font(), Vector2(panel.position.x + 44, y), ln, HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_BODY, UiTheme.C_TEXT)
		y += 56
