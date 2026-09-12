extends Control
## 主命执行画面（填补「主命执行 仅占位 overlay，待实现」缺口）
##
## 12 主命（game_state.COMMAND_NAMES）在此真正对玩家开放：
##   * 内政 / 军备类（0..6）：直接执行，显示精确 delta（M4 精逆结果）+ 推进 1 月。
##   * 外交类（7..11）：**需先选目标国**（`opts.target_province`，0..48 且 ≠ 自国）；
##     进入目标国选择模式，列出 49 国并标注当前 外交関係/主从関係。
##     谋略(11) 原版无静态关系模型（`work_not_modeled`）⇒ 按钮置灰，不做假。
##
## 所有失败原因直接来自 `issue_command` 的 `reason` 字段，不自行发明：
##   not_started / bad_cmd / no_castle / bad_target / dispatch_blocked / work_not_modeled

const UiTheme = preload("res://src/ui/UiTheme.gd")
const DiplomacyScreen = preload("res://src/ui/diplomacy_screen.gd")

# 12 主命里哪些需要选目标国（外交类，见 CMD_TO_WORK {7→9…11→13}）
const _NEED_TARGET := {7: true, 8: true, 9: true, 10: true, 11: true}
# 原版无静态模型者（拉拢武将 0x4b960e）
const _NOT_MODELED := {11: "谋略（拉拢武将）原版无静态关系模型，占位不耗时"}

# —— 场景预置节点（2026-09-12 场景化重构：结构见 command_screen.tscn）——
@onready var _ctx = $Panel/Ctx
@onready var _msg = $Panel/Msg
@onready var _prov_panel: Control = $ProvPicker
@onready var _prov_grid: GridContainer = $ProvPicker/ProvGrid
@onready var _cmd_buttons: Array = _collect_cmd_buttons()
@onready var _prov_buttons: Array = _collect_prov_buttons()
var _pending_cmd: int = -1      # 待选目标国的主命（-1 = 无）
var _dip_screen = null           # 已挂载的外交関係一览屏（关闭时释放）


func _collect_cmd_buttons() -> Array:
	var arr: Array = []
	for k in GameState.COMMAND_NAMES.size():
		var b: Control = $Panel/Grid.get_child(k)
		b.pressed.connect(_on_command.bind(k))
		arr.append(b)
	return arr


func _collect_prov_buttons() -> Array:
	var arr: Array = []
	for i in _prov_grid.get_child_count():
		var b: Control = _prov_grid.get_child(i)
		b.pressed.connect(_on_pick_province.bind(i))
		arr.append(b)
	return arr


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS
	_refresh()


func _refresh() -> void:
	var st: Dictionary = GameState.get_status()
	if st.is_empty():
		get_tree().change_scene_to_file("res://scenes/main.tscn")
		return
	_ctx.text = "%s　%d 年 %d 月　内政 %d" % [
		st["name"], int(st["year"]), int(st["month"]),
		int(st["forces"].get("domestic", 0))]
	if _msg.text.is_empty():
		_msg.text = "选择一项主命执行。每项耗时 1 月。"


func _on_command(cmd_id: int) -> void:
	if _NOT_MODELED.has(cmd_id):
		_show_fail(GameState.COMMAND_NAMES[cmd_id], _NOT_MODELED[cmd_id])
		return
	if _NEED_TARGET.has(cmd_id):
		_open_picker(cmd_id)
		return
	_execute(cmd_id, {})


func _on_pick_province(prov: int) -> void:
	var cmd: int = _pending_cmd
	_close_picker()
	if cmd < 0:
		return
	_execute(cmd, {"target_province": prov})


func _execute(cmd_id: int, opts: Dictionary) -> void:
	var res: Dictionary = GameState.issue_command(cmd_id, opts)
	var name: String = str(res.get("name", GameState.COMMAND_NAMES[cmd_id]))
	if bool(res.get("ok", false)):
		_show_ok(name, res)
	else:
		_show_fail(name, str(res.get("reason", "?")))
	_refresh()


func _show_ok(name: String, res: Dictionary) -> void:
	var lines: Array = ["【%s】执行成功" % name]
	var d: Dictionary = res.get("deltas", {})
	var parts: Array = []
	for k in d.keys():
		parts.append("%s %+d" % [_field_cn(k), int(d[k])])
	if parts.size() > 0:
		lines.append("　" + "　".join(PackedStringArray(parts)))
	var m := int(res.get("merit_gain", 0))
	if m > 0:
		lines.append("　功勲 +%d" % m)
	var dip: Dictionary = res.get("diplomacy", {})
	if not dip.is_empty():
		lines.append("　目标国 %s：外交 %s → %s，主从 %s → %s" % [
			_prov_name(int(dip.get("target", -1))),
			_dipl_name(int(dip.get("dipl_before", -1))), _dipl_name(int(dip.get("dipl_after", -1))),
			_mv_name(int(dip.get("mv_before", -1))), _mv_name(int(dip.get("mv_after", -1)))])
	if bool(res.get("month_advanced", false)):
		var st: Dictionary = GameState.get_status()
		lines.append("　推进到 %d 年 %d 月" % [int(st["year"]), int(st["month"])])
	_msg.text = "\n".join(PackedStringArray(lines))


func _show_fail(name: String, reason: String) -> void:
	_msg.text = "【%s】未能执行（%s）\n　未消耗时间。" % [name, reason]


func _open_picker(cmd_id: int) -> void:
	_pending_cmd = cmd_id
	var my := GameState.protagonist_province()
	for i in _prov_buttons.size():
		var b = _prov_buttons[i]
		var label := "%d %s" % [i, GameData.get_province_name(i)]
		if i == my:
			label = "（自国）"
			b.enabled = false
		else:
			b.enabled = true
			var dip := GameState.diplomacy
			if dip != null and my >= 0:
				label += "\n%s" % _dipl_name(int(dip.get_diplomacy(my, i)))
		b.text = label
	_prov_panel.visible = true


func _close_picker() -> void:
	_pending_cmd = -1
	_prov_panel.visible = false


func _on_back() -> void:
	get_tree().change_scene_to_file("res://scenes/screens/status_screen.tscn")


func _on_open_diplomacy() -> void:
	if _dip_screen != null:
		return
	var scr = DiplomacyScreen.new()
	scr.callback_back = _close_diplomacy
	add_child(scr)
	_dip_screen = scr


func _close_diplomacy() -> void:
	if _dip_screen != null and is_instance_valid(_dip_screen):
		_dip_screen.queue_free()
	_dip_screen = null


func _prov_name(pid: int) -> String:
	if pid < 0:
		return "—"
	return "%d %s" % [pid, GameData.get_province_name(pid)]


func _dipl_name(v: int) -> String:
	var dip = GameState.diplomacy
	if dip == null or v < 0:
		return "—"
	var names: Array = dip.DIPL_NAMES
	return names[v] if v < names.size() else "?"


func _mv_name(v: int) -> String:
	var dip = GameState.diplomacy
	if dip == null or v < 0:
		return "—"
	var names: Array = dip.MV_NAMES
	return names[v] if v < names.size() else "?"


func _field_cn(key: String) -> String:
	match key:
		"agri": return "農耕"
		"comm": return "商業"
		"def": return "守城"
		_: return key
