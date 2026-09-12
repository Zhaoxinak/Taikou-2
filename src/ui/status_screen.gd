extends Control
## 状态画面（自绘）：五维 / 技能 / 職位 / 忠诚 / 体力 / 年月
## 主命：修行（10 技能各一钮，封顶 3）/ 休养（回满体力）；每次主命推进 1 月。
##
## 布局全在 UiTheme 设计空间（1920×1080），废除旧实现的硬编码 font_size(30/20) 与像素偏移。
## 2026-09-12 重构：UI 全部预置在 scenes/screens/status_screen.tscn（编辑器可见、可归类），
## 脚本只做信号接线与逻辑刷新；事件弹窗同样预置为 EventOverlay（visible 切换）。
##
## ⚠️ 对外契约保持不变：`_info` / `_stat`（均有 `.text`）、`_skill_buttons`（有 `.text`）、
##    `_on_train(idx)` / `_on_rest()` / `_on_back()` —— UI 流程测试依赖这些名字。

const UiTheme = preload("res://src/ui/UiTheme.gd")
const ConstsRef = preload("res://src/core/Consts.gd")

# 场景预置节点（编辑器可见；命名见 status_screen.tscn）
@onready var _info = $Panel/VBox/Info
@onready var _stat = $Panel/VBox/Stat
@onready var _help = $Panel/VBox/Help
@onready var _skill_buttons: Array = _collect_skill_buttons()
@onready var _event_overlay: Control = $EventOverlay
@onready var _event_text = $EventOverlay/PopupPanel/PopupVBox/Scroll/Text

# 事件流弹窗（event_log 渲染层；事件解释器效果执行层的 UI 出口）
var _event_read_idx: int = 0       # 已读到的 event_log 下标（避免重复弹旧事件）

# 帮助栏（MSGX 原版说明文接 UI）
const _HELP_HINT := "将鼠标移到技能上，可查看原版说明（MSGX）；Enter/Space=休养，Esc=回标题"
# 技能槽顺序（Consts.SKILL_NAMES）→ MSGX 文本 id（§MESSAGE1 帮助文 7..16）
#   口才7 马术8 算术9 剑术12 忍术15 兵法13 洋枪14 筑城16 礼法10 茶道11
const _SKILL_MSGX: Array[int] = [7, 8, 9, 12, 15, 13, 14, 16, 10, 11]


func _collect_skill_buttons() -> Array:
	var arr: Array = []
	for k in ConstsRef.SKILL_NAMES.size():
		var b = $Panel/VBox/SkillGrid.get_child(k)
		b.pressed.connect(_on_train.bind(k))
		b.mouse_entered.connect(_show_skill_help.bind(k))
		b.mouse_exited.connect(_reset_help)
		arr.append(b)
	return arr


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS
	_reset_help()
	_refresh()


## 键盘兜底：即使鼠标/按钮焦点异常也能操作。
## 若当前焦点在某按钮上，Enter/Space 留给该按钮（未来 UiButton 接键盘时避免重复触发）。
func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_ESCAPE:
				# 事件弹窗模态中：Esc 先关弹窗，不回标题
				if _event_overlay.visible:
					accept_event()
					_close_events_popup()
					return
				accept_event()
				_on_back()
			KEY_ENTER, KEY_KP_ENTER, KEY_SPACE:
				var focus_owner := get_viewport().gui_get_focus_owner()
				if focus_owner != null and is_ancestor_of(focus_owner):
					return
				accept_event()
				_on_rest()


## 悬停技能 → 显示该技能的原版 MSGX 说明文
func _show_skill_help(k: int) -> void:
	if k < 0 or k >= _SKILL_MSGX.size():
		_reset_help()
		return
	var txt := GameData.get_text(int(_SKILL_MSGX[k]))
	if txt.is_empty():
		_reset_help()
		return
	_help.text = "【%s】%s" % [ConstsRef.SKILL_NAMES[k], txt]


func _reset_help() -> void:
	_help.text = _HELP_HINT


func _on_train(idx: int) -> void:
	var r: Dictionary = GameState.train_skill(idx)
	if not bool(r.get("ok", false)):
		_info.text = "修行失败：%s" % String(r.get("reason", "?"))
	_refresh()


func _on_rest() -> void:
	GameState.rest()
	_refresh()


func _on_back() -> void:
	get_tree().change_scene_to_file("res://scenes/main.tscn")


func _on_go_command() -> void:
	get_tree().change_scene_to_file("res://scenes/screens/command_screen.tscn")


## 事件流弹窗：把 event_log[_event_read_idx..] 的叙事行渲染为模态面板（预置节点显隐）。
## 无新事件 / 未开局 / 已弹窗中 → 直接返回（幂等，可安全从 _refresh 反复调用）。
func _show_events_popup() -> void:
	if _event_overlay.visible:
		return
	if not GameState.is_started():
		return
	var lines := GameState.pending_event_lines(_event_read_idx)
	if lines.is_empty():
		return
	_event_text.text = "\n".join(PackedStringArray(lines))
	_event_overlay.show()
	# 把已读下标推到队尾，避免下次 _refresh 重复弹同批事件
	_event_read_idx = GameState.get_event_log().size()
	# 有弹窗时主内容按钮不应抢焦点（仅模态允许关闭钮交互）
	_release_skill_focus()


## 关闭事件弹窗：隐藏预置遮罩、复位状态；idempotent。
func _close_events_popup() -> void:
	if _event_overlay.visible:
		_event_overlay.hide()
	_event_read_idx = GameState.get_event_log().size()


## 弹窗模态期间，把技能钮的焦点清掉（避免 Enter/Space 误操作底层主命）。
func _release_skill_focus() -> void:
	for b in _skill_buttons:
		if b is Control and (b as Control).has_focus():
			(b as Control).release_focus()


func _refresh() -> void:
	var st: Dictionary = GameState.get_status()
	if st.is_empty():
		get_tree().change_scene_to_file("res://scenes/main.tscn")
		return
	_info.text = "%s　%s　%d 年 %d 月" % [
		st["name"], st["rank_name"], int(st["year"]), int(st["month"])]
	var lines: Array = []
	var f: Dictionary = st["forces"]
	for k in ConstsRef.FORCE_NAMES.size():
		lines.append("%s %d" % [ConstsRef.FORCE_CN[k], int(f.get(ConstsRef.FORCE_NAMES[k], 0))])
	lines.append("忠诚 %d" % int(st["loyalty"]))
	lines.append("体力 %d/%d" % [int(st["stamina"]), int(st["stamina_max"])])
	lines.append("功勲 %d" % int(st["merit"]))
	_stat.text = "\n".join(PackedStringArray(lines)) + "\n"
	for k in _skill_buttons.size():
		var lv := int(st["skill_levels"][k])
		var b = _skill_buttons[k]
		b.text = "%s %d/3" % [ConstsRef.SKILL_NAMES[k], lv]
		# UiButton 用 enabled（而非 Godot Button 的 disabled）
		b.enabled = lv < ConstsRef.SKILL_CAP
	# 事件流弹窗：每次刷新检查是否有新事件，有则模态展示（幂等）
	_show_events_popup()
