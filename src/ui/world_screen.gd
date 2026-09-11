extends Control
## 大地图（复刻原版）
##
## 主循环：状态画面 → 大地图 → 逐格/点击移动 → 进城 / 坐船跨海
##   · 移动方式（原版）：
##       - 鼠标左键点击地图任意处 → 主角沿直线自动移动（每格推进 1 天）
##       - 方向键 / WASD 逐格移动（也推进时间）
##       - 移动中按 Esc 停止
##   · 接近城（距离 ≤ ENTER_DIST）→ 高亮 + 底部提示，Enter 进城（城下町）
##   · 港町（沿海町城）→ 底部出现「坐船」提示，按 B 打开航线列表，
##     选择目的地 → 消耗航路天数 + 体力压至 20（复刻原版手册）
##   · 背景 = 日本列岛简化轮廓（史实海岸线，japan_map.gd）+ 城点/城名
##   · HUD：年 / 月 / 日 / 所在 / 体力
##
## 布局在设计空间 1920×1080；地图可视区为去掉顶部/底部 HUD 的矩形。

const UiTheme = preload("res://src/ui/UiTheme.gd")
const UiLabel = preload("res://src/ui/UiLabel.gd")
const WorldMapRef = preload("res://src/core/world_map.gd")
const CastleTown = preload("res://src/ui/castle_town.gd")
const JapanMap = preload("res://src/ui/japan_map.gd")

const HUD_TOP := 64.0
const HUD_BOTTOM := 56.0
const MAP_VIEW := Rect2(0, HUD_TOP, 1920, 1080 - HUD_TOP - HUD_BOTTOM)
const MOVE_TICK := 0.25        # 自动移动每格间隔（秒，模拟原版行走节奏）

var _hud_top: CanvasItem
var _hud_bottom: CanvasItem
var _entered_castle: int = -1      # 进城 overlay 中显示的城 id（-1=未进城）
var _nearest_id: int = -1
var _castle_town: Control = null   # 城下町交互 UI（进城时挂载，离城时置 null）

var _move_target: Vector2 = Vector2.INF   # 点击自动移动目标（INF=未在移动）
var _move_timer: float = 0.0
var _sea_menu: Array = []                # 坐船菜单（可达港 [{id,name,days}]），空=未打开
var _sea_sel: int = 0
var _msg: String = ""                    # 底部消息（坐船结果等），临时显示


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS
	var bg := ColorRect.new()
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bg.color = Color(0.05, 0.10, 0.12, 1)
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
	_refresh_hud()
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
	_hud_top.text = "%s　%d 年 %d 月 %d 日　所在：%s%s　体力 %d/%d" % [
		name_s, GameState.year, GameState.month, GameState.day, loc, sp,
		int(st.get("stamina", 0)), int(st.get("stamina_max", 100)),
	]
	if _entered_castle >= 0:
		_hud_bottom.text = "Esc 返回大地图"
	elif not _sea_menu.is_empty():
		_hud_bottom.text = _sea_hint()
	elif _move_target != Vector2.INF:
		_hud_bottom.text = "正在移动…（Esc 停止）"
	elif _nearest_id >= 0:
		var near_name: String = GameData.get_castle(_nearest_id).get("name", "")
		var extra := ""
		if GameState.nearest_port() >= 0:
			extra = "　·　B 坐船"
		_hud_bottom.text = "鼠标点击移动 / 方向键逐格　·　Enter 进入 %s%s　·　Esc 回状态画面" % [near_name, extra]
	else:
		_hud_bottom.text = "鼠标点击移动 / 方向键逐格　·　Esc 回状态画面"


func _sea_hint() -> String:
	var items := []
	for i in range(_sea_menu.size()):
		var r: Dictionary = _sea_menu[i]
		var mark := "▶" if i == _sea_sel else " "
		items.append("%s%d.%s（%d日）" % [mark, i + 1, GameData.get_castle(int(r["to"])).get("name", ""), int(r["days"])])
	return "坐船：%s　（↑↓ 选择，Enter 乘船，B/Esc 关闭）" % "　".join(items)


func _process(delta: float) -> void:
	if _move_target == Vector2.INF or _entered_castle >= 0:
		return
	_move_timer -= delta
	if _move_timer > 0.0:
		return
	_move_timer = MOVE_TICK
	var arrived: bool = GameState.move_player_towards(_move_target)
	_update_nearest()
	_refresh_hud()
	queue_redraw()
	if arrived:
		_move_target = Vector2.INF


func _update_nearest() -> void:
	_nearest_id = WorldMapRef.nearest(GameState.player_map_pos, GameData.get_castle_positions()) if GameData.has_castle_map() else -1


