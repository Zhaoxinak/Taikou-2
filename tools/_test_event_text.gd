# _test_event_text.gd — M7 事件文本渲染（EventText）无头校验（extends SceneTree）
#
# 复刻结构：src/core/event_text.gd
# 比对参考实现：scripts/s15_event_bits_named.py（14 bit 语义 + MSGX 锚点）
#              msgx_all_texts.json（GameData.get_text 按全局 id 查）
#
# 覆盖：EVENT_DISPLAY 键集（10 个有 MSGX 锚点 bit）/ %s 模板填充主角名（bits 2/5/7）/
#   无 %s 事件原样返回 / 无锚点 bit(1/3/4/38) 返回空 / 委託 event_flags 命名 /
#   GameState.render_event_text + render_resolved_events 集成。
#
# 运行：Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_event_text.gd

extends SceneTree

const EventTextRef = preload("res://src/core/event_text.gd")
const EventFlagsRef = preload("res://src/core/event_flags.gd")

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
	var et: RefCounted = EventTextRef.new()
	var gs = root.get_node("/root/GameState")
	et._data = root.get_node("/root/GameData")   # 注入 GameData（非 autoload 无法解析全局名）
	gs.start_new_game(13)   # 织田信长（确保 GameData 文本已载入，供 _resolve_text 取 MSGX）

	# ---- [1] EVENT_DISPLAY 键集 = 有 MSGX 锚点的 10 个 bit ----
	var ev_keys: Array = EventTextRef.EVENT_DISPLAY.keys()
	ev_keys.sort()
	check(ev_keys == [2, 5, 6, 7, 8, 9, 10, 11, 14, 15], "EVENT_DISPLAY 键集 = 有锚点 10 bit")
	# 全部是 NAMED_BITS 子集
	var ok_subset: bool = true
	for k in ev_keys:
		if not EventFlagsRef.NAMED_BITS.has(int(k)):
			ok_subset = false
	check(ok_subset, "EVENT_DISPLAY 键 ⊆ NAMED_BITS")
	# 无 MSGX 锚点的 bit（1/3/4/38）故意不入 EVENT_DISPLAY
	var ok_absent: bool = true
	for k in [1, 3, 4, 38]:
		if EventTextRef.EVENT_DISPLAY.has(k):
			ok_absent = false
	check(ok_absent, "bit 1/3/4/38 故意不入 EVENT_DISPLAY（const/ref 锚点）")

	# ---- [2] %s 模板填充主角名（bit 7，玩家向文本）----
	var r7: Array[String] = et.render_event(7, "木下藤吉郎")
	check(r7.size() == 2, "bit 7 渲染 2 段")
	check(r7[0] == "啊，木下藤吉郎大人！你没事真是太好了！", "bit7[0] %s→主角名")
	check(r7[1] == "哦，木下藤吉郎，回来了！我正等着你呢！我已经从德川大人那里听说你英勇奋战的事了。", "bit7[1] %s→主角名")
	check("%s" != r7[0] and "%s" != r7[1], "bit7 渲染后无残留 %s")

	# ---- [3] %s 模板（bit 5，宣布+玩家向）----
	var r5: Array[String] = et.render_event(5, "木下藤吉郎")
	check(r5.size() == 2, "bit 5 渲染 2 段")
	check(r5[0] == "这次会议上，信长主公宣布拥戴足利义昭公上京都，接收明智光秀为家臣。", "bit5[0] 无%s原样")
	check(r5[1] == "木下藤吉郎大人，信长主公宣布拥戴足利义昭公上京都，明智光秀成为我家的家臣。", "bit5[1] %s→主角名")

	# ---- [4] %s 模板（bit 2，「…被%s掌握」）----
	var r2: Array[String] = et.render_event(2, "木下藤吉郎")
	check(r2.size() == 2, "bit 2 渲染 2 段")
	check(r2[1] == "旧足利领地的各地相继被木下藤吉郎掌握。", "bit2[1] %s→主角名（控制方近似）")

	# ---- [5] 无 %s 事件原样返回（bit 8 安土城）----
	var r8: Array[String] = et.render_event(8, "木下藤吉郎")
	check(r8.size() == 2, "bit 8 渲染 2 段（无%s）")
	check(r8[0] == "怎么样，来看看？这就是新城，取名安土城，意思是“平安乐土”。", "bit8[0] 原样")
	check(r8[1] == "是天守阁。", "bit8[1] 原样")

	# ---- [6] 无锚点 bit → 空 ----
	check(et.render_event(1, "x").size() == 0, "bit 1（无锚点）返回空")
	check(et.render_event(3, "x").size() == 0, "bit 3（无锚点）返回空")
	check(et.render_event(4, "x").size() == 0, "bit 4（无锚点）返回空")
	check(et.render_event(38, "x").size() == 0, "bit 38（无锚点）返回空")

	# ---- [7] 委託命名 ----
	check(et.event_name(8) == "安土城筑城 (1576)", "event_name(8) = 安土城筑城 (1576)")
	check(et.event_name(99) == "", "event_name(未知) = 空")

	# ---- [8] GameState 集成：render_event_text 用主角名 ----
	var g7: Array[String] = gs.render_event_text(7)
	check(g7.size() == 2, "GameState.render_event_text(7) 2 段")
	check(g7[0].contains("织田信长") and not g7[0].contains("%s"), "render_event_text(7) 填主角名 织田信长")

	# ---- [9] GameState 集成：render_resolved_events 回顾已触发事件 ----
	# 重置事件旗幟（清掉 init_for_protagonist 预置位），显式仅置 7/8，得确定 4 行。
	gs.event_flags.reset()
	gs.event_flags.set_a(7, 1)
	gs.event_flags.set_a(8, 1)
	var resolved: Array[String] = gs.render_resolved_events()
	check(resolved.size() == 4, "render_resolved_events 2 事件 × 2 段 = 4 行")
	var ok_all: bool = true
	for ln in resolved:
		if ln.contains("%s"):
			ok_all = false
	check(ok_all, "render_resolved_events 全部 %s 已填充（无残留）")
	check(resolved.has("怎么样，来看看？这就是新城，取名安土城，意思是“平安乐土”。"), "含 bit8 安土城文本")
	check(resolved.has("啊，织田信长大人！你没事真是太好了！"), "含 bit7 金崎撤退文本")

	# ---- 收尾 ----
	print("")
	if _fails == 0:
		print("[EVENT-TEXT PASS] 全部断言通过 ✅")
		quit(0)
	else:
		push_error("[EVENT-TEXT FAIL] %d 项断言失败 ❌" % _fails)
		quit(1)
