extends SceneTree
## EventSys 复刻自测（编译检查 + 待 --script 主循环恢复后实跑）
## 与 scripts/_test_event_sys_mirror.py 同一套断言。

const EventSysRef = preload("res://src/core/event_sys.gd")

# ⚠️ GDScript 不允许在函数内嵌套 func；且 lambda 捕获局部变量是按值，
#    计数会永远停在 0。故 _chk / fails 提到脚本级成员。
var fails : int = 0
var _pass : int = 0

func _chk(name: String, cond: bool) -> void:
	if cond:
		_pass += 1
		print("  [PASS] ", name)
	else:
		print("  [FAIL] ", name)
		fails += 1

func _run() -> void:
	fails = 0
	_pass = 0

	print("--- 1) 派发注册表结构 ---")
	var all_h : Array = []
	for v in EventSysRef.HANDLERS.values():
		for h in v:
			if h not in all_h: all_h.append(h)
	all_h.sort()
	_chk("49 个独立 handler", all_h.size() == 49)
	_chk("18 个事件 id", EventSysRef.HANDLERS.size() == 18)
	_chk("id 集合正确", EventSysRef.all_ids() == [0,1,2,3,4,5,6,7,8,9,10,11,13,14,15,16,17,29])
	var ok_addr := true
	for h in all_h:
		if h < 0x400000 or h >= 0x600000: ok_addr = false
	_chk("全部 handler 合法代码地址", ok_addr)
	_chk("边界 id 0x31 不在", not EventSysRef.HANDLERS.has(0x31))
	_chk("边界 id 0x3f 不在", not EventSysRef.HANDLERS.has(0x3f))
	_chk("0x490c0 笔误剔除", not (0x490c0 in all_h))
	_chk("0x4e82c0 ∈ id13&id14", (0x4e82c0 in EventSysRef.handlers_for(13)) and (0x4e82c0 in EventSysRef.handlers_for(14)))
	_chk("0x4e7e10 ∈ id10", 0x4e7e10 in EventSysRef.handlers_for(10))
	_chk("0x4b3ac0 ∈ id15", 0x4b3ac0 in EventSysRef.handlers_for(15))
	_chk("0x4b4b20/0x44ca90 ∈ id9", 0x4b4b20 in EventSysRef.handlers_for(9) and 0x44ca90 in EventSysRef.handlers_for(9))
	_chk("0x4499f0 ∈ id29（纠正非0/1）", 0x4499f0 in EventSysRef.handlers_for(29))
	_chk("0x484f34 ∈ id1", 0x484f34 in EventSysRef.handlers_for(1))
	_chk("0x4a3df3 ∈ id0", 0x4a3df3 in EventSysRef.handlers_for(0))

	print("--- 2) PREDICATES 全量 ---")
	_chk("PREDICATES 恰 49 条", EventSysRef.PREDICATES.size() == 49)
	var cov := true
	for h in all_h:
		if not EventSysRef.PREDICATES.has(h): cov = false
	_chk("PREDICATES 覆盖全部 handler", cov)
	_chk("0x4499f0 记为 id29", 29 in EventSysRef.PREDICATES[0x4499f0][0])
	_chk("0x461510 kind=thunk", EventSysRef.PREDICATES[0x461510][1] == "thunk")

	print("--- 3) taxonomy / EventListConfig ---")
	_chk("taxonomy 27 类", EventSysRef.TAXONOMY.size() == 27)
	_chk("EventListConfig 27×4", EventSysRef.EVENT_LIST_CONFIG.size() == 27
		and EventSysRef.EVENT_LIST_CONFIG[2].size() == 4)
	_chk("taxonomy 含 寺院/本能寺大火/结局",
		EventSysRef.taxonomy_name(2) != "" and EventSysRef.taxonomy_name(25) != "" and EventSysRef.taxonomy_name(28) != "")

	print("--- 4) 条件求值 0x4e82c0 ---")
	_chk("op13 cur==arg", EventSysRef.eval_4e82c0(13,5,5,0) == true)
	_chk("op13 cur!=arg", EventSysRef.eval_4e82c0(13,5,6,0) == false)
	_chk("op14 climate==arg", EventSysRef.eval_4e82c0(14,2,0,2) == true)
	_chk("op14 climate!=arg", EventSysRef.eval_4e82c0(14,4,0,2) == false)
	_chk("op99 不命中", EventSysRef.eval_4e82c0(99,0,0,0) == false)

	print("--- 5) 条件求值 0x4e7e10 ---")
	_chk("op10 assoc==arg", EventSysRef.eval_4e7e10(10,7,7,0) == true)
	_chk("op10 assoc!=arg", EventSysRef.eval_4e7e10(10,7,3,0) == false)
	_chk("op10 flags bit2 门控", EventSysRef.eval_4e7e10(10,7,7,2) == false)
	_chk("op9 非10", EventSysRef.eval_4e7e10(9,7,7,0) == false)

	print("--- 6) 每 tick 状态机 0x44d950 ---")
	_chk("TC_44DA00 正确", EventSysRef.TC_44DA00 == [0,4,1,4,4,4,4,2,4,3])
	_chk("JT_44D9EC 正确", EventSysRef.JT_44D9EC == [0,0,1,2,-1])
	_chk("global_mode==2 → EXIT", EventSysRef.tick_dispatch(0,2,0) == EventSysRef.BR_EXIT)
	_chk("global_mode==3 → EXIT", EventSysRef.tick_dispatch(0,3,0) == EventSysRef.BR_EXIT)
	_chk("arg_flags bit15 → EXIT", EventSysRef.tick_dispatch(0,0,0x8000) == EventSysRef.BR_EXIT)
	_chk("state<0 → EXIT", EventSysRef.tick_dispatch(-1,0,0) == EventSysRef.BR_EXIT)
	_chk("state>9 → EXIT", EventSysRef.tick_dispatch(10,0,0) == EventSysRef.BR_EXIT)
	_chk("state0 → DISPATCH_ID", EventSysRef.tick_dispatch(0,0,0) == EventSysRef.BR_DISPATCH_ID)
	_chk("state1 → EXIT", EventSysRef.tick_dispatch(1,0,0) == EventSysRef.BR_EXIT)
	_chk("state2 → DISPATCH_ID", EventSysRef.tick_dispatch(2,0,0) == EventSysRef.BR_DISPATCH_ID)
	_chk("state7 → STATE7", EventSysRef.tick_dispatch(7,0,0) == EventSysRef.BR_STATE7)
	_chk("state8 → EXIT", EventSysRef.tick_dispatch(8,0,0) == EventSysRef.BR_EXIT)
	_chk("state9 → TERMINAL", EventSysRef.tick_dispatch(9,0,0) == EventSysRef.BR_TERMINAL)
	var valid: Array = []
	for s in range(10):
		if EventSysRef.tick_dispatch(s,0,0) != EventSysRef.BR_EXIT: valid.append(s)
	_chk("有效状态恰 {0,2,7,9}", valid == [0,2,7,9])
	_chk("state0 id3→0x44da10", EventSysRef.state0_dispatch(3) == "0x44da10")
	_chk("state0 id15→0x44da90", EventSysRef.state0_dispatch(15) == "0x44da90")
	_chk("state0 其他 id 无路由", EventSysRef.state0_dispatch(5) == "")

	var res_text: String = "ALL PASS" if fails == 0 else ("%d FAIL" % fails)
	print("RESULT: %s (%d/%d)" % [res_text, _pass, _pass + fails])
	quit(0 if fails == 0 else 1)


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)