func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		accept_event()
		if _entered_castle >= 0 or not _sea_menu.is_empty():
			return
		var target := WorldMapRef.unproject(event.position, GameData.get_map_size().x, GameData.get_map_size().y, MAP_VIEW)
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
					if _entered_castle < 0 and not _sea_menu.is_empty():
						_travel_selected()
					elif _entered_castle < 0 and _nearest_id >= 0 and _sea_menu.is_empty():
						_enter_castle(_nearest_id)
					return
				KEY_B:
					accept_event()
					if _entered_castle < 0 and _sea_menu.is_empty():
						_toggle_sea_menu()
					return
				KEY_UP, KEY_W:
					if not _sea_menu.is_empty():
						accept_event(); _sea_sel = (_sea_sel - 1 + _sea_menu.size()) % _sea_menu.size(); _refresh_hud()
					else:
						_move_target = Vector2.INF
						_move(0, -1)
				KEY_DOWN, KEY_S:
					if not _sea_menu.is_empty():
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


func _move(dx: int, dy: int) -> void:
	if _entered_castle >= 0:
		return
	GameState.move_player(dx, dy)
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


func _draw() -> void:
	if not GameData.has_castle_map():
		return
	var ms := GameData.get_map_size()
	var positions: Dictionary = GameData.get_castle_positions()
	_draw_japan_bg(ms)
	# —— 城点 + 城名 ——
	for id in positions.keys():
		var lp: Vector2 = positions[id]
		var sp: Vector2 = WorldMapRef.project(lp, ms.x, ms.y, MAP_VIEW)
		var near: bool = (id == _nearest_id)
		var col: Color
		if GameData.is_port_city(int(id)):
			col = Color(0.42, 0.80, 0.95, 1)
		elif GameData.get_castle_has_town(int(id)):
			col = Color(0.92, 0.74, 0.42, 1)
		else:
			col = Color(0.62, 0.66, 0.70, 1)
		if near:
			col = Color(1.0, 0.95, 0.55, 1)
		var s: float = 5.0 if near else 3.5
		draw_rect(Rect2(sp - Vector2(s, s), Vector2(s * 2, s * 2)), col)
		# 城名只显示：町城 / 港町 / 最近城（军事城只画点，避免 200 城名重叠成糊）
		if near or GameData.get_castle_has_town(int(id)) or GameData.is_port_city(int(id)):
			var cname: String = str(GameData.get_castle(int(id)).get("name", ""))
			draw_string(UiTheme.font(), sp + Vector2(s + 2, 4), cname, HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_SMALL, col)
	# —— 主角 marker ——
	var psp: Vector2 = WorldMapRef.project(GameState.player_map_pos, ms.x, ms.y, MAP_VIEW)
	draw_circle(psp, 9, Color(0.95, 0.32, 0.22, 1))
	draw_arc(psp, 15, 0, TAU, 28, Color(1.0, 0.82, 0.32, 0.9), 2.0)
	# —— 坐船菜单 ——
	if not _sea_menu.is_empty():
		_draw_sea_menu(ms)
	# —— 临时消息 ——
	if _msg != "":
		var mp := Vector2(60, HUD_TOP + 48)
		draw_string(UiTheme.font(), mp, _msg, HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_BODY, Color(1.0, 0.9, 0.6, 1))
	# —— 进城 overlay（城下町 UI 挂载时由其接管，不重复绘制）——
	if _entered_castle >= 0 and _castle_town == null:
		_draw_castle_overlay(GameData.get_castle(_entered_castle))


func _draw_japan_bg(ms: Vector2) -> void:
	var polys: Array = JapanMap.polygons()
	var colors := [Color(0.20, 0.27, 0.22, 1), Color(0.20, 0.27, 0.22, 1), Color(0.20, 0.27, 0.22, 1), Color(0.18, 0.24, 0.20, 1)]
	for i in range(polys.size()):
		var pts := polys[i] as PackedVector2Array
		var scr := PackedVector2Array()
		for p in pts:
			scr.append(WorldMapRef.project(p, ms.x, ms.y, MAP_VIEW))
		draw_colored_polygon(scr, colors[i])
	# 大陆边缘（本州西侧对马海峡方向）示意线
	var shore := PackedVector2Array([
		WorldMapRef.project(Vector2(1.2, 3.0), ms.x, ms.y, MAP_VIEW),
		WorldMapRef.project(Vector2(0.8, 8.0), ms.x, ms.y, MAP_VIEW),
	])
	draw_polyline(shore, Color(0.3, 0.4, 0.35, 0.5), 1.0)


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
