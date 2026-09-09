# _test_ai_diplomacy.gd — AI 主动外交（0x4a84e0）+ 国力（0x49faf0）校验
#
# 覆盖：
#   1) castle_contribution：(seisan×nousang)/25 + 100；城種&8 → +500；full_value=false → 减半
#   2) castle_sum：逐步 min(acc + contrib, 60000) 累加
#   3) prov_power：自国城力 + 従属国 ×2/3，再 ×(n+20)/20，byte[0x0d]&3==3 翻倍，全程 cap 60000
#   4) build_power_table：49 项
#   5) decide：LOOP1 挑国力最大者（主从=2）；LOOP2 邻国（主从=1）；开关 skip/ai_active
#   6) apply_diplo_gain：min(rel+2, 7)
#
# 逆向依据：scripts/ai_diplomacy_ref.py（续104）+ 实机反汇编 0x49faf0/0x49fbb0/
#           0x4ebc50(=(a*b)/c)/0x4ebca0(=min(a+b,c))；魔数 0x51eb851f+sar3=/25、
#           0x66666667+sar3=/20（已数值验证）。

extends SceneTree

const AiDiplomacy = preload("res://src/core/ai_diplomacy.gd")

var _pass := 0
var _fail := 0


func check(cond: bool, msg: String) -> void:
	if cond:
		_pass += 1
		print("[ok] " + msg)
	else:
		_fail += 1
		print("[FAIL] " + msg)


func _mk_ctx(sums: Array, mv_fn: Callable,
		neighbors: Array = [], b0c: Array = [], b0d: Array = []) -> Dictionary:
	if b0c.is_empty():
		b0c = []
		for i in AiDiplomacy.PROV_COUNT:
			b0c.append(0)
	if b0d.is_empty():
		b0d = []
		for i in AiDiplomacy.PROV_COUNT:
			b0d.append(0)
	var lord: Array = []
	for i in AiDiplomacy.PROV_COUNT:
		lord.append(0)   # 全部有效（< 370）
	var ctx := {
		"castle_sums": sums,
		"lord": lord,
		"b0c": b0c,
		"b0d": b0d,
		"get_mv": mv_fn,
		"neighbors": neighbors,
		"ai_active": true,
	}
	ctx["power"] = AiDiplomacy.build_power_table(ctx)
	return ctx


