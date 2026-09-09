# _test_council.gd — 評定 / 任务分配 纯逻辑校验（council.gd）
#
# 依据 scripts/council_ref.py（16/16）+ scripts/council_report_ref.py（18/18）+ council_tails_ref.py（29/29）。
# 校验：12 主命常量 / 13 报告 handler→MSGX 映射 / count_asked / rand_avail /
#       report_index 选取状态机(0x460420) 18 例 / target_name 四段路由 / menu_items / dispatch。
# 运行：Godot --headless --script res://tools/_test_council.gd
#   ⚠️ 本机 --script 主循环失效时，逻辑由 scripts/_test_council_mirror.py（Python 等价镜像）复跑同一套断言验证。

extends SceneTree

const CouncilRef = preload("res://src/core/council.gd")

var _pass := 0
var _fail := 0


func _c(cond: bool, msg: String) -> void:
	if cond:
		_pass += 1
		print("  [ok] ", msg)
	else:
		_fail += 1
		print("  [FAIL] ", msg)


# 可控伪随机：依次吐出预设序列（忽略 n），与 council_report_ref.SeqRng 一致
class SeqRng:
	var seq: Array = []
	var i: int = 0
	func pull(n: int) -> int:
		var v: int = int(seq[i % seq.size()])
		i += 1
		return v


# ⚠️ SeqRng 是 RefCounted：若不持有引用，_new_rng 返回后即被释放，
#    Callable 会变成 null instance（报 'null::pull'）。故缓存在 _rngs。
var _rngs: Array = []

func _new_rng(vals: Array) -> Callable:
	var s := SeqRng.new()
	s.seq = vals
	_rngs.append(s)
	return Callable(s, "pull")


func _run() -> void:
	var C = CouncilRef

	# —— 常量 / 表 ——
	_c(C.HANDLER_COUNT == 13, "HANDLER_COUNT=13")
	_c(C.ID_MERCHANT == 17 and C.ID_CASTLE == 22, "ID 特例 17/22")
	_c(C.TASK_NAMES == ["贩卖军粮","购买军粮","军马","洋枪","开垦农田","改建",
		"筑城","进贡","威吓","朝廷工作","收集情报","谋略"], "12 主命名表")
	_c(C.report_msg_id(1) == 0x1202 and C.report_msg_id(12) == 0x120E, "报告→MSGX 映射 1/12")
	_c(C.report_msg_id(0) == -1, "报告 handler[0] 无 MSGX（-1）")
	_c(C.STR_MERCHANT == "商　人" and C.STR_STOP == "停　止", "「商　人」/「停　止」特例串")

	# —— count_asked（0x460500）——
	_c(C.count_asked([5, 0x8005, 0x8001]) == 2, "count_asked 统计 bit15 已询问数 = 2")
	_c(C.count_asked([1, 2, 3]) == 0, "count_asked 无已询问 = 0")

	# —— rand_avail（0x460530）——
	_c(C.rand_avail([1,1,1,1,1,1,1,1,1,1,1,1,1], _new_rng([0])) == 0, "rand_avail 槽0 可用 -> 0")
	_c(C.rand_avail([0,0,0,0,0,1,0,0,0,0,0,0,0], _new_rng([5])) == 5, "rand_avail 仅在非零槽挑（槽5）")
	_c(C.rand_avail([0,0,0,0,0,0,0,0,0,0,0,0,0], _new_rng([0])) == 0, "rand_avail 全 0 退化 -> 0")

	# —— report_index（0x460420）18 例（与 council_report_ref.self_test 一致）——
	var S: Array = []
	for _i in 13:
		S.append(1)
	_c(C.report_index(9, 5, 1, 0, 0, S, _new_rng([0])) == 0, "d9 c>=3 a1 -> 0")
	_c(C.report_index(9, 5, 2, 0, 0, S, _new_rng([0])) == 1, "d9 c>=3 a2 -> 1")
	_c(C.report_index(9, 5, 3, 0, 0, S, _new_rng([0])) == 0, "d9 c>=3 a3 -> rand_avail(0)")
	_c(C.report_index(9, 5, 4, 0, 0, S, _new_rng([0])) == 0, "d9 c>=3 a>=4 -> 0")
	_c(C.report_index(9, 2, 1, 0, 0, S, _new_rng([40])) == 0, "d9 c<3 a1 lo(40) -> 0")
	_c(C.report_index(9, 2, 1, 0, 0, S, _new_rng([39])) == 1, "d9 c<3 a1 hi(39) -> 1")
	_c(C.report_index(9, 2, 0, 0, 0, S, _new_rng([0])) == 0, "d9 c<3 a0 -> rand_avail(0)")
	_c(C.report_index(5, 3, 1, 0, 0, S, _new_rng([39])) == 1, "d!9 a1 c>1 hi -> 1")
	_c(C.report_index(5, 3, 1, 0, 0, S, _new_rng([40])) == 0, "d!9 a1 c>1 lo -> 0")
	_c(C.report_index(5, 1, 1, 0, 0, S, _new_rng([0])) == 0, "d!9 a1 c<=1 -> rand_avail(0)")
	_c(C.report_index(0, 2, 2, 0, 1, S, _new_rng([0])) == 12, "d0 a2 flag8 -> 12(米価)")
	_c(C.report_index(1, 2, 2, 0, 1, S, _new_rng([0])) == 12, "d1 a2 flag8 -> 12")
	_c(C.report_index(0, 2, 2, 0, 0, S, _new_rng([3])) == 3, "d0 a2 noflag8 -> rand_avail(3)")
	_c(C.report_index(2, 2, 2, 1, 0, S, _new_rng([0])) == 11, "d2 a2 flag6 -> 11(馬販子)")
	_c(C.report_index(2, 2, 2, 0, 0, S, _new_rng([3])) == 3, "d2 a2 noflag6 -> rand_avail(3)")
	_c(C.report_index(7, 2, 2, 0, 0, S, _new_rng([3])) == 3, "d7 a2 -> rand_avail(3)")
	_c(C.report_index(5, 5, 0, 0, 0, S, _new_rng([3])) == 3, "a0 -> rand_avail(3)")
	var only5 := [0,0,0,0,0,1,0,0,0,0,0,0,0]
	_c(C.report_index(5, 5, 0, 0, 0, only5, _new_rng([5])) == 5, "avail-only(槽5) -> 5")

	# —— target_name 四段路由（0x49c2b0）——
	var off_resolver := func(v: int) -> String:
		return ("武将%d" % v) if v < 1000 else ""
	_c(C.target_name(17) == "商　人", "target_name(17) -> 「商　人」特例")
	_c(C.target_name(0, off_resolver) == "武将0", "target_name(0) -> 武将名（resolver）")
	_c(C.target_name(1000, off_resolver) == "NPC1000", "target_name(1000) -> 名表未导出占位 NPC1000")
	_c(C.target_name(3000, off_resolver) == "NPC3000", "target_name(3000) -> 占位 NPC3000")

	# —— menu_items（0x460320）——
	var items: Array[String] = C.menu_items([0, 1, 17], [0, 1000], off_resolver)
	_c(items == ["武将0", "NPC1000", "商　人", "停　止"], "menu_items: 3 条目 + 「停　止」(got %s)" % str(items))

	# —— dispatch（0x4603f0）——
	_c(C.dispatch(22)["kind"] == "special_22", "dispatch(22) -> 築城業者特例")
	_c(C.dispatch(5)["kind"] == "handler", "dispatch(5) -> handler 表")

	print("\nRESULT: %d/%d checks passed" % [_pass, _pass + _fail])
	quit(0 if _fail == 0 else 1)


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)
