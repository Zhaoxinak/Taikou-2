extends RefCounted
## calendar.gd — 游戏日历 / 时钟（原版 0x4a0d50 进位链 + 0x49a120..0x49a1a0 setter）
##
## 复刻 scripts/time_rollover_ref.py（capstone 反汇编 + 二进制自校验，无数据依赖）。
## 设计：与 weather.gd / diplomacy.gd 一致，**自含、不依赖 GameData**；
##   随机数/状态由调用方注入，便于确定性测试。本模块只提供纯函数（进位链 + setter 夹紧）。
##
## 原版函数对应
## --------------
##   0x4a0d50  advance(tick_delta)        游戏时钟主推进（每帧 delta=1），读取全局 [0x5205f0..0x5205f3]
##   0x49a120  setYear(year)   -> byte[0x5205f0] = (year-1560) 夹紧 [0,255]
##   0x49a140  setMonth(m)     -> byte[0x5205f1] = clamp(m,1,12)
##   0x49a170  setDay(d)       -> byte[0x5205f2] = clamp(d,1,30)
##   0x49a1a0  setTick(t)      -> byte[0x5205f3] = clamp(t,0,23)
##
## 结论（实证）：所有月份均为 30 天、每年 12 个月、无闰年；
##   日进位阈值 31（day 上限 30）、月进位阈值 13（month 上限 12）；
##   年上限 1560+255 = 1815（单字节宽度）。

# ── 实证常量（与 time_rollover_ref.py 一一对应）──
const YEAR_BASE      : int = 0x618   # 1560，0x49a120 中 add eax,0xfffff9e8 (= -0x618)
const YEAR_OFF_MAX   : int = 0xff    # 255，年上限 1815
const MONTH_MAX      : int = 0xc     # 12
const MONTH_MIN      : int = 1
const DAY_MAX        : int = 0x1e     # 30
const DAY_MIN        : int = 1
const TICK_MAX       : int = 0x17     # 23
const TICKS_PER_DAY  : int = 0x18     # 24
const DAY_CARRY      : int = 0x1f     # 31，日进位阈值
const MONTH_CARRY    : int = 0xd     # 13，月进位阈值
const YEAR_MAX       : int = YEAR_BASE + YEAR_OFF_MAX   # 1815


# ── setter（复刻 0x49a120/0x49a140/0x49a170/0x49a1a0，夹紧写回）──
static func set_year_off(off: int) -> int:
	return clampi(off, 0, YEAR_OFF_MAX)

static func set_month(m: int) -> int:
	return clampi(m, MONTH_MIN, MONTH_MAX)

static func set_day(d: int) -> int:
	return clampi(d, DAY_MIN, DAY_MAX)

static func set_tick(t: int) -> int:
	return clampi(t, 0, TICK_MAX)


## 0x4a0d50 单次进位（delta = 计时增量，实机每帧=1）。
## 入参 (t,d,m,yoff) 为当前 tick/day/month/year_off；返回 [t,d,m,yoff]（已夹紧）。
## 注：每帧至多进 1 日（TICK>=24 时只 inc DAY 一次），与原版一致。
static func advance(delta: int, t: int, d: int, m: int, yoff: int) -> Array:
	t = set_tick(t)
	yoff = set_year_off(yoff)
	m = set_month(m)
	d = set_day(d)
	t += delta
	if t >= TICKS_PER_DAY:
		t = t % TICKS_PER_DAY
		d += 1
		if d == DAY_CARRY:            # 31 -> 进月
			m += 1
			d = 1
			if m == MONTH_CARRY:      # 13 -> 进年，月归 1
				yoff = set_year_off(yoff + 1)
				m = 1
	yoff = set_year_off(yoff)
	m = set_month(m)
	d = set_day(d)
	t = set_tick(t)
	return [t, d, m, yoff]


## 一次推进 n 天（每天 = 24 tick，逐日携带进位；tick 归 0）。
## 入参 (d,m,yoff) 当前 day/month/year_off；返回 [new_day, new_month, new_year_off]。
static func roll_days(n: int, d: int, m: int, yoff: int) -> Array:
	var t: int = 0
	for _i in range(maxi(0, n)):
		var r: Array = advance(TICKS_PER_DAY, t, d, m, yoff)
		t = int(r[0]); d = int(r[1]); m = int(r[2]); yoff = int(r[3])
	return [d, m, yoff]


## 一次推进 n 月（月进位，年进位；day 保持并钳到 30）。
## 入参 (d,m,yoff) 当前 day/month/year_off；返回 [new_day, new_month, new_year_off]。
static func roll_months(n: int, d: int, m: int, yoff: int) -> Array:
	var y: int = set_year_off(yoff)
	var mm: int = set_month(m)
	var dd: int = set_day(d)
	for _i in range(maxi(0, n)):
		mm += 1
		if mm > MONTH_MAX:
			mm = 1
			y = set_year_off(y + 1)
	dd = set_day(dd)
	mm = set_month(mm)
	y = set_year_off(y)
	return [dd, mm, y]


## 由 year_off 还原绝对年
static func year_of(yoff: int) -> int:
	return YEAR_BASE + set_year_off(yoff)
