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
const WorldTerrain = preload("res://src/core/world_terrain.gd")
const World3DMap = preload("res://src/ui/world3d_map.gd")

const HUD_TOP := 64.0
const HUD_BOTTOM := 56.0
const MAP_VIEW := Rect2(0, HUD_TOP, 1920, 1080 - HUD_TOP - HUD_BOTTOM)
const MOVE_TICK := 0.25            # 自动移动每格间隔（秒；雨雪天 ×1.6 变慢）
const WALK_FRAME_TICK := 0.12      # 走路动画帧切换
const CAM_ZOOM := 4.5              # 区域视野（拉近：约 10.7×5.3 格，聚焦玩家附近 2–4 城）

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
const ROAD_COLOR := Color(0.78, 0.68, 0.50, 0.8)   # 太阁5 土路色
# 动态细节（太阁5 手绘元素：树丛 / 建筑群 / 名山雪山）
const FOREST_TREE_COL := [
	Color(0.30, 0.38, 0.32), Color(0.28, 0.40, 0.22), Color(0.22, 0.32, 0.16), Color(0.34, 0.30, 0.18),
]
const FOREST_HL := Color(0.62, 0.78, 0.46, 0.85)
const FOREST_LIGHT := [
	Color(0.42, 0.52, 0.42), Color(0.38, 0.54, 0.30), Color(0.30, 0.44, 0.24), Color(0.48, 0.42, 0.26),
]
const ROOF_COLS := [
	Color(0.59, 0.31, 0.24), Color(0.43, 0.47, 0.59), Color(0.35, 0.37, 0.39), Color(0.55, 0.47, 0.31),
]

# 太阁5 手绘风底图色（季节）
const LAND_GRASS := [
	Color(0.58, 0.66, 0.58, 1),   # 冬 枯灰绿
	Color(0.66, 0.74, 0.46, 1),   # 春 新绿
	Color(0.52, 0.64, 0.36, 1),   # 夏 深绿
	Color(0.66, 0.56, 0.34, 1),   # 秋 枯黄
]
const LAND_FOREST := [
	Color(0.40, 0.48, 0.42, 1),
	Color(0.40, 0.50, 0.30, 1),
	Color(0.32, 0.42, 0.24, 1),
	Color(0.46, 0.40, 0.26, 1),
]
const BEACH_COLOR := Color(0.87, 0.80, 0.62, 1)
const SNOW_COLOR := Color(0.94, 0.95, 0.93, 1)
const TOWN_STONE := Color(0.55, 0.52, 0.48, 1)
const BG_SCALE := 10.0             # 底图放大倍率（256→2560 像素）
const BG_FILES := ["winter", "spring", "summer", "autumn"]
const ROOF_RED := Color(0.62, 0.22, 0.16, 1)
const ROOF_BLUE := Color(0.24, 0.34, 0.52, 1)
const ROOF_BROWN := Color(0.46, 0.34, 0.20, 1)
const WALL_COLOR := Color(0.86, 0.80, 0.66, 1)
const KEEP_WHITE := Color(0.92, 0.90, 0.86, 1)
const FORT_WOOD := Color(0.48, 0.36, 0.22, 1)

# 城点样式（原版：町城红块 / 军事城白点 / 港町白块+锚）
const TOWN_COLOR := Color(0.78, 0.24, 0.18, 1)
const MIL_COLOR := Color(0.86, 0.88, 0.90, 0.9)
const PORT_COLOR := Color(0.55, 0.85, 1.0, 1)
const NEAR_COLOR := Color(1.0, 0.92, 0.45, 1)

var _hud_top: CanvasItem
var _hud_bottom: CanvasItem
var _entered_castle: int = -1      # 进城 overlay 中显示的城 id（-1=未进城）
var _nearest_id: int = -1
# AI 生成素材图标（assets/icons/，白底 floodfill 抠图）
var _icon_castle: ImageTexture = null
var _icon_fort: ImageTexture = null
var _icon_village: ImageTexture = null
var _icon_peak: ImageTexture = null
var _icon_hill: ImageTexture = null
var _icon_great: ImageTexture = null
var _icon_port: ImageTexture = null
# BFS 陆地路径（点击目标后生成，沿路径逐格走，不穿海）
var _path := PackedVector2Array()
var _path_idx := 0
var _castle_town: Control = null   # 城下町交互 UI（进城时挂载，离城时置 null）

var _move_target: Vector2 = Vector2.INF   # 点击自动移动目标（INF=未在移动）
var _move_timer: float = 0.0
# 平滑行走插值（消除跳格感）
var _draw_pos: Vector2 = Vector2.ZERO   # 画面显示位置（平滑）
var _move_from: Vector2 = Vector2.ZERO  # 本格起点
var _move_to: Vector2 = Vector2.ZERO    # 本格终点
var _move_prog := 1.0                   # 0..1 格内进度（1=静止）
var _cam := Vector2.ZERO            # 镜头左上角（全图屏幕像素坐标）
var _cam_target := Vector2.ZERO
var _bg_tex: ImageTexture = null   # 手绘风底图（季节缓存）
var _bg_season := -1
var _minimap_tex: ImageTexture = null
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
var _view3d: SubViewport = null        # HD-2D 3D 地形层视口
var _world3d = null                    # world3d_map.gd 实例
var _click_cam := false                # 3D 视角点击（映射目标）


