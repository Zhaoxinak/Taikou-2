extends Control
## 外交関係一览画面（阶段 7 收尾：进度表 line 156 显式标注「外交关系一览画面仍未做」）
##
## 只读参考屏：以自国（GameState.protagonist_province）为中心，逐一列出 49 国与自国的
## 外交関係（8 级 → DIPL_NAMES + DIPL_COLOR）与主从関係（4 级 → MV_NAMES + MV_COLOR）。
## 全部走 GameState.diplomacy 已验证纯逻辑（diplomacy.gd 60 断言），本屏只做布局与着色，
## 不持有玩法状态、不修改矩阵。
##
## ⚠️ 诚实未接：① 主从过滤提示 can_dispatch（0x4c4270）不在此屏展示——属可交互校验层，
##   由主命执行时（command_screen 目标国选择器）按主从过滤；② 关系为静态矩阵快照，
##   不随月自动演变（原版月结链未在复刻层建模）；③ 美术为极简 UI 控件，HD-2D 升级待 HD-6。

const UiTheme = preload("res://src/ui/UiTheme.gd")
const UiPanel = preload("res://src/ui/UiPanel.gd")
const UiButton = preload("res://src/ui/UiButton.gd")
const UiLabel = preload("res://src/ui/UiLabel.gd")
const DiplomacyRef = preload("res://src/core/diplomacy.gd")

var callback_back: Callable = Callable()   # 调用方注入：关闭本屏回到上一屏

var _self: int = -1
var _rows: Array = []          # 每个国一行 Control（供测试遍历）
var _legend_ok: bool = false


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP

	var dim := ColorRect.new()
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dim.color = Color(0.0, 0.0, 0.0, 0.6)
	dim.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(dim)

	var panel := UiPanel.new()
	panel.title = "外交関係一览"
	panel.title_height = 56
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.custom_minimum_size = Vector2(1180, 860)
	panel.size = Vector2(1180, 860)
	add_child(panel)

	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 28)
	margin.add_theme_constant_override("margin_top", 28)
	margin.add_theme_constant_override("margin_right", 28)
	margin.add_theme_constant_override("margin_bottom", 28)
	panel.add_child(margin)

	var body := VBoxContainer.new()
	body.add_theme_constant_override("separation", 14)
	margin.add_child(body)

	# —— 自国标题 ——
	_self = int(GameState.protagonist_province())
	var sub := UiLabel.new()
	sub.font_size = UiTheme.FONT_HEAD
	sub.custom_minimum_size = Vector2(1100, 44)
	sub.text = "自国：%s（%d）" % [_prov_name(_self), _self]
	body.add_child(sub)

	# —— 列表（可滚动）——
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(1124, 560)
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_child(scroll)

	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 4)
	scroll.add_child(list)

	for p in 49:
		list.add_child(_row(p))

	# —— 图例 ——
	body.add_child(_legend())
	_legend_ok = true

	# —— 返回 ——
	var back := UiButton.new()
	back.text = "返回"
	back.font_size = UiTheme.FONT_BODY
	back.custom_minimum_size = Vector2(360, 56)
	back.pressed.connect(_on_back)
	body.add_child(back)


## 等级色板：DIPL_COLOR / MV_COLOR 的索引 → 显示色
func _tier_color(idx: int) -> Color:
	match idx:
		1: return Color(0.36, 0.80, 0.45, 1.0)   # 友好（绿）
		2: return Color(0.90, 0.38, 0.34, 1.0)   # 敌对（红）
		4: return Color(0.95, 0.80, 0.30, 1.0)   # 金（同盟/特殊）
		_: return UiTheme.C_TEXT_OFF             # 中性（灰）


func _prov_name(pid: int) -> String:
	if pid < 0:
		return "—"
	return str(GameData.get_province_name(pid))


func _row(p: int) -> Control:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 12)
	h.custom_minimum_size = Vector2(1100, 44)

	var name := UiLabel.new()
	name.font_size = UiTheme.FONT_BODY
	name.custom_minimum_size = Vector2(300, 40)
	if p == _self:
		name.text = "%s（自国）" % _prov_name(p)
		name.color = UiTheme.C_ACCENT
	else:
		name.text = "%s" % _prov_name(p)
	h.add_child(name)

	var dipl := UiLabel.new()
	dipl.font_size = UiTheme.FONT_BODY
	dipl.custom_minimum_size = Vector2(280, 40)
	var mv := UiLabel.new()
	mv.font_size = UiTheme.FONT_BODY
	mv.custom_minimum_size = Vector2(240, 40)

	if p == _self:
		dipl.text = "（自国）"
		dipl.color = UiTheme.C_TEXT_OFF
		mv.text = "—"
		mv.color = UiTheme.C_TEXT_OFF
	else:
		var d: int = int(GameState.diplomacy.get_diplomacy(_self, p))
		var m: int = int(GameState.diplomacy.get_master_vassal(_self, p))
		dipl.text = "外交：%s" % DiplomacyRef.DIPL_NAMES[d] if d < DiplomacyRef.DIPL_NAMES.size() else "?"
		dipl.color = _tier_color(int(DiplomacyRef.DIPL_COLOR[d]))
		mv.text = "主从：%s" % DiplomacyRef.MV_NAMES[m] if m < DiplomacyRef.MV_NAMES.size() else "?"
		mv.color = _tier_color(int(DiplomacyRef.MV_COLOR[m]))
	h.add_child(dipl)
	h.add_child(mv)

	_rows.append(h)
	return h


func _legend() -> Control:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 6)
	box.custom_minimum_size = Vector2(1100, 96)

	var lab := UiLabel.new()
	lab.font_size = UiTheme.FONT_SMALL
	lab.text = "图例"
	box.add_child(lab)

	# 外交関係 8 级
	var row_d := HBoxContainer.new()
	row_d.add_theme_constant_override("separation", 10)
	for d in range(DiplomacyRef.DIPL_NAMES.size()):
		row_d.add_child(_chip(DiplomacyRef.DIPL_NAMES[d], _tier_color(int(DiplomacyRef.DIPL_COLOR[d]))))
	box.add_child(row_d)

	# 主从関係 4 级
	var row_m := HBoxContainer.new()
	row_m.add_theme_constant_override("separation", 10)
	for m in range(DiplomacyRef.MV_NAMES.size()):
		var nm: String = DiplomacyRef.MV_NAMES[m]
		if nm == "":
			nm = "空白"
		row_m.add_child(_chip(nm, _tier_color(int(DiplomacyRef.MV_COLOR[m]))))
	box.add_child(row_m)
	return box


func _chip(text: String, col: Color) -> Control:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 6)
	var swatch := ColorRect.new()
	swatch.custom_minimum_size = Vector2(22, 22)
	swatch.color = col
	h.add_child(swatch)
	var lab := UiLabel.new()
	lab.font_size = UiTheme.FONT_SMALL
	lab.text = text
	lab.color = col
	h.add_child(lab)
	return h


func _on_back() -> void:
	if callback_back.is_valid():
		callback_back.call()


func _input(event: InputEvent) -> void:
	if event is InputEventKey:
		var ek := event as InputEventKey
		if ek.pressed and not ek.echo and ek.keycode == KEY_ESCAPE:
			accept_event()
			_on_back()
