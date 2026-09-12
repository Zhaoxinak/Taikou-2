# battle_screen.gd — 合战场景（2D 精简版：推演 + 战果面板）
#
# 挂到 scenes/screens/battle_screen.tscn（Control 根）。
# _ready 时：读 data/battles.json 的 terrain/deploy，用 BattleFlow 跑完整场推演并显示战果。
#
#
# 数据：data/battles.json（terrain 19×40，deploy 19×40 ASCII：左军 {/,1,7,9} / 右军 {+,-,3,5}）。

extends Control

const BattleFlow = preload("res://src/battle/battle_flow.gd")
const UiTheme = preload("res://src/ui/UiTheme.gd")

# 降水 ⇒ 湿润旗 wet（weather.gd 0x43d223/0x43d233：nw == RAIN or SNOW ⇒ wet=1）
# wet 进入 ctx.mode_m2 ⇒ cat==2 洋枪战力 ×2/3（0x42d62e）
const RAINY_KINDS: Array = ["雨", "雪"]

const LEFT_ARMY_CHARS := ["/", "1", "7", "9"]
const RIGHT_ARMY_CHARS := ["+", "-", "3", "5"]

@export var battle_id: int = 0
# 天气：晴 / 雨 / 雪 / 雾 / 夜（数据层 §3.9 天气系统；battles.json 暂无字段，先由场景参数驱动）
@export var weather: String = "晴"

# 合战推演（battle_flow → battle_sim）：_ready 后自动跑完一整场并显示战果
@export var auto_simulate: bool = true
@export var battle_seed: int = 1
@export var max_rounds: int = 2000
# 运行时切换天气是否重算（天气影响洋枪战力 ⇒ 影响胜负）
@export var resimulate_on_weather_change: bool = true

signal battle_finished(result: Dictionary)

var _battles: Array = []
var result: Dictionary = {}
# 战果层为场景预置节点（battle_screen.tscn）：CanvasLayer/BattleResult/Root，_show_result 只填充+显隐
@onready var _result_root: Control = $BattleResult/Root
@onready var _result_label = $BattleResult/Root/Panel/Margin/ResultLabel


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
	if result.is_empty():
		_result_root.hide()
		return
	_result_label.text = _result_text()
	_result_root.show()


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

	var terrain: Array = b.get("terrain", [])
	var deploy: Array = b.get("deploy", [])
	var left_n := 0
	var right_n := 0
	for row in deploy:
		for ch in row:
			if ch in LEFT_ARMY_CHARS:
				left_n += 1
			elif ch in RIGHT_ARMY_CHARS:
				right_n += 1

	print("[BattleScreen] 战图 %d 已构建（2D 精简版）：地形 %d×%d、左军 %d 格、右军 %d 格；推演 + 战果面板" % [
		bid, terrain.size(), terrain[0].size() if terrain.size() > 0 else 0, left_n, right_n])


func set_weather(kind: String) -> void:
	weather = kind
	# 天气改变降水旗 ⇒ 洋枪战力随之变化，战果需重算
	if resimulate_on_weather_change and not _battles.is_empty():
		simulate()
