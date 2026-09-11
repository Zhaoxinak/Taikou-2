extends Control
## 城下町交互 UI（方案 B 延伸：把占位 overlay 换成可点击设施菜单）
##
## 设施：商店（买/卖物品，接 economy.item_buy/sell_price）/ 宿屋（休養，接 _gs().rest）/
##       道場（修行 10 技能，接 _gs().train_skill）/ 医館（买薬，接 shop.medicine_*）/
##       出る（返回大地图，由 world_screen 注入 callback_exit）。
## 全部走 GameState 已验证的纯逻辑（shop_buy/shop_sell/rest/train_skill/buy_medicine/use_medicine），
## 本脚本只做布局与事件转发，不持有玩法状态。
##
## ⚠️ 诚实未接：① 卖价用 item_value/2 简化（原版 treasure_sell_quote 含 progress，本期未接）；
##   ② 各设施内对话/事件流（品茶/鉴定/铁炮打工/试合/忍里修业/30日修行/学做生意 + 闇商人 0x460890）
##      属 UI/对话驱动层，留待后续；③ 美术为极简 UI 控件，HD-2D 升级待 HD-6。

const UiTheme = preload("res://src/ui/UiTheme.gd")
const UiPanel = preload("res://src/ui/UiPanel.gd")
const UiButton = preload("res://src/ui/UiButton.gd")
const UiLabel = preload("res://src/ui/UiLabel.gd")
const ConstsRef = preload("res://src/core/Consts.gd")
const EconomyRef = preload("res://src/core/economy.gd")
const ShopRef = preload("res://src/core/shop.gd")

var castle_id: int = -1
var callback_exit: Callable = Callable()   # world_screen 注入：关闭本 UI 回到大地图

var _panel: Control
var _body: VBoxContainer
var _status_label: CanvasItem
var _msg_label: CanvasItem



func _gs() -> Node:
	## autoload 兼容访问（--script 无头模式不注册全局标识符）
	return get_node("/root/GameState")


func _gd() -> Node:
	return get_node("/root/GameData")


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP

	var dim := ColorRect.new()
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dim.color = Color(0.0, 0.0, 0.0, 0.55)
	dim.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(dim)

	_panel = UiPanel.new()
	_panel.title = "城下町"
	_panel.title_height = 56
	_panel.set_anchors_preset(Control.PRESET_CENTER)
	_panel.custom_minimum_size = Vector2(900, 680)
	add_child(_panel)

	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 24)
	margin.add_theme_constant_override("margin_top", 24)
	margin.add_theme_constant_override("margin_right", 24)
	margin.add_theme_constant_override("margin_bottom", 24)
	_panel.add_child(margin)

	_body = VBoxContainer.new()
	_body.add_theme_constant_override("separation", 12)
	margin.add_child(_body)

	_status_label = UiLabel.new()
	_status_label.font_size = UiTheme.FONT_BODY
	_status_label.custom_minimum_size = Vector2(800, 36)
	_body.add_child(_status_label)
	_msg_label = UiLabel.new()
	_msg_label.font_size = UiTheme.FONT_SMALL
	_msg_label.custom_minimum_size = Vector2(800, 28)
	_body.add_child(_msg_label)

	_show_facilities()
	_refresh_status()


func _refresh_status() -> void:
	if not is_instance_valid(_status_label):
		return
	var st: Dictionary = _gs().get_status()
	_status_label.text = "金 %d　体力 %d/%d　%d年%d月　薬 %d服" % [
		int(st.get("money", 0)), int(st.get("stamina", 0)), int(st.get("stamina_max", 0)),
		_gs().year, _gs().month, _gs().get_medicines()
	]


func _clear_body() -> void:
	for c in _body.get_children():
		if c != _status_label and c != _msg_label:
			c.queue_free()


func _msg(s: String) -> void:
	if is_instance_valid(_msg_label):
		_msg_label.text = s


func _add_btn(parent: Control, text: String, cb: Callable) -> UiButton:
	var b := UiButton.new()
	b.text = text
	b.font_size = UiTheme.FONT_BODY
	b.custom_minimum_size = Vector2(380, 52)
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.pressed.connect(cb)
	parent.add_child(b)
	return b


# ============================================================ 设施菜单
func _show_facilities() -> void:
	_clear_body()
	_msg("施設を選んでください（Esc で出る）")
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 12)
	grid.add_theme_constant_override("v_separation", 12)
	_body.add_child(grid)
	_add_btn(grid, "商店", _show_shop.bind("buy"))
	_add_btn(grid, "宿屋", _show_inn)
	_add_btn(grid, "道場", _show_dojo)
	_add_btn(grid, "医館", _show_medicine)
	_add_btn(grid, "出る", _exit)


# ============================================================ 商店（买 / 卖）
func _show_shop(mode: String = "buy") -> void:
	_clear_body()
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	_body.add_child(row)
	_add_btn(row, "買う", _show_shop.bind("buy"))
	_add_btn(row, "売る", _show_shop.bind("sell"))
	_add_btn(row, "戻る", _show_facilities)

	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(852, 430)
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_body.add_child(scroll)

	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 6)
	scroll.add_child(list)

	if mode == "buy":
		_fill_buy_list(list)
	else:
		_fill_sell_list(list)