func _run() -> void:
	# 1) 单城贡献
	check(AiDiplomacy.castle_contribution(10, 10, 0) == 104,
		"城贡献 10x10/25+100 = 104（实得 %d）" % AiDiplomacy.castle_contribution(10, 10, 0))
	check(AiDiplomacy.castle_contribution(0, 0, 0) == 100,
		"空城仍有基数 100（实得 %d）" % AiDiplomacy.castle_contribution(0, 0, 0))
	check(AiDiplomacy.castle_contribution(10, 10, 8) == 604,
		"城種&8 → +500 = 604（实得 %d）" % AiDiplomacy.castle_contribution(10, 10, 8))
	check(AiDiplomacy.castle_contribution(10, 10, 8, false) == 302,
		"full_value=false → 减半 = 302（实得 %d）" % AiDiplomacy.castle_contribution(10, 10, 8, false))
	# /25 截断（非四舍五入）
	check(AiDiplomacy.castle_contribution(3, 3, 0) == 100,
		"9/25 截断为 0 → 100（实得 %d）" % AiDiplomacy.castle_contribution(3, 3, 0))

	# 2) 城力和累加（含 60000 上限）
	var two := [
		{"seisan": 10, "nousang": 10, "castle_type": 0},   # 104
		{"seisan": 10, "nousang": 10, "castle_type": 8},   # 604
	]
	check(AiDiplomacy.castle_sum(two) == 708,
		"城力和 104+604 = 708（实得 %d）" % AiDiplomacy.castle_sum(two))
	var big := [
		{"seisan": 255, "nousang": 255, "castle_type": 0},  # 2601+100=2701
		{"seisan": 255, "nousang": 255, "castle_type": 8},  # 3201
	]
	var s := AiDiplomacy.castle_sum(big)
	check(s == 5902, "城力和 2701+3201 = 5902（实得 %d）" % s)

	# 3) prov_power：自国 + 従属国(主从=3) 的 2/3
	var sums: Array = []
	for i in AiDiplomacy.PROV_COUNT:
		sums.append(0)
	sums[0] = 708
	sums[1] = 300
	var mv3 := func(i: int, j: int) -> int:
		return 3 if (i == 1 and j == 0) else 0
	var ctx := _mk_ctx(sums, mv3)
	var p0: int = AiDiplomacy.prov_power(ctx, 0)
	check(p0 == 908, "国力 = 708 + (300*2/3=200) = 908（实得 %d）" % p0)
	# 无従属时 = 自国城力（n=0 → ×20/20 = 1.0）
	var mv0 := func(i: int, j: int) -> int: return 0
	var ctx0 := _mk_ctx(sums, mv0)
	check(AiDiplomacy.prov_power(ctx0, 0) == 708,
		"无従属国 → 国力 = 自国城力 708（实得 %d）" % AiDiplomacy.prov_power(ctx0, 0))

	# 国力 nibble 放大：n=4 → ×24/20 = 1.2
	var b0c4: Array = []
	for i in AiDiplomacy.PROV_COUNT:
		b0c4.append(0)
	b0c4[0] = 4
	var ctxn := _mk_ctx(sums, mv0, [], b0c4)
	check(AiDiplomacy.prov_power(ctxn, 0) == 849,
		"n=4 → 708*24/20 = 849（实得 %d）" % AiDiplomacy.prov_power(ctxn, 0))
	# byte[0x0d]&3 == 3 → 翻倍
	var b0d3: Array = []
	for i in AiDiplomacy.PROV_COUNT:
		b0d3.append(0)
	b0d3[0] = 3
	var ctxd := _mk_ctx(sums, mv0, [], [], b0d3)
	check(AiDiplomacy.prov_power(ctxd, 0) == 1416,
		"b0d&3=3 → 708*2 = 1416（实得 %d）" % AiDiplomacy.prov_power(ctxd, 0))
	# 60000 上限
	var sums_huge: Array = []
	for i in AiDiplomacy.PROV_COUNT:
		sums_huge.append(0)
	sums_huge[0] = 59999
	sums_huge[1] = 59999
	var ctxh := _mk_ctx(sums_huge, mv3)
	check(AiDiplomacy.prov_power(ctxh, 0) <= AiDiplomacy.POWER_CAP,
		"国力封顶 60000（实得 %d）" % AiDiplomacy.prov_power(ctxh, 0))

	# 4) 国力表 49 项
	var pt := AiDiplomacy.build_power_table(ctx)
	check(pt.size() == 49, "国力表 49 项（实得 %d）" % pt.size())

	# 5) decide：LOOP1 挑主从=2 中国力最大者
	var sums2: Array = []
	for i in AiDiplomacy.PROV_COUNT:
		sums2.append(0)
	sums2[3] = 100   # 国力 100
	sums2[7] = 900   # 国力 900  ← 应被挑中
	sums2[9] = 500
	# 5 号是邻国，须返回 1 才会被 LOOP2 采纳（LOOP2 要求主从 == 1）
	var mv2 := func(i: int, j: int) -> int:
		if i in [3, 7, 9]:
			return 2
		if i == 5:
			return 1
		return 0
	var ctxd2 := _mk_ctx(sums2, mv2, [5])
	var d := AiDiplomacy.decide(ctxd2, 0)
	check(d.size() == 2, "decide 产出 LOOP1+LOOP2 共 2 条（实得 %d）" % d.size())
	if d.size() >= 1:
		check(int(d[0]["prov"]) == 7, "LOOP1 挑国力最大者 = 7（实得 %s）" % str(d[0]["prov"]))
		check(int(d[0]["msgx"]) == AiDiplomacy.MSGX_VASSAL, "LOOP1 MSGX = 0xd1f")
		check(int(d[0]["master_vassal"]) == 0, "LOOP1 解除主从 → 0")
		check(int(d[0]["diplo_delta"]) == 2, "LOOP1 外交 +2")
	if d.size() >= 2:
		check(int(d[1]["prov"]) == 5, "LOOP2 邻国 = 5（实得 %s）" % str(d[1]["prov"]))
		check(int(d[1]["msgx"]) == AiDiplomacy.MSGX_NEIGHBOR, "LOOP2 MSGX = 0xd1e")

	# 开关：skip / ai_active=false → 空
	var ctxskip := _mk_ctx(sums2, mv2, [5])
	ctxskip["skip"] = true
	check(AiDiplomacy.decide(ctxskip, 0).is_empty(), "skip 开关 → 不产出")
	var ctxoff := _mk_ctx(sums2, mv2, [5])
	ctxoff["ai_active"] = false
	check(AiDiplomacy.decide(ctxoff, 0).is_empty(), "ai_active=false → 不产出")

	# 6) 外交增益
	check(AiDiplomacy.apply_diplo_gain(0) == 2, "0 +2 = 2")
	check(AiDiplomacy.apply_diplo_gain(6) == 7, "6 +2 → 封顶 7（实得 %d）" % AiDiplomacy.apply_diplo_gain(6))
	check(AiDiplomacy.apply_diplo_gain(7) == 7, "已满 7 保持 7")

	# 注意：headless 下 process_frame 可能永不触发，禁止 await，直接 quit 退出
	if _fail == 0:
		print("ALL PASS (%d checks)" % _pass)
	else:
		print("FAILURES: %d / %d" % [_fail, _pass])
	quit(1 if _fail > 0 else 0)


func _initialize() -> void:
	# --script 模式下 autoload 尚未进树，挂首个 process_frame 再跑断言
	process_frame.connect(_run, CONNECT_ONE_SHOT)
