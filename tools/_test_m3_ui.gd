# _test_m3_ui.gd — M3 UI 流程无头校验（extends SceneTree）
#
# 链路：标题「开始新游戏」→ 主角选择（6 名可选）→ 点选 #13 → 状态画面
#       → 修行（技能+1/体力-20/推月）→ 休养（回满/推月）。
#
# 运行：Godot_v4.7.1/Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_m3_ui.gd

extends SceneTree

const UiButton = preload("res://src/ui/UiButton.gd")
const UiLabel = preload("res://src/ui/UiLabel.gd")

var _fails: int = 0

func check(cond: bool, msg: String) -> void:
	if cond:
		print("[ok] " + msg)
	else:
		push_error("[FAIL] " + msg)
		_fails += 1


## 递归查找子树内文本含 label 的自绘/原生按钮（弹窗的「知道了」关闭钮）
func _find_button(node: Node, label: String) -> Node:
	if node == null:
		return null
	if (node is UiButton or node is Button) and str(node.get("text")).contains(label):
		return node
	for c in node.get_children():
		var r := _find_button(c, label)
		if r != null:
			return r
	return null


## 判断叙事行数组是否含指定事件 id 的「叙事待补」诚实占位行
func _has_pending_placeholder(arr: Array, eid: int) -> bool:
	var expect := "[事件 %d 触发] 叙事待补（逆向缺口）" % eid
	for s in arr:
		if str(s) == expect:
			return true
	return false

func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)

