# _test_weather.gd — 天气/季节系统 1:1 移植校验（weather.gd）
#
# 依据 scripts/weather_ref.py（0x43cfc0 简版 / 0x43d0e0 完整版逐指令复刻）。
# 校验方式：随机源注入「确定性队列」（pop_front），与 Python 等价镜像推导的期望值比对。
#   - 17 个显式场景（雪持续/转晴/转雨/雪国冬季分歧/alias 等）
#   - 24 个月长跑轨迹（region, climate=0 雪国, 每月 7 tick，队列 = (i*37+11)%100）
# 运行：Godot_v4.7.1 --headless --script res://tools/_test_weather.gd

extends SceneTree

const WeatherRef = preload("res://src/core/weather.gd")

var _pass := 0
var _fail := 0


func _c(cond: bool, msg: String) -> void:
	if cond:
		_pass += 1
		print("  [ok] ", msg)
	else:
		_fail += 1
		print("  [FAIL] ", msg)


## 确定性随机队列：每次 rnd(n) 从队首弹一个值（空则 0）
func _queue_rnd(vals: Array) -> Callable:
	var q: Array = vals.duplicate()
	return func(n: int) -> int:
		if q.is_empty():
			return 0
		return int(q.pop_front())


## 跑单步场景并返回 (w, wet)
func _run_scen(w0: int, wet0: int, vals: Array, simple: bool, month: int, climate: int) -> Array:
	var st = WeatherRef.new(w0, wet0, _queue_rnd(vals))
	if simple:
		st.tick_simple(month)
	else:
		st.tick_region(month, climate)
	return [int(st.w), int(st.wet)]