func _ready() -> void:
	_icon_castle = _load_icon("castle")
	_icon_fort = _load_icon("fort")
	_icon_village = _load_icon("village")
	_icon_peak = _load_icon("peak")
	_icon_hill = _load_icon("hill")
	_icon_great = _load_icon("great")
	_icon_port = _load_icon("port")
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
	_build_3d_layer()
	_set_initial_pos()
	_build_roads()
	_build_town_list()
	_update_nearest()
	_refresh_hud()
	_snap_cam()
	queue_redraw()


func _build_3d_layer() -> void:
	## HD-2D 3D 地形层：SubViewport 内渲染 world3d_map（3D 地形 + 城标 + 像素武士 + 跟随相机）
	_view3d = SubViewport.new()
	_view3d.size = Vector2i(int(MAP_VIEW.size.x), int(MAP_VIEW.size.y))
	_view3d.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_view3d.own_world_3d = true
	_view3d.msaa_3d = Viewport.MSAA_4X
	add_child(_view3d)
	_world3d = World3DMap.new()
	_world3d.viewport = _view3d
	_view3d.add_child(_world3d)
	_world3d.setup()


func _set_initial_pos() -> void:
	# 若主角尚未落点（开局），放到其所在/默认城坐标
	if _gs().player_map_pos == Vector2.ZERO and _gd().has_castle_map():
		var home: int = 0 if _gs().current_castle < 0 else _gs().current_castle
		_gs().player_map_pos = _gd().get_castle_pos(home)


func _gs() -> Node:
	## autoload 兼容访问（--script 无头模式不注册全局标识符）
	return get_node("/root/GameState")


func _gd() -> Node:
	return get_node("/root/GameData")


func _make_label() -> CanvasItem:
	var l = UiLabel.new()
	l.font_size = UiTheme.FONT_BODY
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func _build_roads() -> void:
	## 道路网：同国最近 2 城连线（无向边，跨海自动断开——四国/九州不走陆路）
	if not _gd().has_castle_map():
		return
	var positions: Dictionary = _gd().get_castle_positions()
	var edges := {}
	for id in positions.keys():
		var prov: int = int(_gd().get_castle(int(id)).get("province", 255))
		var mine: Vector2 = positions[id]
		var cands := []
		for j in positions.keys():
			if j == id:
				continue
			if int(_gd().get_castle(int(j)).get("province", 255)) != prov:
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
	for id in _gd().get_castle_positions().keys():
		var cid := int(id)
		if _gd().get_castle_has_town(cid) or _gd().is_port_city(cid):
			var c: Dictionary = _gd().get_castle(cid)
			rows.append({"id": cid, "name": str(c.get("name", "")), "prov": int(c.get("province", 255))})
	rows.sort_custom(func(a, b):
		var pa: int = int(a["prov"])
		var pb: int = int(b["prov"])
		if pa != pb:
			return pa < pb
		return str(a["name"]) < str(b["name"]))
	_tl_items = rows


