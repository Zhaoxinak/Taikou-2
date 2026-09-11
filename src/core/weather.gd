# weather.gd — 天气 / 季节系统（原版逐指令 1:1 复刻）
#
# 逆向依据：scripts/weather_ref.py（含概率表 0x5037b8.. 映像自校验 + 蒙特卡洛）
#           来源 = 脱壳映像 scripts/_unpacked_mem.bin（基址 0x400000）逐指令反汇编。
#
# 原版函数对应
# --------------
#   0x43cad0  getWeather()          -> word[0x513530]
#   0x43cae0  setWeather(w)         -> word[0x513530] = w
#   0x43caf0  bucket()              -> 0 if w==0 else (2 if w>2 else 1)（晴/雨系/雪 3 档）
#   0x43cb10  getWetFlag()          -> dword[0x51352c]（降水/湿润标志）
#   0x43cb20  setWetFlag(v)         -> dword[0x51352c] = v
#   0x43cfc0  tick_simple()         简版（无地域），调用点 0x4347b6（counter%4==0）
#   0x43d0e0  tick_region()         完整版（含地域气候），调用点 0x434e6c
#   0x43d060  _transition(threshold, mode)
#
# 天气状态编码 word[0x513530]：0=晴 1=曇(阴) 2=雨 3=雪
# 季节 = (月 // 3) & 3 ⇒ 0=冬{12,1,2} 1=春{3,4,5} 2=夏{6,7,8} 3=秋{9,10,11}；月份源 byte[0x5205f1]
# 地域气候：byte[0x519548 + 国id*5 + 1]（国id = word[0x524866] < 49）；气候组 ∈ {0,2,4} ⇒ 雪国
#
# 概率表（静态，单位=百分比，语义 =「天气保持不变」的概率）：
#   0x5037b8  T_SIMPLE  [season*3 + weather]      简版
#   0x5037c5  T_SEASON  [season*3 + weather]      完整版·非冬季用（前导 3 字节 0；stride=3 而列有 4，
#                                                  weather==3 会 alias 到下一行首列 —— 原版如此非笔误）
#   0x5037d4  T_WINTER_SNOWREG / 0x5037d8  T_WINTER_NORMAL [weather]  冬季·雪国/非雪国
#
# 战斗联动：0x42d62e 读 getWetFlag()，非零且兵种类别 kind==2（铁炮/洋枪）⇒ 战力 ×2/3
#   （0x42d643 shl eax,1; imul 0x55555556）—— 已提供 gun_strength_penalty 纯函数，
#   待 battle_sim 补兵种类别概念后接线。
#
# 设计：与 diplomacy.gd / ai_diplomacy.gd 一致，**自含、不依赖 GameData**。
#   随机数由调用方注入（`rnd(n) -> [0,n) 均匀整数`，缺省 = randi()%n，等价 0x4ebd60 rand()%n），
#   便于确定性测试。实例即「一份天气运行时状态」。

class_name WeatherState
extends RefCounted

# ── 天气/季节常量 ──────────────────────────────────────────
const CLEAR  : int = 0
const CLOUDY : int = 1
const RAIN   : int = 2
const SNOW   : int = 3

const WEATHER_NAMES : Array[String] = ["晴", "曇", "雨", "雪"]
const SEASON_NAMES  : Array[String] = ["冬", "春", "夏", "秋"]
const SNOW_CLIMATE_GROUPS : Array[int] = [0, 2, 4]   # 气候组 ∈ 此集合 ⇒ 雪国

# 简版 12B（season*3+weather，weather 只到 2）
const T_SIMPLE : Array[int] = [
	90, 80, 40,   # 冬: 晴 曇 雨
	80, 60, 70,   # 春
	90, 20, 50,   # 夏
	80, 60, 90]   # 秋

# 完整版 15B（非冬季；索引 season*3+weather，season 只取 1..3；weather==3 alias 下一行首列）
const T_SEASON : Array[int] = [
	0, 0, 0,
	70, 60, 50,   # 春
	80, 20, 60,   # 夏
	60, 50, 70,   # 秋
	0, 0, 0]

# 冬季
const T_WINTER_SNOWREG : Array[int] = [20, 50, 0]   # 雪国   晴/曇/雨 保持率
const T_WINTER_NORMAL  : Array[int] = [90, 40, 20]  # 非雪国 晴/曇/雨 保持率


# 整数除法（非负；避开 GDScript 整型除法语义歧义）
static func _idiv(a: int, b: int) -> int:
	if b == 0:
		return 0
	return floori(float(a) / float(b))


## 季节编码 0x43cfe9 / 0x43d0f9：((月 // 3) & 3)；月为正 ⇒ 0=冬{12,1,2} 1=春 2=夏 3=秋
static func season_of(month: int) -> int:
	return int(month / 3) & 3


## 3 档归类 0x43caf0：0=晴档 1=雨档(曇/雨) 2=雪档
static func bucket_of(w: int) -> int:
	if w == 0:
		return 0
	return 2 if w > 2 else 1


