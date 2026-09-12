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
##   不随月自动演变（原版月结链未在复刻层建模）；③ 美术为极简 UI 控件。

const UiTheme = preload("res://src/ui/UiTheme.gd")
const DiplomacyRef = preload("res://src/core/diplomacy.gd")

var callback_back: Callable = Callable()   # 调用方注入：关闭本屏回到上一屏

var _self: int = -1
var _rows: Array = []          # 每个国一行 Control（供测试遍历）
var _legend_ok: bool = false

# —— 场景预置节点（2026-09-12 场景化重构：49 行+图例见 diplomacy_screen.tscn）——
@onready var _sub = $Panel/Margin/Body/SubTitle
@onready var _list: VBoxContainer = $Panel/Margin/Body/Scroll/List


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP

	# —— 自国标题 ——
	_self = int(GameState.protagonist_province())
	_sub.text = "自国：%s（%d）" % [_prov_name(_self), _self]

	# —— 49 行数据填充（结构已预置）——
	for p in _list.get_child_count():
		_rows.append(_row(p))
	_legend_ok = true


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


## 填充第 p 行的预置三个标签（结构已在 .tscn：Row{p}/Name|Dipl|Mv）
func _row(p: int) -> Control:
	var h: HBoxContainer = _list.get_child(p)
	var name: Control = h.get_node("Name")
	var dipl: Control = h.get_node("Dipl")
	var mv: Control = h.get_node("Mv")

	if p == _self:
		name.text = "%s（自国）" % _prov_name(p)
		name.color = UiTheme.C_ACCENT
	else:
		name.text = "%s" % _prov_name(p)

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