func _run() -> void:
	var W = WeatherRef
	_c(W.CLEAR == 0 and W.CLOUDY == 1 and W.RAIN == 2 and W.SNOW == 3, "天气常量 晴/曇/雨/雪 = 0..3")

	# —— 表 ——
	_c(W.T_SIMPLE == [90, 80, 40, 80, 60, 70, 90, 20, 50, 80, 60, 90], "T_SIMPLE 12B 与映像一致")
	_c(W.T_SEASON == [0, 0, 0, 70, 60, 50, 80, 20, 60, 60, 50, 70, 0, 0, 0], "T_SEASON 15B 与映像一致（含前导 3 字节 0）")
	_c(W.T_WINTER_SNOWREG == [20, 50, 0], "T_WINTER_SNOWREG 与映像一致")
	_c(W.T_WINTER_NORMAL == [90, 40, 20], "T_WINTER_NORMAL 与映像一致")
	_c(W.WEATHER_NAMES == ["晴", "曇", "雨", "雪"], "天气名表")
	_c(W.SEASON_NAMES == ["冬", "春", "夏", "秋"], "季节名表")
	_c(W.SNOW_CLIMATE_GROUPS == [0, 2, 4], "雪国气候组 {0,2,4}")
	_c(W.PRESENTATION_KIND == ["晴", "晴", "雨", "雪"], "表现层预设映射（曇→晴回落）")

	# —— 季节 ——
	_c(W.season_of(1) == 0 and W.season_of(2) == 0 and W.season_of(12) == 0, "冬 {12,1,2} -> 0")
	_c(W.season_of(3) == 1 and W.season_of(4) == 1 and W.season_of(5) == 1, "春 {3,4,5} -> 1")
	_c(W.season_of(6) == 2 and W.season_of(7) == 2 and W.season_of(8) == 2, "夏 {6,7,8} -> 2（season_of=(月//3)&3，6//3=2）")
	_c(W.season_of(9) == 3 and W.season_of(10) == 3 and W.season_of(11) == 3, "秋 {9,10,11} -> 3")

	# —— 分档 / 战斗联动 ——
	_c(W.bucket_of(0) == 0 and W.bucket_of(1) == 1 and W.bucket_of(2) == 1 and W.bucket_of(3) == 2, "bucket 3 档（晴/雨系/雪）")
	var bk := WeatherRef.new(3, 1)
	_c(bk.bucket() == 2, "实例 bucket 雪 -> 2")
	_c(bk.weather_name() == "雪", "实例天气名 雪")
	bk.set_weather(0)
	_c(bk.presentation_kind() == "晴", "presentation 晴")
	_c(W.gun_strength_penalty(300, 0, 2) == 300, "gun 未降水 300")
	_c(W.gun_strength_penalty(300, 1, 2) == 200, "gun 降水 kind2 -> 200")
	_c(W.gun_strength_penalty(301, 1, 2) == 200, "gun 301 -> 200（向下取整）")
	_c(W.gun_strength_penalty(300, 1, 1) == 300, "gun kind!=2 不惩罚")
	_c(W.gun_strength_penalty(0, 1, 2) == 0, "gun 0 战力")

	# —— 显式场景（期望值来自 Python 等价镜像）——
	var exp := {
		"s1": [3, 1], "s2": [3, 1], "s3": [1, 0], "s4": [2, 1], "s5": [0, 0],
		"s6": [2, 1], "s7": [1, 0], "s8": [1, 0], "s9": [2, 1],
		"s10": [3, 1], "s11": [0, 0], "s12": [3, 1], "s13": [3, 0],
		"s14": [0, 0], "s15": [3, 0], "s16": [3, 1], "s17": [2, 0],
	}
	var scen := {
		# 简版：降雪 toggle wet / 持续 / 晴->曇 / 曇->雨(偶) / 曇->晴(奇)
		"s1": {"w": 3, "wet": 0, "q": [10], "simple": true, "m": 1, "c": 0},
		"s2": {"w": 3, "wet": 1, "q": [30], "simple": true, "m": 2, "c": 0},
		"s3": {"w": 0, "wet": 0, "q": [90], "simple": true, "m": 2, "c": 0},
		"s4": {"w": 1, "wet": 0, "q": [80], "simple": true, "m": 2, "c": 0},
		"s5": {"w": 1, "wet": 0, "q": [81], "simple": true, "m": 2, "c": 0},
		# region：春 曇->雨 / 春 雪 alias->曇 / 冬非雪国 晴->曇 / 曇->雨 / 冬雨保持
		"s6": {"w": 1, "wet": 0, "q": [60], "simple": false, "m": 4, "c": 0},
		"s7": {"w": 3, "wet": 1, "q": [80], "simple": false, "m": 4, "c": 0},
		"s8": {"w": 0, "wet": 0, "q": [90], "simple": false, "m": 12, "c": 1},
		"s9": {"w": 1, "wet": 0, "q": [40], "simple": false, "m": 12, "c": 1},
		"s17": {"w": 2, "wet": 0, "q": [0], "simple": false, "m": 12, "c": 1},
		# region：冬雪国 曇 分歧（rnd<10 -> 雪 / >=10 -> 晴）/ 雪持续(湿) / 湿雪转干雪
		"s10": {"w": 1, "wet": 0, "q": [50, 30], "simple": false, "m": 1, "c": 0},
		"s11": {"w": 1, "wet": 0, "q": [50, 5], "simple": false, "m": 1, "c": 0},
		"s12": {"w": 3, "wet": 1, "q": [79], "simple": false, "m": 1, "c": 0},
		"s13": {"w": 3, "wet": 1, "q": [80], "simple": false, "m": 1, "c": 0},
		"s14": {"w": 3, "wet": 0, "q": [65], "simple": false, "m": 1, "c": 0},
		"s15": {"w": 3, "wet": 0, "q": [30], "simple": false, "m": 1, "c": 0},
		"s16": {"w": 2, "wet": 0, "q": [0], "simple": false, "m": 1, "c": 0},
	}
	for name in scen:
		var s: Dictionary = scen[name]
		var got: Array = _run_scen(int(s["w"]), int(s["wet"]), s["q"],
			bool(s["simple"]), int(s["m"]), int(s["c"]))
		var want: Array = exp[name]
		_c(got[0] == want[0] and got[1] == want[1],
			"%s -> (w=%d,wet=%d) 期望 (%d,%d)" % [name, int(got[0]), int(got[1]), int(want[0]), int(want[1])])

	# —— 24 个月长跑（region, climate=0 雪国，每月 7 tick）——
	var w_exp := [3, 3, 1, 0, 0, 1, 2, 1, 2, 2, 2, 3, 3, 1, 2, 0, 1, 1, 2, 1, 2, 2, 2, 3]
	var wet_exp := [1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0]
	var q: Array = []
	for i in range(260):
		q.append((i * 37 + 11) % 100)
	var wx = WeatherRef.new(0, 0, _queue_rnd(q))
	var idx := 0
	for y in range(2):
		for m in range(1, 13):
			for t in range(7):
				wx.tick_region(m, 0)
			_c(int(wx.w) == int(w_exp[idx]) and int(wx.wet) == int(wet_exp[idx]),
				"长跑 月%d w=%d wet=%d（期望 %d,%d）" % [m, int(wx.w), int(wx.wet), int(w_exp[idx]), int(wet_exp[idx])])
			idx += 1

	print()
	if _fail == 0:
		print("ALL PASS (%d checks)" % _pass)
		quit(0)
	else:
		print("FAILURES: %d / %d" % [_fail, _pass])
		quit(1)


func _initialize() -> void:
	# --script 模式下 autoload 尚未进树，挂首个 process_frame 再跑断言
	process_frame.connect(_run, CONNECT_ONE_SHOT)