## 战斗联动 0x42d62e：降水(湿润)且 kind==2（铁炮/洋枪）⇒ 战力 ×2/3（向下取整）
static func gun_strength_penalty(strength: int, wet_flag: int, kind: int) -> int:
	if wet_flag != 0 and kind == 2:
		return _idiv(strength * 2, 3)
	return strength


# 缺省随机源：等价原版 0x4ebd60 rand()%n
static func _default_rnd(n: int) -> int:
	return randi() % n


# ── 运行时状态 ─────────────────────────────────────────────
var w   : int = CLEAR    # word[0x513530]
var wet : int = 0        # dword[0x51352c]（降水/湿润标志）
var _rnd : Callable = Callable()


func _init(weather: int = CLEAR, wet_flag: int = 0, rnd: Callable = Callable()) -> void:
	w = weather
	wet = wet_flag
	_rnd = rnd if rnd.is_valid() else _default_rnd


func set_weather(v: int) -> void:   # 0x43cae0
	w = v


func get_weather() -> int:          # 0x43cad0
	return w


func bucket() -> int:
	return bucket_of(w)


func weather_name() -> String:
	if w >= 0 and w < WEATHER_NAMES.size():
		return WEATHER_NAMES[w]
	return "?"


## 表现层预设映射：晴/曇→晴、雨、雪（供战斗场景天气表现使用）
const PRESENTATION_KIND : Array[String] = ["晴", "晴", "雨", "雪"]

func presentation_kind() -> String:
	if w >= 0 and w < PRESENTATION_KIND.size():
		return PRESENTATION_KIND[w]
	return "晴"


## 0x43d060 weather_transition(threshold, mode) -> 新天气或 -1（保持不变）
## mode：0=通用（简版/非冬季） 1=冬季非雪国 2=冬季雪国
func _transition(threshold: int, mode: int, r1: int) -> int:
	if r1 < threshold:
		return -1                     # 0x43d074 or ax,0xffff → 不变
	if w == 0:                        # 0x43d084
		return CLOUDY
	if w == 1:                        # 0x43d08b
		if mode == 2:                 # 0x43d091 雪国冬季：曇 90% 直接转雪
			return CLEAR if _rnd.call(100) < 10 else SNOW
		return CLEAR if (r1 & 1) != 0 else RAIN   # 0x43d0b0 奇→晴 偶→雨
	return SNOW if mode != 0 else CLOUDY          # 0x43d0ce


## 0x43cfc0 简版（无地域）
func tick_simple(month: int) -> void:
	var r1 : int = _rnd.call(100)
	if w == SNOW:                     # 0x43cfd4
		if r1 < 20:                   # 0x43cfda cmp si,0x14
			wet ^= 1                  # 0x43cfe0 xor dword[0x51352c],1
		return
	var s : int = season_of(month)
	var thr : int = T_SIMPLE[s * 3 + w]            # 0x43d019
	var new : int = _transition(thr, 0, r1)
	if new < 0:
		return
	wet = 1 if new == RAIN else 0     # 0x43d034
	w = new


## 0x43d0e0 完整版（含地域气候）
## climate_group = byte[0x519548 + 国id*5 + 1]；国id>=49 时原版传 0
func tick_region(month: int, climate_group: int) -> void:
	var r1 : int = _rnd.call(100)
	var s : int = season_of(month)

	if s != 0:                                        # 0x43d146 非冬季
		var nw_season : int = _transition(T_SEASON[s * 3 + w], 0, r1)  # 0x43d248
		if nw_season < 0:
			return
		wet = 1 if nw_season == RAIN else 0           # 0x43d265
		w = nw_season
		return

	var snow_region : bool = climate_group in SNOW_CLIMATE_GROUPS   # 0x43d14f..15a

	if w == SNOW:
		var thr_snow : int
		var cut : int
		if snow_region:                               # 0x43d1c5
			thr_snow = 80 if wet != 0 else 60
			cut = 70                                  # 0x43d1f5 cmp bx,0x46
		else:                                         # 0x43d166
			thr_snow = 20 if wet != 0 else 40
			cut = 80                                  # 0x43d199 cmp bx,0x50
		if r1 < thr_snow:
			return                                    # 保持
		if wet != 0:
			wet = 0
			w = SNOW
		elif r1 >= cut:
			wet = 1
			w = SNOW
		else:
			wet = 0
			w = CLEAR
		return

	var mode_w : int
	var thr_w : int
	if snow_region:                                   # 0x43d201
		mode_w = 2
		thr_w = T_WINTER_SNOWREG[w]
	else:                                             # 0x43d1ac
		mode_w = 1
		thr_w = T_WINTER_NORMAL[w]
	var nw : int = _transition(thr_w, mode_w, r1)
	if nw < 0:
		return
	wet = 1 if (nw == RAIN or nw == SNOW) else 0      # 0x43d223/0x43d233
	w = nw