func _refresh_hud() -> void:
	var st: Dictionary = _gs().get_status()
	var name_s: String = str(st.get("name", "")) if not st.is_empty() else ""
	var loc := "野外"
	if _entered_castle >= 0:
		loc = "【城下】" + str(_gd().get_castle(_entered_castle).get("name", ""))
	elif _gs().current_castle >= 0:
		loc = str(_gd().get_castle(_gs().current_castle).get("name", ""))
	var sp := ""
	var port_id: int = _gs().nearest_port()
	if port_id >= 0:
		sp = "（港町 %s）" % _gd().get_castle(port_id).get("name", "")
	var wname: String = _gs().weather.weather_name()
	var wmark := "☀" if wname == "晴" else ("◐" if wname == "曇" else ("☂" if wname == "雨" else "❄"))
	var seas: int = WeatherRef.season_of(_gs().month)
	var sname: String = WeatherRef.SEASON_NAMES[seas]
	_hud_top.text = "%s　%d 年 %d 月 %d 日（%s）　所在：%s%s　体力 %d/%d　天气 %s%s" % [
		name_s, _gs().year, _gs().month, _gs().day, sname, loc, sp,
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
		var near_name: String = _gd().get_castle(_nearest_id).get("name", "")
		var extra := ""
		if _gs().nearest_port() >= 0:
			extra = "　·　B 坐船"
		_hud_bottom.text = "点击/T 城町一览移动　·　Enter 进入 %s%s　·　Esc 回状态画面" % [near_name, extra]
	else:
		_hud_bottom.text = "点击/T 城町一览移动　·　Esc 回状态画面"


func _sea_hint() -> String:
	var items := []
	for i in range(_sea_menu.size()):
		var r: Dictionary = _sea_menu[i]
		var mark := "▶" if i == _sea_sel else " "
		items.append("%s%d.%s（%d日）" % [mark, i + 1, _gd().get_castle(int(r["to"])).get("name", ""), int(r["days"])])
	return "坐船：%s　（↑↓ 选择，Enter 乘船，B/Esc 关闭）" % "　".join(items)


## 停止自动移动（清路径）
func _stop_move() -> void:
	_move_target = Vector2.INF
	_path = PackedVector2Array()
	_path_idx = 0
	_move_from = _gs().player_map_pos
	_move_to = _gs().player_map_pos
	_move_prog = 1.0


## 开始自动移动：BFS 陆地寻路 → 路径逐格行走
func _begin_move(target: Vector2) -> void:
	var ms: Vector2 = _gd().get_map_size()
	_path = WorldMapRef.find_path(_gs().player_map_pos, target, ms.x, ms.y, WorldTerrain.type_at)
	_path_idx = 0
	_move_target = target
	_move_timer = 0.0
	_move_from = _gs().player_map_pos
	_move_to = _gs().player_map_pos
	_move_prog = 0.0
	_msg = ""
	_refresh_hud()
	queue_redraw()


func _move_speed() -> float:
	## 天气影响行走节奏（雨雪变慢，豪雨機動力が鈍る）
	return 1.6 if _gs().weather.get_weather() >= WeatherRef.RAIN else 1.0


func _process(delta: float) -> void:
	_update_cam(delta)
	if _move_target == Vector2.INF or _entered_castle >= 0:
		_draw_pos = _gs().player_map_pos   # 静止/城内时同步
		_walk_frame = 0
		_sync_3d()
		return
	# 走路动画
	_walk_timer += delta
	if _walk_timer >= WALK_FRAME_TICK:
		_walk_timer = 0.0
		_walk_frame ^= 1
	# 平滑推进本格
	_move_prog += delta / (MOVE_TICK * _move_speed())
	if _move_prog >= 1.0:
		_move_prog = 1.0
		# 沿 BFS 陆地路径走一步（不穿海，贴地形绕行）
		if _path_idx >= _path.size() - 1:
			_stop_move()
			_path = PackedVector2Array()
			_move_prog = 1.0
		else:
			_path_idx += 1
			var np: Vector2 = _path[_path_idx]
			var before: Vector2 = _gs().player_map_pos
			_gs().player_map_pos = np
			_gs().advance_days(_gs().move_days_per_cell())
			var diff := np - before
			if diff.length() > 0.01:
				_face = diff.normalized()
			_move_from = _move_to
			_move_to = np
			_move_prog = 0.0
			_update_nearest()
			_refresh_hud()
			queue_redraw()
	_draw_pos = _move_from.lerp(_move_to, _move_step(_move_prog))
	queue_redraw()
	_sync_3d()


func _sync_3d() -> void:
	## 每帧把玩家/朝向/季节同步到 3D 层
	if _world3d != null:
		_world3d.sync(_draw_pos, _face, _walk_frame, _season())


## 缓动步进（smoothstep：起步慢-中段快-收步缓，行走感）
func _move_step(p: float) -> float:
	return p * p * (3.0 - 2.0 * p)


## 逻辑坐标 → 屏幕坐标（含镜头偏移与聚焦倍率）
func _scr(ms: Vector2, lp: Vector2) -> Vector2:
	return WorldMapRef.project(lp, ms.x, ms.y, MAP_VIEW) * CAM_ZOOM - _cam


## 镜头平滑跟随玩家（原版相机逐格平移质感）
func _update_cam(delta: float) -> void:
	var ms: Vector2 = _gd().get_map_size()
	var p: Vector2 = WorldMapRef.project(_draw_pos, ms.x, ms.y, MAP_VIEW) * CAM_ZOOM
	var full_w: float = MAP_VIEW.size.x * CAM_ZOOM
	var full_h: float = MAP_VIEW.size.y * CAM_ZOOM
	_cam_target = Vector2(
		clampf(p.x - MAP_VIEW.size.x / 2.0, 0, full_w - MAP_VIEW.size.x),
		clampf(p.y - MAP_VIEW.size.y / 2.0, 0, full_h - MAP_VIEW.size.y))
	_cam = _cam.lerp(_cam_target, minf(1.0, delta * 8.0))


## 镜头瞬移到玩家（开局 / 乘船跨海后）
func _snap_cam() -> void:
	var ms: Vector2 = _gd().get_map_size()
	_draw_pos = _gs().player_map_pos
	_move_from = _draw_pos
	_move_to = _draw_pos
	_move_prog = 1.0
	var p: Vector2 = WorldMapRef.project(_draw_pos, ms.x, ms.y, MAP_VIEW) * CAM_ZOOM
	var full_w: float = MAP_VIEW.size.x * CAM_ZOOM
	var full_h: float = MAP_VIEW.size.y * CAM_ZOOM
	_cam_target = Vector2(
		clampf(p.x - MAP_VIEW.size.x / 2.0, 0, full_w - MAP_VIEW.size.x),
		clampf(p.y - MAP_VIEW.size.y / 2.0, 0, full_h - MAP_VIEW.size.y))
	_cam = _cam_target


func _update_nearest() -> void:
	_nearest_id = WorldMapRef.nearest(_gs().player_map_pos, _gd().get_castle_positions()) if _gd().has_castle_map() else -1


func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		accept_event()
		if _entered_castle >= 0 or not _sea_menu.is_empty() or _town_list:
			return
		var target := WorldMapRef.unproject((event.position + _cam) / CAM_ZOOM, _gd().get_map_size().x, _gd().get_map_size().y, MAP_VIEW)
		target = WorldMapRef.clamp_pos(target, _gd().get_map_size().x, _gd().get_map_size().y)
		_begin_move(target)
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
						_stop_move()
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
							_stop_move()
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
						_stop_move()
						_move(0, -1)
				KEY_DOWN, KEY_S:
					if _town_list:
						accept_event(); _tl_sel = mini(_tl_items.size() - 1, _tl_sel + 1); _clamp_tl_scroll()
					elif not _sea_menu.is_empty():
						accept_event(); _sea_sel = (_sea_sel + 1) % _sea_menu.size(); _refresh_hud()
					else:
						_stop_move()
						_move(0, 1)
				KEY_LEFT, KEY_A:
					_stop_move()
					_move(-1, 0)
				KEY_RIGHT, KEY_D:
					_stop_move()
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
	var pos: Vector2 = _gd().get_castle_pos(int(row["id"]))
	_town_list = false
	_begin_move(pos)
	_refresh_hud()


func _move(dx: int, dy: int) -> void:
	if _entered_castle >= 0:
		return
	_stop_move()
	var before: Vector2 = _gs().player_map_pos
	_gs().move_player(dx, dy)
	var diff: Vector2 = _gs().player_map_pos - before
	if diff.length() > 0.01:
		_face = diff.normalized()
	_walk_frame = 1
	_update_nearest()
	_refresh_hud()
	queue_redraw()


func _toggle_sea_menu() -> void:
	var port_id: int = _gs().nearest_port()
	if port_id < 0:
		return
	var routes: Array = _gd().get_sea_routes_from(port_id)
	if routes.is_empty():
		return
	_sea_menu = []
	for r in routes:
		_sea_menu.append({"to": int(r["to"]), "days": int(r["days"])})
	_sea_sel = 0
	_refresh_hud()


func _travel_selected() -> void:
	var r: Dictionary = _sea_menu[_sea_sel]
	var res: Dictionary = _gs().travel_by_sea(int(r["to"]))
	if res.get("ok", false):
		_msg = "乘船 %d 日到达 %s（体力降至 20）" % [int(res["days"]), _gd().get_castle(int(r["to"])).get("name", "")]
		_sea_menu = []
		_stop_move()
		_update_nearest()
		_snap_cam()
	else:
		_msg = "无法乘船：%s" % str(res.get("reason", ""))
	_refresh_hud()
	queue_redraw()


func _enter_castle(cid: int) -> void:
	_gs().enter_castle(cid)
	_entered_castle = cid
	_stop_move()
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
	_gs().leave_to_world()
	_update_nearest()
	_refresh_hud()
	queue_redraw()


func _lord_name(lord_id: int) -> String:
	if lord_id >= 65535 or lord_id < 0:
		return "无"
	var o: Dictionary = _gd().get_officer(lord_id)
	if o.is_empty():
		return "无(%d)" % lord_id
	return str(o.get("surname", "")) + str(o.get("given", ""))


# =====================================================================
# 绘制（原版像素风）
# =====================================================================

func _draw() -> void:
	if not _gd().has_castle_map():
		return
	var ms: Vector2 = _gd().get_map_size()
	# HD-2D 3D 地形层（八方旅人风格：3D 地形 + 城标 + 跟随相机）
	if _view3d != null:
		draw_texture_rect(_view3d.get_texture(), MAP_VIEW, false)
	# 玩家：3D 相机投影到屏幕，2D 叠加绘制（光圈+像素武士+头顶箭头，保证醒目）
	if _world3d != null:
		var psp: Vector2 = _world3d.player_screen_pos()
		if psp.x > -9000:
			var px := psp.x + MAP_VIEW.position.x
			var py := psp.y + MAP_VIEW.position.y
			var pw := 100.0
			var ph := pw * 20.0 / 16.0
			# 脚下光圈
			draw_circle(Vector2(px, py + 4), 36.0, Color(1.0, 0.95, 0.72, 0.32))
			# 像素武士（投影点为脚底基准）
			var ptex: Texture2D = _world3d.player_tex()
			if ptex != null:
				draw_texture_rect(ptex, Rect2(px - pw / 2.0, py - ph + 6.0, pw, ph), false)
			# 头顶黄色箭头（太阁5 式指示）
			draw_colored_polygon(PackedVector2Array([
				Vector2(px, py - ph - 16),
				Vector2(px - 9, py - ph - 3),
				Vector2(px + 9, py - ph - 3),
			]), Color(1.0, 0.85, 0.25, 0.95))
	# 2D 覆盖层（小地图/菜单/天气/消息，城标城名由 3D 层绘制）
	_draw_minimap(ms)
	if not _sea_menu.is_empty():
		_draw_sea_menu(ms)
	if _town_list:
		_draw_town_list(ms)
	if _msg != "":
		draw_string(UiTheme.font(), Vector2(60, HUD_TOP + 48), _msg, HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_BODY, Color(1.0, 0.9, 0.6, 1))
	_draw_weather_fx(ms)
	if _entered_castle >= 0 and _castle_town == null:
		_draw_castle_overlay(_gd().get_castle(_entered_castle))


func _season() -> int:
	return WeatherRef.season_of(_gs().month)


func _draw_sea(ms: Vector2) -> void:
	## 断续波纹线（只画在海面，太阁5 波浪感）
	var t: float = fmod(Time.get_ticks_msec() / 1400.0, 44.0)
	for i in range(24):
		var wy: float = MAP_VIEW.position.y + 26 + i * 40 + t
		if wy > MAP_VIEW.end.y - 14:
			continue
		var xoff: float = fmod(float(i * 71), 110.0)
		var x0 := -40.0 - xoff
		while x0 < MAP_VIEW.size.x:
			var x1 := x0 + 120.0 + fmod(float(i * 37), 60.0)
			var a: bool = _px_is_sea(ms, Vector2(x0, wy))
			var b: bool = _px_is_sea(ms, Vector2(x1, wy))
			if a and b:
				draw_line(Vector2(x0, wy), Vector2(x1, wy), Color(1, 1, 1, 0.13), 2.0)
			x0 = x1 + 26.0 + fmod(float(i * 13), 34.0)


func _draw_bg(ms: Vector2) -> void:
	## 贴图底图（太阁5 手绘风：平滑渐变陆地/山/森林/沙滩/城下町）
	if _bg_tex == null or _bg_season != _season():
		_build_bg_tex()
	var s: float = minf(MAP_VIEW.size.x / ms.x, MAP_VIEW.size.y / ms.y)
	var off := Vector2(
		MAP_VIEW.position.x + (MAP_VIEW.size.x - ms.x * s) * 0.5,
		MAP_VIEW.position.y + (MAP_VIEW.size.y - ms.y * s) * 0.5)
	var scale: float = float(_bg_tex.get_width()) / WorldTerrain.MAP_W
	var lx0 := (_cam.x - off.x * CAM_ZOOM) / (s * CAM_ZOOM)
	var ly0 := (_cam.y - off.y * CAM_ZOOM) / (s * CAM_ZOOM)
	var lw := MAP_VIEW.size.x / (s * CAM_ZOOM)
	var lh := MAP_VIEW.size.y / (s * CAM_ZOOM)
	var src := Rect2(lx0 * scale, ly0 * scale, lw * scale, lh * scale)
	draw_texture_rect_region(_bg_tex, MAP_VIEW, src)


## 屏幕点（MAP_VIEW 内）是否为海（掩码采样）
func _px_is_sea(ms: Vector2, sp: Vector2) -> bool:
	var s: float = minf(MAP_VIEW.size.x / ms.x, MAP_VIEW.size.y / ms.y)
	var off := Vector2(
		MAP_VIEW.position.x + (MAP_VIEW.size.x - ms.x * s) * 0.5,
		MAP_VIEW.position.y + (MAP_VIEW.size.y - ms.y * s) * 0.5)
	var lx := ((sp.x + _cam.x) / CAM_ZOOM - off.x) / s
	var ly := ((sp.y + _cam.y) / CAM_ZOOM - off.y) / s
	return WorldTerrain.type_at(int(lx / WorldTerrain.CELL), int(ly / WorldTerrain.CELL)) == WorldTerrain.SEA


func _build_bg_tex() -> void:
	## 加载预生成太阁5 手绘风底图（scripts/gen_map_bg.py 产出 4 季 1280×960）
	var seas := _season()
	var f := FileAccess.open("res://assets/map_bg_%s.png" % BG_FILES[seas], FileAccess.READ)
	if f == null:
		return
	var img := Image.new()
	img.load_png_from_buffer(f.get_buffer(f.get_length()))
	var small := img.duplicate()
	small.resize(int(WorldTerrain.MAP_W * 2.75), int(WorldTerrain.MAP_H * 2.75), Image.INTERPOLATE_BILINEAR)  # 132×99
	_minimap_tex = ImageTexture.create_from_image(small)
	_bg_tex = ImageTexture.create_from_image(img)
	_bg_season = seas


## 底图像素颜色（手绘风：海渐变 / 山体明暗 / 草地起伏 / 森林斑块 / 沙滩 / 城下町）
func _draw_terrain_detail(ms: Vector2) -> void:
	## 太阁5 手绘细节：森林树丛 / 城下町建筑群 / 名山雪山（屏幕分辨率绘制，清晰）
	var s: float = minf(MAP_VIEW.size.x / ms.x, MAP_VIEW.size.y / ms.y)
	var off := Vector2(
		MAP_VIEW.position.x + (MAP_VIEW.size.x - ms.x * s) * 0.5,
		MAP_VIEW.position.y + (MAP_VIEW.size.y - ms.y * s) * 0.5)
	var lx0 := (_cam.x - off.x * CAM_ZOOM) / (s * CAM_ZOOM)
	var ly0 := (_cam.y - off.y * CAM_ZOOM) / (s * CAM_ZOOM)
	var lw := MAP_VIEW.size.x / (s * CAM_ZOOM)
	var lh := MAP_VIEW.size.y / (s * CAM_ZOOM)
	var rx0 := int(lx0 / WorldTerrain.CELL) - 1
	var ry0 := int(ly0 / WorldTerrain.CELL) - 1
	var rx1 := int((lx0 + lw) / WorldTerrain.CELL) + 1
	var ry1 := int((ly0 + lh) / WorldTerrain.CELL) + 1
	for ry in range(ry0, ry1 + 1):
		for rx in range(rx0, rx1 + 1):
			var t: int = WorldTerrain.type_at(rx, ry)
			if t == WorldTerrain.TOWN:
				_draw_town_cell(rx, ry, ms)
	# 名山：底图已含 3D 雪顶山体，不再叠加 AI 图标


func _draw_forest_cell(rx: int, ry: int, ms: Vector2) -> void:
	## 每森林格 4 棵小树冠（密集树丛感，太阁5 手绘）
	var tcol: Color = FOREST_TREE_COL[_season()]
	var gx := float(rx) + 0.5
	var gy := float(ry) + 0.5
	for k in range(4):
		var hx: float = WorldTerrain._hash01(rx * 3 + k, ry * 5 + k, 7)
		var hy: float = WorldTerrain._hash01(rx * 7 + k, ry * 3 + k, 13)
		var p := Vector2((gx + (hx - 0.5) * 0.9) * WorldTerrain.CELL, (gy + (hy - 0.5) * 0.9) * WorldTerrain.CELL)
		var sp: Vector2 = _scr(ms, p)
		if sp.x < -20 or sp.x > MAP_VIEW.size.x + 20 or sp.y < HUD_TOP - 20 or sp.y > MAP_VIEW.end.y + 20:
			continue
		var r := 3.8 + 1.9 * WorldTerrain._hash01(rx, ry, k)
		var tlight: Color = FOREST_LIGHT[_season()]
		draw_circle(sp, r * 1.25, tlight)                      # 外围浅绿
		draw_circle(sp + Vector2(r * 0.15, r * 0.20), r * 0.78, tcol)  # 深绿偏心树冠
		draw_circle(sp + Vector2(-r * 0.4, -r * 0.45), r * 0.32, FOREST_HL)  # 高光


func _draw_town_cell(rx: int, ry: int, ms: Vector2) -> void:
	## 城下町建筑群：屋顶小方块 + 街道
	var gx := float(rx) + 0.5
	var gy := float(ry) + 0.5
	for k in range(7):
		var hx: float = WorldTerrain._hash01(rx * 11 + k, ry * 13 + k, 29)
		var hy: float = WorldTerrain._hash01(rx * 5 + k, ry * 17 + k, 37)
		var p := Vector2((gx + (hx - 0.5) * 0.9) * WorldTerrain.CELL, (gy + (hy - 0.5) * 0.9) * WorldTerrain.CELL)
		var sp: Vector2 = _scr(ms, p)
		if sp.x < -20 or sp.x > MAP_VIEW.size.x + 20 or sp.y < HUD_TOP - 20 or sp.y > MAP_VIEW.end.y + 20:
			continue
		var sz := 3.0 + WorldTerrain._hash01(rx, ry, k) * 2.0
		var rc: Color = ROOF_COLS[int(WorldTerrain._hash01(rx * 3, ry * 3, k) * 4) % 4]
		draw_rect(Rect2(sp - Vector2(sz, sz) * 0.5, Vector2(sz, sz)), rc)
	# 街道
	var c: Vector2 = _scr(ms, Vector2(gx * WorldTerrain.CELL, gy * WorldTerrain.CELL))
	draw_line(c - Vector2(14, 0), c + Vector2(14, 0), Color(0.85, 0.80, 0.70, 0.5), 2.0)


func _draw_peak(sp: Vector2) -> void:
	## 名山：AI 雪山图标（山脚贴地）
	_draw_icon(_icon_peak, sp + Vector2(0, 30), 150.0)
	# 山脚融入草地的柔和阴影
	draw_set_transform(sp + Vector2(0, 30), 0.0, Vector2(1.0, 0.42))
	draw_circle(Vector2.ZERO, 78.0, Color(0.30, 0.34, 0.22, 0.22))
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
func _draw_minimap(ms: Vector2) -> void:
	## 右上角日本全域缩略图（太阁5：城点 + 视野框 + 玩家）
	if _minimap_tex == null:
		return
	var msize := Vector2(132, 99)
	var mpos := Vector2(1920 - msize.x - 18, 76)
	draw_texture_rect(_minimap_tex, Rect2(mpos, msize), false)
	draw_rect(Rect2(mpos, msize), Color(0.90, 0.84, 0.60, 0.85), false, 2)
	# 城点
	var positions: Dictionary = _gd().get_castle_positions()
	for id in positions.keys():
		var lp: Vector2 = positions[id]
		var cid := int(id)
		var col: Color
		if _gd().is_port_city(cid):
			col = Color(0.55, 0.85, 1.0, 1)
		elif _gd().get_castle_has_town(cid):
			col = Color(0.90, 0.40, 0.30, 1)
		else:
			col = Color(0.85, 0.88, 0.90, 0.8)
		var mp := mpos + Vector2(lp.x / WorldTerrain.MAP_W, lp.y / WorldTerrain.MAP_H) * msize
		draw_rect(Rect2(mp - Vector2(1, 1), Vector2(2.5, 2.5)), col)
	# 视野框
	var s: float = minf(MAP_VIEW.size.x / ms.x, MAP_VIEW.size.y / ms.y)
	var off := Vector2(
		MAP_VIEW.position.x + (MAP_VIEW.size.x - ms.x * s) * 0.5,
		MAP_VIEW.position.y + (MAP_VIEW.size.y - ms.y * s) * 0.5)
	var lx0 := (_cam.x - off.x * CAM_ZOOM) / (s * CAM_ZOOM)
	var ly0 := (_cam.y - off.y * CAM_ZOOM) / (s * CAM_ZOOM)
	var lw := MAP_VIEW.size.x / (s * CAM_ZOOM)
	var lh := MAP_VIEW.size.y / (s * CAM_ZOOM)
	var fr := Rect2(
		mpos.x + lx0 / WorldTerrain.MAP_W * msize.x,
		mpos.y + ly0 / WorldTerrain.MAP_H * msize.y,
		lw / WorldTerrain.MAP_W * msize.x,
		lh / WorldTerrain.MAP_H * msize.y)
	draw_rect(fr, Color(1.0, 0.95, 0.45, 0.95), false, 2)
	# 玩家
	var p: Vector2 = _gs().player_map_pos
	draw_circle(mpos + Vector2(p.x / WorldTerrain.MAP_W, p.y / WorldTerrain.MAP_H) * msize, 3.0, Color(0.95, 0.25, 0.15, 1))


func _draw_roads(ms: Vector2) -> void:
	var view := MAP_VIEW.grow(30)
	for e in _roads:
		var a: Vector2 = _scr(ms, e[0])
		var b: Vector2 = _scr(ms, e[1])
		if not (view.has_point(a) or view.has_point(b)):
			continue
		draw_line(a, b, ROAD_COLOR, 3.5)


func _draw_mountains(ms: Vector2) -> void:
	var land_dark := Color(0.30, 0.24, 0.18, 1)
	var view := MAP_VIEW.grow(40)
	for m in JapanMap.mountains():
		var lp: Vector2 = JapanMap.mountain_pos(m)
		var sp: Vector2 = _scr(ms, lp)
		if not view.has_point(sp):
			continue
		var w: float = 34.0
		var h: float = 40.0
		draw_colored_polygon(PackedVector2Array([sp + Vector2(-w, h * 0.4), sp + Vector2(0, -h), sp + Vector2(w, h * 0.4)]), land_dark)
		draw_colored_polygon(PackedVector2Array([sp + Vector2(-w * 0.3, -h * 0.1), sp + Vector2(0, -h), sp + Vector2(w * 0.3, -h * 0.1), sp + Vector2(0, -h * 0.55)]), SNOW_COLOR)


func _draw_castles(ms: Vector2, positions: Dictionary) -> void:
	var drawn_names: Array = []   # [Rect2] 已绘城名包围盒（避让用）
	var view := MAP_VIEW.grow(60)
	var font_sz: float = UiTheme.FONT_SMALL * 1.9
	for id in positions.keys():
		var lp: Vector2 = positions[id]
		var sp: Vector2 = _scr(ms, lp)
		var near: bool = (id == _nearest_id)
		var cid := int(id)
		var has_town: bool = _gd().get_castle_has_town(cid)
		var is_port: bool = _gd().is_port_city(cid)
		if not view.has_point(sp):
			continue
		var name_col: Color = NEAR_COLOR if near else (PORT_COLOR if is_port else TOWN_COLOR)
		var minkok: int = int(_gd().get_castle(cid).get("minkok", 0))
		# 城郭分级图标（按史实石高/类型：大天守/天守/港口/城寨/村落）
		_draw_castle_keep(sp, is_port, near, minkok, has_town)
		# 城名（简单避让：右侧 → 上方 → 下方 → 跳过）
		var cname: String = str(_gd().get_castle(cid).get("name", ""))
		var name_w: float = float(cname.length()) * font_sz * 0.62
		var cand := [
			Rect2(sp + Vector2(26, -14), Vector2(name_w, 40)),
			Rect2(sp + Vector2(-name_w * 0.4, -46), Vector2(name_w, 40)),
			Rect2(sp + Vector2(-name_w * 0.4, 34), Vector2(name_w, 40)),
		]
		var placed := false
		for cand_rect in cand:
			var clash := false
			for r in drawn_names:
				if r.intersects(cand_rect):
					clash = true
					break
			if not clash:
				draw_string(UiTheme.font(), cand_rect.position + Vector2(0, 32), cname, HORIZONTAL_ALIGNMENT_LEFT, -1, font_sz, name_col)
				drawn_names.append(cand_rect)
				placed = true
				break
		if not placed and near:
			var forced := Rect2(sp + Vector2(-name_w * 0.4, -46), Vector2(name_w, 40))
			draw_string(UiTheme.font(), forced.position + Vector2(0, 32), cname, HORIZONTAL_ALIGNMENT_LEFT, -1, font_sz, name_col)
			drawn_names.append(forced)



## 町城/港町城郭：石垣 + 白墙天守 + 瓦顶
func _load_icon(n: String) -> ImageTexture:
	var f := FileAccess.open("res://assets/icons/%s.png" % n, FileAccess.READ)
	if f == null:
		return null
	var img := Image.new()
	img.load_png_from_buffer(f.get_buffer(f.get_length()))
	return ImageTexture.create_from_image(img)


## 绘制图标（中心锚点，等比缩放）
func _draw_icon(tex: ImageTexture, c: Vector2, w: float) -> void:
	if tex == null:
		return
	var h: float = w * float(tex.get_height()) / float(tex.get_width())
	draw_texture_rect(tex, Rect2(c - Vector2(w, h) * 0.5, Vector2(w, h)), false)


## 最近城黄色光圈（压扁椭圆，贴地）
func _draw_near_ring(c: Vector2) -> void:
	draw_set_transform(c, 0.0, Vector2(1.0, 0.5))
	draw_arc(Vector2.ZERO, 54.0, 0, TAU, 36, Color(1, 0.85, 0.30, 0.9), 4.0)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	draw_circle(c + Vector2(0, 10), 40, Color(1, 0.9, 0.3, 0.10))


func _draw_castle_keep(c: Vector2, is_port: bool, near: bool, minkok: int, has_town: bool) -> void:
	## 史实分级：港町→港口；石高≥150 町城→大天守；町城→天守；石高≥100 据点→城寨；小据点→村落
	if is_port:
		_draw_icon(_icon_port, c + Vector2(0, 12), 68.0)
	elif has_town and minkok >= 150:
		_draw_icon(_icon_great, c + Vector2(0, 16), 112.0)
	elif has_town:
		_draw_icon(_icon_castle, c + Vector2(0, 14), 92.0)
	elif minkok >= 100:
		_draw_icon(_icon_fort, c + Vector2(0, 8), 66.0)
	else:
		_draw_icon(_icon_village, c + Vector2(0, 10), 58.0)
	if near:
		_draw_near_ring(c)


## 军事城小寨：木栅 + 望楼
## (军事城图标已并入 _draw_castle_keep 分级)


## 港町帆船标（小帆船）
func _draw_sail(c: Vector2) -> void:
	var b := c + Vector2(0, 16)
	draw_rect(Rect2(b + Vector2(-7, 0), Vector2(14, 4)), Color(0.36, 0.28, 0.18, 1))
	draw_colored_polygon(PackedVector2Array([
		b + Vector2(4, 0), b + Vector2(10, -10), b + Vector2(4, -8),
	]), Color(0.92, 0.90, 0.86, 1))
	draw_line(b + Vector2(4, 0), b + Vector2(4, -10), Color(0.5, 0.42, 0.30, 1), 1.5)


func _draw_player(ms: Vector2) -> void:
	var psp: Vector2 = _scr(ms, _gs().player_map_pos)
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
	var w: int = _gs().weather.get_weather()
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
	draw_string(UiTheme.font(), Vector2(panel.position.x + 30, y - 12), "【%s · 坐船】" % _gd().get_castle(_gs().nearest_port()).get("name", ""),
		HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_BODY, Color(0.42, 0.80, 0.95, 1))
	for i in range(_sea_menu.size()):
		var r: Dictionary = _sea_menu[i]
		var line: String = "%d. %s（%d 日）" % [i + 1, _gd().get_castle(int(r["to"])).get("name", ""), int(r["days"])]
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
		var prov_name: String = str(_gd().get_province(prov).get("name", "")) if _gd().get_province(prov).size() > 0 else "—"
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
	var p: Dictionary = _gd().get_province(pid)
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
