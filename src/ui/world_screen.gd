extends Control
## 大地图（方案 B 最小可玩空壳）
##
## 打通「状态画面 → 大地图 → 移动 → 进城」主循环：
##   · 方向键 / WASD 移动主角（逻辑坐标，world_map.gd 投影到屏幕）
##   · 靠近某城（距离 ≤ ENTER_DIST）时高亮并在底部提示，按 Enter 进城
##   · 进城显示城下町占位 overlay（城名/国/城主/兵米金/农商石高）
##   · Esc 在 overlay 时关闭回大地图；否则回状态画面
##
## ⚠️ 诚实未接：
##   1. 城坐标为聚类近似（data/castle_map.json，非原版固定坐标，见 gen_castle_map.py）
##   2. 美术为极简几何占位，HD-2D 升级待 HD-6
##   3. 城下町设施（商店/宿屋/道場/医館）与主命执行已由 castle_town.gd / command_screen.gd 实现；
##      待实现：30 店铺人格专属交互（画师/医师/教会/南蛮商馆）、剧情推进
##
## 布局在设计空间 1920×1080；地图可视区为去掉顶部/底部 HUD 的矩形。

const UiTheme = preload("res://src/ui/UiTheme.gd")
const UiLabel = preload("res://src/ui/UiLabel.gd")
const WorldMapRef = preload("res://src/core/world_map.gd")
const CastleTown = preload("res://src/ui/castle_town.gd")

const HUD_TOP := 64.0
const HUD_BOTTOM := 56.0
const MAP_VIEW := Rect2(0, HUD_TOP, 1920, 1080 - HUD_TOP - HUD_BOTTOM)
const ENTER_DIST := 90.0

var _hud_top: CanvasItem
var _hud_bottom: CanvasItem
var _entered_castle: int = -1      # 进城 overlay 中显示的城 id（-1=未进城）
var _nearest_id: int = -1
var _castle_town: Control = null   # 城下町交互 UI（进城时挂载，离城时置 null）


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS
	var bg := ColorRect.new()
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bg.color = Color(0.07, 0.11, 0.09, 1)
	# 子节点默认绘制在父 _draw() 之上，会盖住城点/主角 marker；置后让父 draw 浮在 bg 上。
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
	_hud_top.text = "%s　%d 年 %d 月　所在：%s" % [name_s, GameState.year, GameState.month, loc]
	if _entered_castle >= 0:
		_hud_bottom.text = "Esc 返回大地图"
	elif _nearest_id >= 0:
		_hud_bottom.text = "方向键 / WASD 移动　·　Enter 进入 %s　·　Esc 回状态画面" % GameData.get_castle(_nearest_id).get("name", "")
	else:
		_hud_bottom.text = "方向键 / WASD 移动　·　Esc 回状态画面"


func _input(event: InputEvent) -> void:
	if event is InputEventKey:
		var ek := event as InputEventKey
		if ek.pressed and not ek.echo:
			match ek.keycode:
				KEY_ESCAPE:
					accept_event()
					if _entered_castle >= 0 or _castle_town != null:
						_exit_castle()
					else:
						get_tree().change_scene_to_file("res://scenes/screens/status_screen.tscn")
					return
				KEY_ENTER, KEY_KP_ENTER, KEY_SPACE:
					accept_event()
					if _entered_castle < 0 and _nearest_id >= 0:
						_enter_castle(_nearest_id)
					return
				KEY_UP, KEY_W: _move(0, -1)
				KEY_DOWN, KEY_S: _move(0, 1)
				KEY_LEFT, KEY_A: _move(-1, 0)
				KEY_RIGHT, KEY_D: _move(1, 0)


func _move(dx: int, dy: int) -> void:
	if _entered_castle >= 0:
		return
	GameState.move_player(dx, dy)
	var ms := GameData.get_map_size()
	_nearest_id = WorldMapRef.nearest(GameState.player_map_pos, GameData.get_castle_positions()) if GameData.has_castle_map() else -1
	_refresh_hud(); queue_redraw()


func _enter_castle(cid: int) -> void:
	GameState.enter_castle(cid)
	_entered_castle = cid
	if _castle_town == null:
		_castle_town = CastleTown.new()
		_castle_town.castle_id = cid
		_castle_town.callback_exit = _exit_castle
		add_child(_castle_town)
	_refresh_hud(); queue_redraw()


func _exit_castle() -> void:
	if _castle_town != null:
		_castle_town.queue_free()
		_castle_town = null
	_entered_castle = -1
	GameState.leave_to_world()
	_refresh_hud(); queue_redraw()


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
	# —— 城点 + 城名 ——
	for id in positions.keys():
		var lp: Vector2 = positions[id]
		var sp: Vector2 = WorldMapRef.project(lp, ms.x, ms.y, MAP_VIEW)
		var near: bool = (id == _nearest_id)
		var col: Color = Color(0.92, 0.74, 0.42, 1) if near else Color(0.62, 0.66, 0.70, 1)
		var s: float = 6.0 if near else 4.0
		draw_rect(Rect2(sp - Vector2(s, s), Vector2(s * 2, s * 2)), col)
		var cname: String = str(GameData.get_castle(id).get("name", ""))
		draw_string(UiTheme.font(), sp + Vector2(s + 2, 4), cname, HORIZONTAL_ALIGNMENT_LEFT, -1, UiTheme.FONT_SMALL, col)
	# —— 主角 marker ——
	var psp: Vector2 = WorldMapRef.project(GameState.player_map_pos, ms.x, ms.y, MAP_VIEW)
	draw_circle(psp, 9, Color(0.95, 0.32, 0.22, 1))
	draw_arc(psp, 15, 0, TAU, 28, Color(1.0, 0.82, 0.32, 0.9), 2.0)
	# —— 进城 overlay（城下町 UI 挂载时由其接管，不重复绘制）——
	if _entered_castle >= 0 and _castle_town == null:
		_draw_castle_overlay(GameData.get_castle(_entered_castle))


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
