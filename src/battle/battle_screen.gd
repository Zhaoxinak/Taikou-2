# battle_screen.gd — 合战场景逻辑（HD-1 地形 + HD-2 单位 sprite）
#
# 挂到 scenes/screens/battle_screen.tscn（Node3D 根，含 Camera3D + DirectionalLight3D）。
# _ready 时：用 Terrain3DBuilder 把第 battle_id 战的 19×40 地形变成 3D 网格（HD-1），
# 再用 UnitSprite 在部署图每个左右军格上摆一个 billboard 像素 sprite（HD-2，占位图，HD-4 就位自动换真图）。
#
# 数据：data/battles.json（terrain 19×40，deploy 19×40 ASCII：左军 {/,1,7,9} / 右军 {+,-,3,5}）。

extends Node3D

const Terrain3DBuilder = preload("res://src/battle/Terrain3DBuilder.gd")
const UnitSprite = preload("res://src/render/UnitSprite.gd")
const AssetLoader = preload("res://src/render/asset_loader.gd")
const Hd2DEnvironment = preload("res://src/render/Hd2DEnvironment.gd")
const WeatherFX = preload("res://src/render/WeatherFX.gd")
const BattleFlow = preload("res://src/battle/battle_flow.gd")
const UiPanel = preload("res://src/ui/UiPanel.gd")
const UiLabel = preload("res://src/ui/UiLabel.gd")

# 降水 ⇒ 湿润旗 wet（weather.gd 0x43d223/0x43d233：nw == RAIN or SNOW ⇒ wet=1）
# wet 进入 ctx.mode_m2 ⇒ cat==2 洋枪战力 ×2/3（0x42d62e）
const RAINY_KINDS: Array = ["雨", "雪"]

const LEFT_ARMY_CHARS := ["/", "1", "7", "9"]
const RIGHT_ARMY_CHARS := ["+", "-", "3", "5"]

@export var battle_id: int = 0
@export var unit_pixel_size: float = 0.02
# HD-3 天气：晴 / 雨 / 雪 / 雾 / 夜（数据层 §3.9 天气系统；battles.json 暂无字段，先由场景参数驱动）
@export var weather: String = "晴"

# 合战推演（battle_flow → battle_sim）：_ready 后自动跑完一整场并显示战果
@export var auto_simulate: bool = true
@export var battle_seed: int = 1
@export var max_rounds: int = 2000
# 运行时切换天气是否重算（天气影响洋枪战力 ⇒ 影响胜负）
@export var resimulate_on_weather_change: bool = true

signal battle_finished(result: Dictionary)

var _battles: Array = []
var _env: Environment = null
var _sun: DirectionalLight3D = null
var _weather_node: Node = null
var result: Dictionary = {}
var _result_layer: CanvasLayer = null


func _ready() -> void:
	var path := "res://data/battles.json"
	if not FileAccess.file_exists(path):
		push_error("[BattleScreen] 缺少 %s（先运行 scripts/export_for_godot.py）" % path)
		return
	_battles = JSON.parse_string(FileAccess.get_file_as_string(path))
	if _battles == null or _battles.size() == 0:
		push_error("[BattleScreen] battles.json 解析失败")
		return
	if battle_id < 0 or battle_id >= _battles.size():
		push_error("[BattleScreen] battle_id 越界: %d" % battle_id)
		return
	_build_battle(battle_id)
	_setup_environment()
	_apply_weather_now()
	if auto_simulate:
		simulate()


# ── 合战推演（battle_flow 生产入口接线）────────────────────────
## 当前天气对应的湿润旗：雨/雪 ⇒ 1（weather.gd 0x43d223/0x43d233）
func wet_flag() -> int:
	return 1 if weather in RAINY_KINDS else 0


## 跑完一整场并把战果画到屏幕。返回 BattleFlow.run 的结果 Dictionary：
##   winner / rounds / wet / gun_units / troops_side0 / troops_side1
func simulate(seed_value: int = -1, wet: int = -1) -> Dictionary:
	if battle_id < 0 or battle_id >= _battles.size():
		return {}
	var sv := battle_seed if seed_value < 0 else seed_value
	var wv := wet_flag() if wet < 0 else wet
	result = BattleFlow.run(_battles[battle_id], sv, wv, max_rounds)
	_show_result()
	battle_finished.emit(result)
	print("[BattleScreen] 战图 %d 推演结束：%s" % [battle_id, result_summary()])
	return result


func result_summary() -> String:
	if result.is_empty():
		return "（未推演）"
	var who := "引き分け（双方全灭）" if int(result.get("winner", -1)) < 0 \
		else ("左軍勝利" if int(result.get("winner", 0)) == 0 else "右軍勝利")
	return "%s / %d 回合 / 残兵 左%d 右%d / 天気%s(wet=%d) 洋枪%d" % [
		who, int(result.get("rounds", 0)),
		int(result.get("troops_side0", 0)), int(result.get("troops_side1", 0)),
		weather, int(result.get("wet", 0)), int(result.get("gun_units", 0)),
	]