func _run() -> void:
	var t0 := Time.get_ticks_msec()

	# —— 1) 标题画面 ——
	var title: Control = (load("res://scenes/main.tscn") as PackedScene).instantiate()
	root.add_child(title)
	current_scene = title
	await process_frame
	await process_frame
	# 自绘：按钮改为自绘 UiButton（extends Control），故同时接受 UiButton / Button
	var start_btn = null
	for c in title.get_children():
		if c is UiButton or c is Button:
			start_btn = c
	check(start_btn != null and str(start_btn.get("text")).contains("开 始"),
		"标题画面有自绘「开始新游戏」按钮")
	start_btn.pressed.emit()
	await process_frame
	await process_frame

	# —— 2) 主角选择 ——
	var psel: Control = current_scene
	check(psel != null and psel.name == "ProtagonistSelect",
		"跳转到主角选择 (got %s)" % (psel.name if psel != null else "null"))
	var btns: Array = []
	for c in psel.get_children():
		if c is VBoxContainer:
			for b in c.get_children():
				if b is UiButton or b is Button:
					btns.append(b)
	check(btns.size() == 6, "列出 6 名可选主角 (got %d)" % btns.size())
	var t0_text := str(btns[0].get("text"))
	check(t0_text.contains("柴田胜家"), "排序首位 = #1 柴田胜家 (%s)" % t0_text)
	var has_nobu := false
	for b in btns:
		if str(b.get("text")).contains("织田信长"):
			has_nobu = true
	check(has_nobu, "列表含 #13 织田信长")

	# —— 3) 点选 #13 → 状态画面 ——
	for b in btns:
		if str(b.get("text")).contains("织田信长"):
			b.pressed.emit()
	await process_frame
	await process_frame
	var status: Control = current_scene
	check(status != null and status.name == "StatusScreen",
		"跳转到状态画面 (got %s)" % (status.name if status != null else "null"))
	# 自绘：_info / _stat 已改为自绘 UiLabel（非 Godot Label），按 .text 契约断言
	var info_text := str(status._info.get("text"))
	check(info_text.contains("织田信长") and info_text.contains("大名") and info_text.contains("1560 年 1 月"),
		"状态栏 = 织田信长/大名/1560年1月 (got %s)" % info_text)
	check(str(status._stat.get("text")).contains("魅力 90"), "五维含 魅力 90")

	# —— 4) 主命：修行 ——
	var gs = root.get_node("/root/GameState")
	var st0: Dictionary = gs.get_status()
	var t_idx := -1
	for k in (st0["skill_levels"] as Array).size():
		if int(st0["skill_levels"][k]) < 3:
			t_idx = k
			break
	var lv0 := int(st0["skill_levels"][t_idx])
	status._on_train(t_idx)
	var st1: Dictionary = gs.get_status()
	check(int(st1["skill_levels"][t_idx]) == lv0 + 1, "修行后技能 +1")
	check(int(st1["month"]) == 2, "修行推进到 2 月")
	var btn4_text := str(status._skill_buttons[t_idx].get("text"))
	check(btn4_text.contains("%d/3" % (lv0 + 1)), "技能按钮文本刷新 (%s)" % btn4_text)

	# —— 4.5) MSGX 帮助栏（悬停技能 → 原版说明文）——
	var help0 := str(status._help.get("text"))
	check(help0.contains("MSGX"), "帮助栏默认提示 (got %s)" % help0)
	var t_btn = status._skill_buttons[t_idx]
	(t_btn as Control).mouse_entered.emit()
	var help1 := str(status._help.get("text"))
	var expect_skill: String = Consts.SKILL_NAMES[t_idx]
	# ⚠️ 不要比长度：默认提示 help0 含 "MSGX …" 操作说明，可能比技能说明还长，
	#    原断言 `help1.length() > help0.length()` 会因长度而非内容误判。改为「前缀匹配 + 有变化」。
	check(help1.begins_with("【%s】" % expect_skill) and help1 != help0,
		"悬停技能显示原版说明 [%s] (got %s)" % [expect_skill, help1.substr(0, 40)])
	(t_btn as Control).mouse_exited.emit()
	check(str(status._help.get("text")) == help0, "移出后帮助栏还原")

	# —— 5) 主命：休养 ——
	var st_before: Dictionary = gs.get_status()
	status._on_rest()
	var st2: Dictionary = gs.get_status()
	check(int(st2["stamina"]) == int(st2["stamina_max"]), "休养后体力回满 (%d/%d)"
		% [int(st2["stamina"]), int(st2["stamina_max"])])
	check(int(st2["month"]) == int(st_before["month"]) + 1, "休养推进 1 月")

	# —— 6) 事件流弹窗（event_log 的 UI 渲染出口；闭环效果执行层）——
	var ev_before: int = gs.get_event_log().size()
	# 6.1 叙事事件 id15：force → _refresh 弹出，含 MSGX 叙事行
	gs.force_event(15)
	status._refresh()
	await process_frame
	await process_frame
	check(status._event_overlay != null, "事件日志非空 → 状态画面弹出事件层")
	var lines15: Array = gs.pending_event_lines(ev_before)
	check(lines15.size() >= 1, "id15 叙事事件产出 ≥1 行 MSGX 文本 (got %d)" % lines15.size())
	var close_btn = _find_button(status._event_overlay, "知道了")
	check(close_btn != null, "事件弹窗含关闭钮「知道了」")
	# 关闭
	if close_btn != null:
		close_btn.pressed.emit()
	await process_frame
	await process_frame
	check(status._event_overlay == null, "关闭 → _event_overlay 复位")
	# 6.2 narrative_pending 占位：id13 触发后叙事未逆 → 诚实占位行（不伪造）
	gs.force_event(13)
	status._refresh()
	await process_frame
	await process_frame
	check(status._event_overlay != null, "id13 事件也弹出事件层")
	var lines13: Array = gs.pending_event_lines(ev_before + 1)
	check(_has_pending_placeholder(lines13, 13), "id13 触发后显示叙事待补占位行（逆向缺口诚实标注）")
	var close_btn2 = _find_button(status._event_overlay, "知道了")
	if close_btn2 != null:
		close_btn2.pressed.emit()
	await process_frame
	await process_frame
	# 6.3 关闭后不重复弹（_event_read_idx 已推进到队尾）
	status._refresh()
	await process_frame
	await process_frame
	check(status._event_overlay == null, "已读事件不再重复弹（_event_read_idx 推进）")

	print("")
	if _fails > 0:
		push_error("M3 UI 校验失败 %d 项" % _fails)
		quit(1)
	print("[ok] M3 UI 全链路通过（用时 %.0f ms）" % [float(Time.get_ticks_msec() - t0)])
	quit(0)