func _fill_buy_list(list: Control) -> void:
	var ids: Array = _gd().get_item_ids()
	for id in ids:
		var item: Dictionary = _gd().get_item(int(id))
		if item.is_empty():
			continue
		var price: int = EconomyRef.item_buy_price(item)
		var h := HBoxContainer.new()
		h.add_theme_constant_override("separation", 10)
		var lab := UiLabel.new()
		lab.font_size = UiTheme.FONT_SMALL
		lab.custom_minimum_size = Vector2(560, 40)
		lab.text = "%s　%d 金" % [str(item.get("name", "")), price]
		h.add_child(lab)
		var b := UiButton.new()
		b.text = "買"
		b.font_size = UiTheme.FONT_SMALL
		b.custom_minimum_size = Vector2(120, 40)
		b.pressed.connect(_on_buy.bind(int(id)))
		h.add_child(b)
		list.add_child(h)


func _fill_sell_list(list: Control) -> void:
	var inv: Dictionary = _gs().get_inventory()
	if inv.is_empty():
		var empty := UiLabel.new()
		empty.font_size = UiTheme.FONT_SMALL
		empty.text = "（所持品がありません）"
		list.add_child(empty)
		return
	for id in inv.keys():
		var qty: int = int(inv[id])
		if qty <= 0:
			continue
		var item: Dictionary = _gd().get_item(int(id))
		if item.is_empty():
			continue
		var price: int = EconomyRef.item_sell_value(item)
		var h := HBoxContainer.new()
		h.add_theme_constant_override("separation", 10)
		var lab := UiLabel.new()
		lab.font_size = UiTheme.FONT_SMALL
		lab.custom_minimum_size = Vector2(520, 40)
		lab.text = "%s ×%d　%d 金/個" % [str(item.get("name", "")), qty, price]
		h.add_child(lab)
		var b := UiButton.new()
		b.text = "売"
		b.font_size = UiTheme.FONT_SMALL
		b.custom_minimum_size = Vector2(120, 40)
		b.pressed.connect(_on_sell.bind(int(id)))
		h.add_child(b)
		list.add_child(h)


func _on_buy(item_id: int) -> void:
	var r: Dictionary = _gs().shop_buy(item_id)
	if r["ok"]:
		_msg("購入：%s（-%d 金）" % [r["name"], r["cost"]])
	else:
		_msg("購入失敗：%s" % r["reason"])
	_refresh_status()


func _on_sell(item_id: int) -> void:
	var r: Dictionary = _gs().shop_sell(item_id, 1)
	if r["ok"]:
		_msg("売却：%s（+%d 金）" % [r["name"], r["gain"]])
	else:
		_msg("売却失敗：%s" % r["reason"])
	_refresh_status()
	_show_shop("sell")


# ============================================================ 宿屋
func _show_inn() -> void:
	_clear_body()
	_msg("宿屋：休養すると体力が回復し、1ヶ月経過します。")
	_add_btn(_body, "休養する", _on_inn_rest)
	_add_btn(_body, "戻る", _show_facilities)


func _on_inn_rest() -> void:
	var r: Dictionary = _gs().rest()
	if r["ok"]:
		_msg("休養しました。体力が回復しました。")
	else:
		_msg("休養失敗：%s" % r["reason"])
	_refresh_status()
	_show_inn()


# ============================================================ 道場
func _show_dojo() -> void:
	_clear_body()
	_msg("道場：技能を修行します（体力20・1ヶ月）。")
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 12)
	grid.add_theme_constant_override("v_separation", 12)
	_body.add_child(grid)
	var st: Dictionary = _gs().get_status()
	var skills: Array = st.get("skill_levels", [])
	var names: Array = ConstsRef.SKILL_NAMES
	for i in range(names.size()):
		var lvl: int = int(skills[i]) if i < skills.size() else 0
		var b := UiButton.new()
		b.text = "%s Lv%d" % [str(names[i]), lvl]
		b.font_size = UiTheme.FONT_SMALL
		b.custom_minimum_size = Vector2(380, 48)
		b.pressed.connect(_on_train.bind(i))
		grid.add_child(b)
	_add_btn(_body, "戻る", _show_facilities)


func _on_train(idx: int) -> void:
	var r: Dictionary = _gs().train_skill(idx)
	if r["ok"]:
		_msg("%s を修行しました。" % ConstsRef.SKILL_NAMES[idx])
	else:
		_msg("修行失敗：%s" % r["reason"])
	_refresh_status()
	_show_dojo()


# ============================================================ 医館
func _show_medicine() -> void:
	_clear_body()
	var money: int = int(_gs().get_status().get("money", 0))
	var max_d: int = ShopRef.medicine_doses(money)
	_msg("医館：薬を買えます（所持 %d 服）。1服 = 50 金相当。" % _gs().get_medicines())
	_add_btn(_body, "薬を最大で買う（%d 服）" % max_d, _on_buy_med.bind(max_d))
	_add_btn(_body, "薬を1服使う（体力回復）", _on_use_med)
	_add_btn(_body, "戻る", _show_facilities)


func _on_buy_med(doses: int) -> void:
	var r: Dictionary = _gs().buy_medicine(doses)
	if r["ok"]:
		_msg("薬 %d 服を購入しました（-%d 金）" % [r["doses"], r["cost"]])
	else:
		_msg("購入失敗：%s" % r["reason"])
	_refresh_status()
	_show_medicine()


func _on_use_med() -> void:
	var r: Dictionary = _gs().use_medicine()
	if r["ok"]:
		_msg("薬を使いました。体力が回復しました。")
	else:
		_msg("使用失敗：%s" % r["reason"])
	_refresh_status()
	_show_medicine()


# ============================================================ 退出
func _exit() -> void:
	if callback_exit.is_valid():
		callback_exit.call()


func _input(event: InputEvent) -> void:
	if event is InputEventKey:
		var ek := event as InputEventKey
		if ek.pressed and not ek.echo and ek.keycode == KEY_ESCAPE:
			accept_event()
			_exit()