func _show_result() -> void:
	if _result_layer != null:
		_result_layer.queue_free()
		_result_layer = null
	if result.is_empty():
		return
	_result_layer = CanvasLayer.new()
	_result_layer.name = "BattleResult"
	add_child(_result_layer)

	var panel := UiPanel.new()
	panel.title = "合戦結果"
	panel.title_height = 56
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.custom_minimum_size = Vector2(760, 300)
	_result_layer.add_child(panel)

	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 36)
	margin.add_theme_constant_override("margin_top", 56 + 24)
	margin.add_theme_constant_override("margin_right", 36)
	margin.add_theme_constant_override("margin_bottom", 24)
	panel.add_child(margin)

	var lab := UiLabel.new()
	lab.text = _result_text()
	lab.h_align = HORIZONTAL_ALIGNMENT_CENTER
	margin.add_child(lab)


func _result_text() -> String:
	var who := "引き分け（双方全灭）" if int(result.get("winner", -1)) < 0 \
		else ("左軍の勝利" if int(result.get("winner", 0)) == 0 else "右軍の勝利")
	var lines := [
		who,
		"",
		"戦闘回合数：%d" % int(result.get("rounds", 0)),
		"残存兵力　左軍 %d ／ 右軍 %d" % [
			int(result.get("troops_side0", 0)), int(result.get("troops_side1", 0))],
		"天気：%s（降水旗 wet=%d）　洋枪隊 %d" % [
			weather, int(result.get("wet", 0)), int(result.get("gun_units", 0))],
	]
	if int(result.get("wet", 0)) != 0 and int(result.get("gun_units", 0)) > 0:
		lines.append("※ 降水中：洋枪隊戦力 ×2/3（0x42d62e）")
	return "\n".join(lines)


func _build_battle(bid: int) -> void:
	var b: Dictionary = _battles[bid]

	# —— HD-1：3D 地形 ——
	var terrain_node := Terrain3DBuilder.build_from_battle(_battles, bid)
	add_child(terrain_node)

	# —— HD-2：单位 sprite（billboard + NEAREST，占位图回退）——
	var units_root := Node3D.new()
	units_root.name = "Units"
	add_child(units_root)

	var terrain: Array = b.get("terrain", [])
	var deploy: Array = b.get("deploy", [])
	var tex: Texture2D = AssetLoader.load_unit_texture(-1)
	var y := 0
	for row in deploy:
		var x := 0
		for ch in row:
			var side := -1
			if ch in LEFT_ARMY_CHARS:
				side = 0
			elif ch in RIGHT_ARMY_CHARS:
				side = 1
			if side >= 0:
				var cell: Variant = terrain[y][x] if (y < terrain.size() and x < terrain[y].size()) else null
				var h: float = Terrain3DBuilder.cell_height(cell)
				var pos: Vector3 = UnitSprite.grid_to_world(x, y, h + 0.5)
				var tint: Color = Color(1.0, 0.82, 0.82, 1.0) if side == 1 else Color(0.85, 1.0, 0.85, 1.0)
				var s: Sprite3D = UnitSprite.make(tex, pos, unit_pixel_size, tint)
				units_root.add_child(s)
			x += 1
		y += 1

	print("[BattleScreen] 战图 %d 已构建：地形网格 + %d 个单位 sprite（占位图，HD-4 就位自动替换）" % [bid, units_root.get_child_count()])


# ── HD-3：HD-2D 后处理环境（Bloom / ACES / SSAO / DOF）──────────
func _setup_environment() -> void:
	var we := WorldEnvironment.new()
	we.name = "WorldEnvironment"
	_env = Hd2DEnvironment.build_environment(Hd2DEnvironment.Quality.HIGH)
	# 4K 性能降级：关最贵后处理（参照 Hd2DEnvironment.downgrade_for_4k）
	if DisplayAdapter.is_4k():
		Hd2DEnvironment.downgrade_for_4k(_env)
	we.environment = _env
	add_child(we)
	_sun = get_node_or_null("DirectionalLight3D") as DirectionalLight3D


# ── HD-3：天气联动（晴/雨/雪/雾/夜）─────────────────────────────
func _apply_weather_now() -> void:
	if _env == null:
		return
	Hd2DEnvironment.apply_weather(_env, _sun, weather)
	_spawn_weather_fx()


func _spawn_weather_fx() -> void:
	if _weather_node != null:
		_weather_node.queue_free()
		_weather_node = null
	var fx := WeatherFX.make_particles(weather)
	if fx != null:
		# 战场中心偏上（地形约 40×19 格，粒子盒覆盖全场）
		fx.position = Vector3(20.0, 14.0, 13.0)
		add_child(fx)
		_weather_node = fx


# 运行时切换天气（战役/事件层可调用）
func set_weather(kind: String) -> void:
	weather = kind
	_apply_weather_now()
	# 天气改变降水旗 ⇒ 洋枪战力随之变化，战果需重算
	if resimulate_on_weather_change and not _battles.is_empty():
		simulate()
