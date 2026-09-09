# _test_event_effects.gd — M7 事件解释器「效果执行层」无头校验（extends SceneTree）
#
# 复刻结构：src/core/event_effects.gd + src/core/game_state.gd（poll_events / force_event）
# 比对参考实现：scripts/event_id_dispatch_ref.py（真实 vtable 7 id：0,1,9,10,13,14,15）
#              scripts/event_handlers_full_ref.py（DECODED_CONDITIONS：MSGX id 序列）
#
# 覆盖：① force_event 对 0/1/9/10/15 发射正确 MSGX 叙事；② id13/14 仅门控、叙事未逆(narrative_pending)；
#   ③ poll_events 按月对注入状态自动触发 10/13/14；④ 月度 advance_month 驱动 poll_events 写入 event_log；
#   ⑤ 未开局/未定位时不触发。
#
# 运行：Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_event_effects.gd

extends SceneTree

const EventEffectsRef = preload("res://src/core/event_effects.gd")

var _fails: int = 0


func check(cond: bool, msg: String) -> void:
	if cond:
		print("[ok] " + msg)
	else:
		push_error("[FAIL] " + msg)
		_fails += 1


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)


func _run() -> void:
	var gs = root.get_node("/root/GameState")
	var gd = root.get_node("/root/GameData")
	# 注入 GameData 到事件效果层（防止 _ready 未跑）
	gs.event_effects.data = gd
	gs.start_new_game(13)   # 织田信长（载入 MSGX 文本）

	# ---- [1] force_event(0/1)：主效果 msg 0x7d = 125 ----
	var r0: Dictionary = gs.force_event(0)
	check(r0.get("id", -1) == 0, "force_event(0) 返回 id=0")
	check(r0.get("msg_ids", []) == [0x7d], "id0 msg_ids = [0x7d]")
	check(r0.get("msgs", []).size() == 1 and str(r0["msgs"][0]).length() > 0, "id0 叙事非空（MSGX 文本解析）")
	check(r0.get("outcome", {}).get("kind") == "gift_or_event", "id0 outcome.kind = gift_or_event")

	var r1: Dictionary = gs.force_event(1)
	check(r1.get("msg_ids", []) == [0x7d], "id1 msg_ids = [0x7d]（与 id0 同构）")
	check(not r1.get("narrative_pending", false), "id0/1 叙事已解码(非 pending)")

	# ---- [2] force_event(9)：四段叙事 0x1224..0x1227 ----
	var r9: Dictionary = gs.force_event(9)
	check(r9.get("msg_ids", []) == [0x1224, 0x1225, 0x1226, 0x1227], "id9 msg_ids = [0x1224..0x1227]")
	check(r9.get("msgs", []).size() == 4, "id9 渲染 4 段")
	var ok9: bool = true
	for ln in r9.get("msgs", []):
		if str(ln).length() == 0:
			ok9 = false
	check(ok9, "id9 四段叙事均非空")
	check(r9.get("outcome", {}).get("kind") == "local_event", "id9 outcome.kind = local_event")

	# ---- [3] force_event(10)：fire 经 sub-eval 显示 0x845/0x846 ----
	var r10: Dictionary = gs.force_event(10)
	check(r10.get("msg_ids", []) == [0x845, 0x846], "id10 msg_ids = [0x845,0x846]")
	check(r10.get("msgs", []).size() == 2 and str(r10["msgs"][0]).length() > 0, "id10 两段叙事非空")

	# ---- [4] force_event(15)：七路跳表公共尾 6 msg ----
	var r15: Dictionary = gs.force_event(15)
	check(r15.get("msg_ids", []) == [0x44, 0x53, 0x2b, 0x21, 0x24, 0x2f], "id15 msg_ids = 6 段")
	check(r15.get("msgs", []).size() == 6, "id15 渲染 6 段")

	# ---- [5] id13/14 仅门控、叙事未逆（narrative_pending=true, 无 MSG）----
	var r13: Dictionary = gs.force_event(13)
	check(r13.get("msg_ids", []).size() == 0, "id13 无叙事 MSG（仅 province 门控）")
	check(r13.get("narrative_pending", false) == true, "id13 narrative_pending = true（诚实未逆）")
	check(r13.get("outcome", {}).get("kind") == "scenario_trigger", "id13 outcome.kind = scenario_trigger")
	var r14: Dictionary = gs.force_event(14)
	check(r14.get("narrative_pending", false) == true, "id14 narrative_pending = true")

	# ---- [6] poll_events 按注入状态自动触发 10/13/14 ----
	gs.event_log.clear()
	gs.set_event_location(5, 2, 3)   # 国=5, 气候组=2, 关联国=3
	var fired: Array = gs.poll_events()
	var fired_ids: Array = []
	for f in fired:
		fired_ids.append(f.get("id"))
	check(fired_ids.has(10) and fired_ids.has(13) and fired_ids.has(14), "poll_events 触发 10/13/14（按注入状态）")
	check(fired_ids.size() == 3, "poll_events 恰好触发 3 个条件门控事件")
	# event_log 已写入
	check(gs.get_event_log().size() == 3, "event_log 记录 3 条触发")

	# ---- [7] 未定位不触发 ----
	gs.event_log.clear()
	gs.set_event_location(-1, -1, -1)
	var fired2: Array = gs.poll_events()
	check(fired2.size() == 0, "未定位（evt_*=-1）时 poll_events 不触发")
	check(gs.get_event_log().size() == 0, "未定位时 event_log 为空")

	# ---- [8] advance_month 驱动 poll_events（月度自动轮询）----
	gs.start_new_game(13)
	gs.set_event_location(7, 1, 7)
	gs.event_log.clear()
	gs.advance_month()   # 推进 1 月 → 内部 poll_events
	var log_after: Array = gs.get_event_log()
	var log_ids: Array = []
	for e in log_after:
		log_ids.append(e.get("id"))
	check(log_ids.has(10) and log_ids.has(13) and log_ids.has(14), "advance_month 驱动 poll_events 写入事件流")

	# ---- [9] 未开局不触发 ----
	gs.started = false
	gs.event_log.clear()
	var fired3: Array = gs.poll_events()
	check(fired3.size() == 0 and gs.get_event_log().size() == 0, "未开局 poll_events 不触发")

	# ---- 收尾 ----
	print("")
	if _fails == 0:
		print("[EVENT-EFFECTS PASS] 全部断言通过 ✅")
		quit(0)
	else:
		push_error("[EVENT-EFFECTS FAIL] %d 项断言失败 ❌" % _fails)
		quit(1)
