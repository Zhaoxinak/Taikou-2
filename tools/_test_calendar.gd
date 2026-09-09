# _test_calendar.gd — 游戏日历 / 时钟 复刻校验（calendar.gd）
#
# 依据 scripts/time_rollover_ref.py（0x4a0d50 进位链 + setter 夹紧，二进制自校验）。
# 校验：常量实证 / setter 夹紧 / 月末·年末进位 / 2 月 30 天（无闰年）/ 全年 360 天回环 / 年上限 1815。
# 运行：Godot --headless --script res://tools/_test_calendar.gd
#   ⚠️ 本机 --script 主循环失效时，逻辑由 scripts/_test_calendar_mirror.py（Python 等价镜像）复跑同一套断言验证。

extends SceneTree

const CalRef = preload("res://src/core/calendar.gd")

var _pass := 0
var _fail := 0


func _c(cond: bool, msg: String) -> void:
	if cond:
		_pass += 1
		print("  [ok] ", msg)
	else:
		_fail += 1
		print("  [FAIL] ", msg)


func _run() -> void:
	var C := CalRef
	# —— 常量实证（与反汇编字节一一对应）——
	_c(C.YEAR_BASE == 1560, "YEAR_BASE=1560")
	_c(C.YEAR_OFF_MAX == 255, "YEAR_OFF_MAX=255")
	_c(C.MONTH_MAX == 12, "MONTH_MAX=12")
	_c(C.DAY_MAX == 30, "DAY_MAX=30")
	_c(C.TICK_MAX == 23, "TICK_MAX=23")
	_c(C.TICKS_PER_DAY == 24, "TICKS_PER_DAY=24")
	_c(C.DAY_CARRY == 31, "DAY_CARRY=31")
	_c(C.MONTH_CARRY == 13, "MONTH_CARRY=13")
	_c(C.YEAR_MAX == 1815, "YEAR_MAX=1815")

	# —— setter 夹紧 ——
	_c(C.set_year_off(0) == 0, "set_year_off(0)=0")
	_c(C.set_year_off(255) == 255, "set_year_off(255)=255")
	_c(C.set_year_off(300) == 255, "set_year_off(300) clamp 255")
	_c(C.set_month(1) == 1 and C.set_month(12) == 12, "set_month 边界 1/12")
	_c(C.set_month(13) == 12 and C.set_month(0) == 1, "set_month clamp 0..12")
	_c(C.set_day(1) == 1 and C.set_day(30) == 30, "set_day 边界 1/30")
	_c(C.set_day(31) == 30 and C.set_day(0) == 1, "set_day clamp 1..30")
	_c(C.set_tick(0) == 0 and C.set_tick(23) == 23, "set_tick 边界 0/23")
	_c(C.set_tick(24) == 23 and C.set_tick(99) == 23, "set_tick clamp 0..23")

	# —— 单次进位：月末 01-30 + 1 tick(24) -> 02-01 ——
	var r: Array = C.advance(24, 0, 30, 1, 0)
	_c(r == [0, 1, 2, 0], "月末 01-30 +24tick -> 02-01 (got %s)" % str(r))
	# 月末不足 24 tick 不进日
	r = C.advance(23, 0, 30, 1, 0)
	_c(r == [23, 30, 1, 0], "月末 +23tick 不进位 (got %s)" % str(r))

	# —— 年末 12-30 + 1 tick -> 1561-01-01 ——
	r = C.advance(24, 0, 30, 12, 0)
	_c(r == [0, 1, 1, 1], "年末 12-30 +24tick -> 1561-01-01 (got %s)" % str(r))

	# —— 无闰年：2 月 30 天 ——
	var t: int = 1; var d: int = 1; var m: int = 2; var y: int = 0
	for _i in range(29):
		r = C.advance(24, t, d, m, y); t=r[0]; d=r[1]; m=r[2]; y=r[3]
	_c(d == 30 and m == 2 and y == 0, "2 月有 30 天 -> 02-30 (got %d/%d)" % [d, m])
	r = C.advance(24, t, d, m, y); t=r[0]; d=r[1]; m=r[2]; y=r[3]
	_c(d == 1 and m == 3, "02-30 -> 03-01（无 28/29）(got %d/%d)" % [d, m])

	# —— 全年 360 次 advance(24) -> 1561-01-01，且月<=12/日<=30 不变量 ——
	t=0; d=1; m=1; y=0
	var max_d := 0; var max_m := 0
	for _i in range(360):
		r = C.advance(24, t, d, m, y); t=r[0]; d=r[1]; m=r[2]; y=r[3]
		max_d = maxi(max_d, d); max_m = maxi(max_m, m)
	_c(d == 1 and m == 1 and y == 1, "1 年(360天) -> 1561-01-01 (got %d/%d/%d)" % [d, m, y])
	_c(max_d == 30, "不变量：日上限 30（无 31 天月）")
	_c(max_m == 12, "不变量：月上限 12")

	# —— roll_days / roll_months 便利函数 ——
	var rd: Array = C.roll_days(1, 30, 1, 0)
	_c(rd == [1, 2, 0], "roll_days(1, 01-30) -> 02-01 (got %s)" % str(rd))
	var rm: Array = C.roll_months(1, 15, 12, 0)
	_c(rm == [15, 1, 1], "roll_months(1, 12-15) -> 1561-01-15 (got %s)" % str(rm))
	# 跨年回环：12 次 roll_months(1) 从 1560-01 到 1561-01
	var acc: Array = [1, 1, 0]
	for _i in range(12):
		acc = C.roll_months(1, acc[0], acc[1], acc[2])
	_c(acc == [1, 1, 1], "12×roll_months(1) -> 1561-01 (got %s)" % str(acc))

	# —— 年上限 1815：YEAR_OFF=255 跨年仍 clamp 255 ——
	r = C.advance(24, 0, 30, 12, 255)
	_c(r[3] == 255 and r[2] == 1 and r[1] == 1, "年上限 1815：off 保持 255 不溢出 (got %s)" % str(r))

	print("\nRESULT: %d/%d checks passed" % [_pass, _pass + _fail])
	quit(0 if _fail == 0 else 1)


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)
