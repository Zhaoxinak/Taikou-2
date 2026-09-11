extends Node
## GameState — 游戏逻辑单例（Autoload），M3 最小可玩核心 + M4 内政与修行
##
## 职责：持有"运行期可变状态"（主角、年/月/日、体力、技能/五维、金钱、功勲、城资源覆盖层），
## 数据只读委托 GameData 单例；不引用任何 UI，逻辑可无头跑（tools/_test_m3.gd / _test_m4.gd）。
##
## ⚠️ 不要声明 `class_name GameState`（与 autoload 名冲突）。
##
## 覆盖层设计：officers.json / castles.json 是只读导出产物，运行期改动存本单例的 override 字典，
## 不回写原表 —— 保证重开局即干净复现初始值。改 GameData 缓存取出的 Dict 必须先 .duplicate()。

const ConstsRef = preload("res://src/core/Consts.gd")
const EventFlagsRef = preload("res://src/core/event_flags.gd")
const DuelRef = preload("res://src/core/duel.gd")
const EventTextRef = preload("res://src/core/event_text.gd")
const ShopRef = preload("res://src/core/shop.gd")
const DiplomacyRef = preload("res://src/core/diplomacy.gd")
const WeatherRef = preload("res://src/core/weather.gd")
const CalendarRef = preload("res://src/core/calendar.gd")
const WorldMapRef = preload("res://src/core/world_map.gd")
const EconomyRef = preload("res://src/core/economy.gd")
const EventEffectsRef = preload("res://src/core/event_effects.gd")
const EventSysRef = preload("res://src/core/event_sys.gd")

# 游戏起始年（太阁立志传2 经典开局）
const START_YEAR : int = 1560

# —— 主命/修行 消耗与回复参数 ——
const TRAIN_STAMINA_COST  : int = 20   # M3 train_skill 一次性耗体力
const MONTH_RECOVER        : int = 15   # 每月自然回体力
const TRAIN_COST_PER_DAY   : int = 2    # 修行 金/日（§5.4）
const TRAIN_STAMINA_PER_DAY: int = 5    # 修行 体力/日（文档未逆，取保守值）
const MONTH_DAYS           : int = 30   # 每月天数（原版全月 30 天，time_rollover_ref 实证；§5.4 上限 min(30-日, 金/2)）
const START_MONEY          : int = 1000 # 主角私金起始（officers.json 无此字段，M4 占位常量，待补逆）
const WEATHER_TICKS_PER_MONTH : int = 7 # 每月天气 tick 数（≈31 日中 counter%4==0 的次数）

# —— 12 主命名称（§5.2 A，名表 0x504b28）——
const COMMAND_NAMES : Array[String] = [
	"贩卖军粮", "购买军粮", "购买军马", "购买洋枪", "开垦农田", "改建",
	"筑城", "进贡", "威吓", "朝廷工作", "收集情报", "谋略"
]

# 主命 id(0..11) → diplomacy.gd 工作指令码（0x4c5699 写 ent+0x16 bit0-5；diplomacy2_ref §4）
#   7进贡→9友好 / 8威吓→10高压 / 9朝廷工作→11 / 10收集情报→12 / 11谋略→13（offset +2）
const CMD_TO_WORK := {7: 9, 8: 10, 9: 11, 10: 12, 11: 13}

# —— 城种派生上限（§3.21.5，二进制跳表 0x49f9xx 已破，naisei_ref 66/66 自校验）——
#   城種 = int(castle["castle_type"]) & 7（castle_type 为 word@+0x1b，低字节=城種）
const CASTLE_TYPE_BASE : Dictionary = {0:0, 1:1, 2:2, 3:2, 4:2, 5:3, 6:3, 7:3}  # 農商基档
const CASTLE_TYPE_CAP  : Dictionary = {0:0, 1:80, 2:150, 3:150, 4:200, 5:250, 6:250, 7:250}  # 改修(守城度)上限
const NOUSANG_CAP : int = 100   # 农商 字段硬上限（sat_add 包装器 0x4A32A0）
const F0D_CAP     : int = 250   # 守城度 字段硬上限（0x4A32C0）

# —— 运行期状态 ——
var pid     : int = -1                # 当前主角武将 id（-1 = 未开局）
var year    : int = START_YEAR
var month   : int = 1                 # 1..12
var day     : int = 1                 # 1..MONTH_DAYS
var started : bool = false

# —— 大地图（方案 B 最小可玩空壳）——
var player_map_pos: Vector2 = Vector2.ZERO   # 主角大地图逻辑坐标
var current_castle: int = -1                  # 当前所在城 id（-1=野外）

# —— 评定対象名解析器（注入 council.gd.target_name）——
#   id<1000 → 武将名(surname+given)；1000..1999 → special NPC 名；2000..2999 → ""(运行时指针,无静态名)；
#   3000+ → generic NPC 名。council.gd 对 NPC 段 resolver 返回 "" 时回退 "NPC{id}"。
var council_name_resolver: Callable = Callable()

# —— 运行期覆盖层（pid -> 值；不回写 officers.json / castles.json）——
var _stamina_override : Dictionary = {}   # pid -> int
var _skill_override   : Dictionary = {}   # pid -> Array[int](10)
var _force_override   : Dictionary = {}   # pid -> {lead,martial,domestic,diplomacy,charm}
var _loyalty_override : Dictionary = {}   # pid -> int
var _merit_override   : Dictionary = {}   # pid -> int
var _money_override   : Dictionary = {}   # pid -> int（主角私金）
var _inventory        : Dictionary = {}   # item_id -> qty（城下町购买，运行期覆盖层；不回写 items.json）
var _medicines        : int = 0           # 薬 持有数
var _castle_override  : Dictionary = {}   # castle_id -> {field: value}（12 主命资源变更）
var _rank_override    : Dictionary = {}   # pid -> int（職位 0..7）
var _salary_override  : Dictionary = {}   # pid -> int（俸禄）
var _city_override    : Dictionary = {}   # pid -> int（居城，用于城主派生态）
var _castle_lord_override : Dictionary = {}   # castle_id -> int（城主武将编号，派生状态，覆盖 castles.json 的 f0a）

# —— S15 劇本/築城イベント旗幟塊（原版 0x5203c0，25B；M7 事件链）——
var event_flags : RefCounted = EventFlagsRef.new()

# —— M7 事件文本渲染（S15 结构层承接；MSGX %s 模板填充主角名）——
var event_text : RefCounted = EventTextRef.new()

# —— M7 店铺/商业核心（记录模型 + 入店分发 + favor 饱和 + 买药÷50）——
var shop : RefCounted = ShopRef.new()

# —— M7 外交（国関係マトリクス 1176B + 外交/主从位域 + 使者功勋结算）——
var diplomacy : RefCounted = DiplomacyRef.new()

# —— HD-3 天气（0x43cfc0 简版逐月推进；0=晴 1=曇 2=雨 3=雪 + 湿润旗 wet）——
# 复刻 word[0x513530] / dword[0x51352c]。雪国地域气候（tick_region）待国表气候字节导出后接线。
var weather = WeatherRef.new()
var _weather_tick_counter := 0      # 原版全局时钟 counter（每 4 点 tick 一次天气）

# —— M7 事件解释器「效果执行层」（7 真实事件 id 的 MSGX 叙事发射 + outcome 记录）——
var event_effects : RefCounted = EventEffectsRef.new()

# —— 事件解释器运行期条件注入（复刻 [ctx+8]/province/climate/assoc 全局：原版读 0x519548/0x5179b8/0x516638）——
#   -1 表示「未定位/未注入」，条件门控事件默认不触发。进入城/国时由 set_event_location 更新。
var evt_province : int = -1   # 玩家当前所在国 idx（id13 条件 opcode 13）
var evt_climate  : int = -1   # 当前气候组（id14 条件 opcode 14）
var evt_assoc    : int = -1   # 事件关联国 idx（id10 条件 opcode 10）

# —— 本局事件叙事流（UI 渲染源；advance_month 驱动 poll_events 追加）——
var event_log : Array = []


func _ready() -> void:
	# event_text 非 autoload，编译期无法解析 GameData 全局名；本构建 Engine.get_singleton 也取不到，
	# 故在此（GameState autoload，GameData 已先注册）注入 GameData 实例供其取 MSGX 文本。
	event_text._data = GameData
	event_effects.data = GameData
	# council.gd 非 autoload，无法解析 GameData 全局名；注入评定対象名解析器
	council_name_resolver = Callable(self, "_council_resolve")

## 评定対象名解析（供 council.gd.target_name 经 council_name_resolver 调用）
func _council_resolve(target_id: int) -> String:
	var i: int = int(target_id) & 0xFFFF
	if i < 1000:
		var o: Dictionary = GameData.get_officer(i)
		if not o.is_empty():
			return str(o.get("surname", "")) + str(o.get("given", ""))
		return ""
	if i < 2000:
		return GameData.get_npc_name(i)        # special NPC（1000..1999）
	if i < 3000:
		return ""                               # 运行时指针（dword[0x506c54]），无静态名
	return GameData.get_npc_name(i)             # generic NPC（3000+）


func start_new_game(protagonist_id: int) -> bool:
	var o := GameData.get_officer(protagonist_id)
	if o.is_empty():
		push_error("[GameState] 武将 %d 不存在" % protagonist_id)
		return false
	if not bool(o.get("is_selectable", false)):
		push_error("[GameState] 武将 %d 不可选为主角" % protagonist_id)
		return false
	pid = protagonist_id
	year = START_YEAR
	month = 1
	day = 1
	started = true
	_stamina_override.clear()
	_skill_override.clear()
	_force_override.clear()
	_loyalty_override.clear()
	_merit_override.clear()
	_money_override.clear()
	_inventory.clear()
	_medicines = 0
	_castle_override.clear()
	_rank_override.clear()
	_salary_override.clear()
	_city_override.clear()
	_castle_lord_override.clear()
	# 事件解释器运行期状态重置
	evt_province = -1
	evt_climate = -1
	evt_assoc = -1
	event_log.clear()
	# S15 事件旗幟塊：复刻原版 0x488030（0x487f9a 开局一次调用）
	event_flags.reset()
	event_flags.init_for_protagonist(pid)
	# 天气重置（原版 word[0x513530] 开局为晴）
	weather = WeatherRef.new()
	_weather_tick_counter = 0
	return true


func is_started() -> bool:
	return started and pid >= 0


func get_protagonist() -> Dictionary:
	if not is_started():
		return {}
	return GameData.get_officer(pid)


## M7 单挑：用两名武将（id）驱动一场单挑，返回 DuelSim.auto_battle 结果。
## rng=null 时用确定性 LCG（需复现可传 DuelRef.new_rng() 并 seed）。
## char 字典由 DuelSim.build_char_from_officer 从 GameData 武将派生（映射近似，公式精确）。
func run_duel(a_id: int, b_id: int, rng = null) -> Dictionary:
	var sim : RefCounted = DuelRef.new()
	var ra : RefCounted = rng if rng != null else DuelRef.new_rng()
	var ca : Dictionary = DuelRef.build_char_from_officer(GameData.get_officer(a_id))
	var cb : Dictionary = DuelRef.build_char_from_officer(GameData.get_officer(b_id))
	return sim.auto_battle(ca, cb, ra)


## M7 事件文本渲染：返回某历史事件 bit 的 MSGX 叙事文本（%s 填当前主角名）。
## 无 MSGX 锚点的 bit（1/3/4/38）返回空数组。
func render_event_text(bit: int) -> Array[String]:
	var o : Dictionary = get_protagonist()
	if o.is_empty():
		return []
	var name : String = str(o.get("surname", "")) + str(o.get("given", ""))
	return event_text.render_event(bit, name)


## 返回本局「已解决」命名历史事件的全部渲染文本（事件回顾面板用）。
func render_resolved_events() -> Array[String]:
	var o : Dictionary = get_protagonist()
	if o.is_empty():
		return []
	var name : String = str(o.get("surname", "")) + str(o.get("given", ""))
	return event_text.render_resolved(event_flags, name)


## M7 店铺/商业：入店分发器转发（shop_id ∈ [0,30) → 记录，否则空；几何同 0x44e710/0x44e7d4）
func enter_shop(shop_id: int) -> Dictionary:
	return shop.enter_shop(shop_id)


## 主角当前完整状态（合并运行期覆盖层），供 UI/测试消费
func get_status() -> Dictionary:
	if not is_started():
		return {}
	var o := GameData.get_officer(pid)
	var rank: int = _ov_rank(pid)
	var rank_name: String = rank_ladder_name_of(rank)
	if is_castle_lord(pid) and rank >= ConstsRef.CASTLE_LORD_MIN_RANK:
		rank_name = "城主"
	var forces: Dictionary = _effective_forces()
	return {
		"id": pid,
		"name": str(o.get("surname", "")) + str(o.get("given", "")),
		"year": year,
		"month": month,
		"day": day,
		"forces": forces,
		"force_names": ConstsRef.FORCE_CN,
		"skill_names": ConstsRef.SKILL_NAMES,
		"skill_levels": _effective_skills(),   # 10-int 数组（含修行覆盖）
		"rank": rank,
		"rank_name": rank_name,
		"loyalty": _effective_loyalty(),
		"stamina": _effective_stamina(),
		"stamina_max": _stamina_max(),
		"merit": _effective_merit(),
		"money": _effective_money(),
		"salary": _ov_salary(pid),
		"city": _ov_city(pid),
		"is_castle_lord": is_castle_lord(pid),
		"province": int(o.get("province", ConstsRef.NONE_PROVINCE)),
	}


# =====================================================================
# 大地图（复刻原版：逐格移动 / 点击自动移动 / 坐船跨海 / 移动推进时间）
# =====================================================================
#
# 坐标源：data/castle_map.json（200 城史实经纬度投影，见 gen_castle_map.py）。
# 移动机制（原版，见 docs/replication/worldmap_notes.md）：
#   · 移动方式：点击地图位置 / 指定城町自动移动 / 方向键逐格
#   · 野外移动推进时间：每格 1 天（原版「移動だけでも時間が進む」）
#   · 四国・九州须经港町坐船；坐船消耗航路天数 + 体力压至 20（原版手册）
# 纯逻辑（投影 / 最近城 / 寻路）在 src/core/world_map.gd。

const MOVE_DAYS_PER_CELL := 1.0    # 每格移动天数（复刻原版）
const SEA_STAMINA_FLOOR := 20      # 坐船体力下限（原版手册：降至 20 不再降）
const PORT_DIST := 1.5             # 判定"在港町"的距离阈值（京畿城密，按距离找港而非最近城）
const WEATHER_TICK_EVERY := 4      # 原版 counter%4==0 时天气 tick 一次（每月约 7 次）
const MOVE_DAYS_BAD_WEATHER := 2   # 雨/雪天每格移动天数（原版「豪雨時機動力が鈍る」）

## 进入大地图（离开城到野外）
func enter_world() -> void:
	current_castle = -1

## 进入指定城（更新所在城 + 移动到该城坐标）
func enter_castle(cid: int) -> void:
	current_castle = cid
	var p := GameData.get_castle_pos(cid)
	if p != Vector2.ZERO:
		player_map_pos = p

## 从城下町返回野外（保留坐标，便于再次进城）
func leave_to_world() -> void:
	current_castle = -1

## 当前天气下的每格移动天数：晴/阴 1 天；雨/雪 2 天（复刻「豪雨時機動力が鈍る」）
func move_days_per_cell() -> int:
	var w: int = weather.get_weather()
	if w == WeatherRef.RAIN or w == WeatherRef.SNOW:
		return MOVE_DAYS_BAD_WEATHER
	return 1

## 逐格移动主角（dx,dy ∈ {-1,0,1}），每格推进 move_days_per_cell() 天；返回新坐标
func move_player(dx: int, dy: int) -> Vector2:
	var ms := GameData.get_map_size()
	var before := player_map_pos
	player_map_pos = WorldMapRef.step(player_map_pos, float(dx), float(dy), ms.x, ms.y)
	if player_map_pos != before:
		advance_days(move_days_per_cell())
	return player_map_pos

## 朝目标位置走一步（点击自动移动，每步 1 格），推进 move_days_per_cell() 天；
## 返回 true 表示已到达目标
func move_player_towards(target: Vector2) -> bool:
	var ms := GameData.get_map_size()
	var before := player_map_pos
	player_map_pos = WorldMapRef.move_towards(player_map_pos, target, ms.x, ms.y)
	if player_map_pos != before:
		advance_days(move_days_per_cell())
	return player_map_pos.distance_to(target) <= 0.01

## 坐船：从当前最近港町前往 to_id 港町。
## 复刻原版：消耗航路天数；连续坐船体力压至 20（不再降）。
## 返回 {ok, reason?, days?, to?}
func travel_by_sea(to_id: int) -> Dictionary:
	var from_id := nearest_port()
	if from_id < 0:
		return {"ok": false, "reason": "not_near_port"}
	var route := GameData.get_sea_route(from_id, to_id)
	if route.is_empty():
		return {"ok": false, "reason": "no_route"}
	var days := int(route["days"])
	advance_days(days)
	if _effective_stamina() > SEA_STAMINA_FLOOR:
		_stamina_override[pid] = SEA_STAMINA_FLOOR
	var p := GameData.get_castle_pos(to_id)
	if p != Vector2.ZERO:
		player_map_pos = p
	current_castle = -1
	return {"ok": true, "days": days, "to": to_id}

## 当前坐标最近的城 id（-1 = 无地图）
func nearest_castle() -> int:
	if not GameData.has_castle_map():
		return -1
	return WorldMapRef.nearest(player_map_pos, GameData.get_castle_positions())

## 距离 ≤ PORT_DIST 的最近港町 id（-1 = 不在港町）。
## 复刻原版：港町是大地图独立点，走到港町（或城下）附近即可搭船；
## 用距离判定避免京畿密城区 nearest_castle 误判。
func nearest_port() -> int:
	if not GameData.has_castle_map():
		return -1
	var best := -1
	var best_d := PORT_DIST
	for pid in GameData.get_port_ids():
		var d: float = player_map_pos.distance_to(GameData.get_castle_pos(int(pid)))
		if d <= best_d:
			best_d = d
			best = int(pid)
	return best

# =====================================================================
# 修行（§5.4）—— 8 动作 + 功勲 += (旧级+1)×500 封顶 60000
# =====================================================================
#
# 动作表（mode → 效果）：
#   0 学习内政  → 口才(0)  +1（概率 rand%(16-sub)==0，sub=当前口才级）
#   1 学习外交  → 筑城(7)  +1（概率与属性和相关；以 mode-0 门为近似，待 0x45f710 精逆）
#   2 学习魅力  → 兵法(5)  +1（确定）
#   3 学习剑术  → 武力      +1（确定，五维封顶 100）
#   4 读书      → 50% 内政(domestic) +1，否则 统御(lead) +1（确定 50/50）
#   5 艺术鉴赏  → 魅力      +1（确定）
#   6 宝物鉴赏  → 外交      +1（确定）
#   7 什么也不做 → 早退（仅推进时间，不计费/不增益/不功勲）
#
# 功勲：仅"技能等级提升"（mode 0/1/2 提升口才/筑城/兵法）时按 (旧级+1)×500 累加，
#       饱和封顶 MERIT_CAP(60000)。五维提升（mode 3-6）走独立路径 0x45feb0，
#       续240 所逆写器族专指 cap-3 技能，故五维提升不在此处计功勲（文档已留档）。
#
# 资格（§5.4 资格判定 0x4b5620）：学习者与师父的 技能等级和≥6 / 外交和≥100 /
#       魅力和≥100，任一达标则不可执行（仅当提供师父时生效，无师不阻断）。

## 报名前资格判定；teacher_id<0 视为无师（恒可修行）
func can_train(mode: int, teacher_id: int = -1) -> bool:
	if mode < 0 or mode > 7:
		return false
	if teacher_id < 0:
		return true
	var t := GameData.get_officer(teacher_id)
	if t.is_empty():
		return true
	var sk := _effective_skills()
	var tsk: Array = t.get("skill_levels", [])
	var sum_skill := 0
	for i in range(mini(sk.size(), tsk.size())):
		sum_skill += int(sk[i]) + int(tsk[i])
	var dip := int(_effective_forces().get("diplomacy", 0)) + int(t.get("forces", {}).get("diplomacy", 0))
	var cha := int(_effective_forces().get("charm", 0)) + int(t.get("forces", {}).get("charm", 0))
	if sum_skill >= 6 or dip >= 100 or cha >= 100:
		return false
	return true


## 执行修行：mode(0..7) + 天数 days + 每日随机整数序列 rand_vals（不传则运行时取随机）
## 返回 {ok, reason, mode, days, cost, gains[], merit_gain}
func train_mode(mode: int, days: int, rand_vals: Array = []) -> Dictionary:
	var res := {"ok": false, "reason": "", "mode": mode, "days": 0, "cost": 0, "gains": [], "merit_gain": 0}
	if not is_started():
		res["reason"] = "not_started"; return res
	if mode < 0 or mode > 7:
		res["reason"] = "bad_mode"; return res
	if not can_train(mode):
		res["reason"] = "ineligible"; return res

	# mode 7 早退：仅推进时间，不计费/不增益
	if mode == 7:
		res["ok"] = true
		res["reason"] = "early_exit"
		advance_days(maxi(1, days))
		return res

	var money := _effective_money()
	var day_cap := mini(MONTH_DAYS - day, money / TRAIN_COST_PER_DAY)
	if days < 1:
		res["reason"] = "bad_days"; return res
	if days > day_cap:
		res["reason"] = "exceeds_cap"; return res

	var cost := days * TRAIN_COST_PER_DAY
	var stamina_cost := days * TRAIN_STAMINA_PER_DAY
	if _effective_stamina() < stamina_cost:
		res["reason"] = "low_stamina"; return res

	var gains := []
	var merit_gain := 0
	for d in range(days):
		var rv: int = (rand_vals[d] if d < rand_vals.size() else randi()) as int
		var g: Variant = _train_day(mode, rv)
		if g != null:
			gains.append(g)
			merit_gain += int(g.get("merit", 0))

	# 落实花费与时间推进
	_money_override[pid] = money - cost
	_consume_stamina(stamina_cost)
	advance_days(days)

	res["ok"] = true
	res["days"] = days
	res["cost"] = cost
	res["gains"] = gains
	res["merit_gain"] = merit_gain
	return res


## 单日修行尝试；返回增益描述 Dict 或 null（无增益）
func _train_day(mode: int, rv: int) -> Variant:
	match mode:
		0:  # 学习内政 → 口才(0)，概率 rand%(16-sub)==0
			var sub := int(_effective_skills()[0])
			if rv % (16 - sub) != 0:
				return null
			return _skill_up(0)
		1:  # 学习外交 → 筑城(7)，概率与属性和相关（以 mode-0 门近似）
			var sub := int(_effective_skills()[7])
			if rv % (16 - sub) != 0:
				return null
			return _skill_up(7)
		2:  # 学习魅力 → 兵法(5)，确定
			return _skill_up(5)
		3:  # 学习剑术 → 武力，确定
			return _force_up("martial")
		4:  # 读书 → 50% 内政(domestic) 否 统御(lead)
			if rv % 2 == 0:
				return _force_up("domestic")
			return _force_up("lead")
		5:  # 艺术鉴赏 → 魅力，确定
			return _force_up("charm")
		6:  # 宝物鉴赏 → 外交，确定
			return _force_up("diplomacy")
		_:
			return null


## 技能 +1（封顶 3）+ 功勲 += (旧级+1)×500 封顶 60000
func _skill_up(k: int) -> Variant:
	var skills: Array = _effective_skills()
	var old: int = int(skills[k])
	if old >= ConstsRef.SKILL_CAP:
		return null
	skills[k] = old + 1
	_skill_override[pid] = skills
	var prev_merit: int = _effective_merit()
	var new_merit: int = mini(prev_merit + (old + 1) * 500, ConstsRef.MERIT_CAP)
	_merit_override[pid] = new_merit
	return {"kind": "skill", "index": k, "name": ConstsRef.SKILL_NAMES[k], "old": old, "new": old + 1, "merit": new_merit - prev_merit}


## 五维 +1（封顶 100）；不计功勲（见文件头说明）（封顶时返回 null）
func _force_up(key: String) -> Variant:
	var f: Dictionary = _effective_forces()
	var old: int = int(f.get(key, 0))
	if old >= ConstsRef.FORCE_CAP:
		return null
	f[key] = old + 1
	_force_override[pid] = f
	return {"kind": "force", "key": key, "old": old, "new": old + 1, "merit": 0}


# =====================================================================
# 12 主命（§5.2 A）—— 派发到城资源覆盖层
# =====================================================================
#
# 精确 delta 状态（handler 级逆向 续153 / naisei_ref.py 66/66）：
#   · 开垦农田/改建/筑城（主命 4/5/6）已逐 handler 逆向，delta 由"実行者内政力(naisei=
#     forces.domestic)"与"城規模(f09)/城種(castle_type&7)"精确推导，并经字段硬上限钳制。
#   · 贩卖/购买军粮（0/1）handler 只算"仕事成果値"(byte[ent+0x17])，真实 軍糧↔資金 转移走
#     纳结算路径（§3.21.9 / naisei_resource_ref.py，已破但不在主命层）；军马/洋枪(2/3) 的
#     物品池是全局表(0x51e1f6)非城字段；进贡/威吓/朝廷/收集情报/谋略(7-11) 已接线真实
#     diplomacy.gd（关系写入 + can_dispatch 筛选 + 0x4b9250 功勋），资金 delta 仍为占位。
#   主命统一耗时 1 月（M3 约定：执行 1 条主命 → 推进 1 月）。

## 返回 {ok, reason, cmd, name, deltas, month_advanced}
func issue_command(cmd_id: int, _opts: Dictionary = {}) -> Dictionary:
	var res := {"ok": false, "reason": "", "cmd": cmd_id, "name": "", "deltas": {}, "month_advanced": false}
	if not is_started():
		res["reason"] = "not_started"; return res
	if cmd_id < 0 or cmd_id >= COMMAND_NAMES.size():
		res["reason"] = "bad_cmd"; return res
	var castle_id: int = int(get_protagonist().get("city", ConstsRef.NONE_CITY))
	if castle_id == ConstsRef.NONE_CITY:
		res["reason"] = "no_castle"; return res

	res["name"] = COMMAND_NAMES[cmd_id]
	# 外交类主命（7..11）先过 can_dispatch 目标国筛选（0x4c4270，按主从関係）；
	# 被拒不耗时（不推进月份、不扣钱）
	var dip := {}
	if CMD_TO_WORK.has(cmd_id):
		dip = _apply_diplomacy_command(cmd_id, _opts)
		res["diplomacy"] = dip
		if not bool(dip.get("ok", false)):
			res["reason"] = str(dip.get("reason", ""))
			return res
	# 精确 delta 需要：当前有效城状态 + 実行者内政力(naisei) + 改建 tier2（ent+0x10>>6，缺省 0）
	var eff_castle: Dictionary = _effective_castle(castle_id)
	var naisei: int = int(_effective_forces().get("domestic", 0))
	var tier2: int = int(_opts.get("tier2", 0))
	var deltas: Dictionary = _command_deltas(cmd_id, eff_castle, naisei, tier2)
	for field in deltas.keys():
		_mutate_castle(castle_id, field, int(deltas[field]))
	res["deltas"] = deltas
	# 外交功勋（使者归还结算 0x4b9250 → 0x4b9890 功勋加算）
	var m := int(dip.get("merit", 0))
	if m > 0:
		_add_merit(m)
		res["merit_gain"] = m
	advance_month()   # 主命耗时 1 月
	res["month_advanced"] = true
	res["ok"] = true
	return res


## 主角所在省（自国省 id；无城 → -1）
func protagonist_province() -> int:
	var cid := int(get_protagonist().get("city", ConstsRef.NONE_CITY))
	if cid == ConstsRef.NONE_CITY:
		return -1
	return int(GameData.get_castle(cid).get("province", -1))


## 目标省城数（0x4d9e50 prov 链表计数；复刻层按连续 id 扫 castles.json 等价实现）
func province_city_count(prov: int) -> int:
	var n := 0
	var id := 0
	while true:
		var c: Dictionary = GameData.get_castle(id)
		if c.is_empty():
			break
		if int(c.get("province", -1)) == prov:
			n += 1
		id += 1
	return n


## 功勋加算（0x4b9890；封顶 MERIT_CAP 60000，沿用 _effective_merit 哨兵约定）
func _add_merit(n: int) -> void:
	if n <= 0:
		return
	_merit_override[pid] = mini(_effective_merit() + n, ConstsRef.MERIT_CAP)


## 外交类主命真实接线 diplomacy.gd。
##   cmd_id 7进贡/8威吓/9朝廷工作/10收集情报/11谋略
##   opts: target_province 必填（目标国）；work_type / got_rank / g10 / g0d 可选覆写
## RE 依据：diplomacy2_ref §2/§4 ——
##   · can_dispatch(0x4c4270)：目标国筛选按【主从関係】（高压拒{2,3} / 友好仅空白 / 情报无条件）
##   · friendly_success(0x4b5bcb) / pressure_success(0x4b6095)：关系写入（外交 bit0-2 + 主从 bit3-4）
##   · 使者归还结算 0x4b9250 功勋：友好 600 / 高压 1000 / 朝廷 800·1000(得官位) /
##     情报 = 城数*(mission_level+5)+100
## ⚠️ 诚实建模边界（不发明 RE 之外的东西）：
##   · 成败：结算层无随机失败分支（0x47b5f0 高压恒成；0x4b94ac/0x4b94f4 直接出
##     「进贡使者完成 / 使屈服成功」消息）→ 进贡/威吓按必定完成建模
##   · work_type 语义未逆 → 默认 0（friendly: lv=diff(1,0)=1 亲密；pressure 同），opts 覆写
##   · g[0x10]/g[0x0d] 字段语义未逆（BREAKTHROUGHS 续1105/1235 挂账）→ 情报功勋默认 0/0
##     （lv=1 → merit=城数*6+100），opts["g10"]/["g0d"] 覆写
##   · 朝廷工作不改关系矩阵（RE 无关系写入点）；谋略（拉拢武将）无关系/功勋模型 → 仅占位
func _apply_diplomacy_command(cmd_id: int, opts: Dictionary) -> Dictionary:
	var res := {"ok": false, "reason": "", "work": int(CMD_TO_WORK.get(cmd_id, 0)),
		"target": -1, "lv": -1, "dipl_before": -1, "dipl_after": -1,
		"mv_before": -1, "mv_after": -1, "merit": 0}
	var work: int = int(CMD_TO_WORK.get(cmd_id, 0))
	# 谋略（拉拢武将 0x4b960e）：无关系/功勋静态模型 → 诚实占位（不耗时）
	if work == 13:
		res["reason"] = "work_not_modeled"; return res
	var my := protagonist_province()
	if my < 0:
		res["reason"] = "no_province"; return res
	var target := int(opts.get("target_province", -1))
	res["target"] = target
	if target < 0 or target > 48 or target == my:
		res["reason"] = "bad_target"; return res
	# can_dispatch 的 mode：0=高压 1=友好 2=情报；朝廷/谋略无此筛选（-1 = 跳过）
	var mode := -1
	if work == 9:
		mode = 1
	elif work == 10:
		mode = 0
	elif work == 12:
		mode = 2
	var mv_before := int(diplomacy.get_master_vassal(my, target))
	res["mv_before"] = mv_before
	res["dipl_before"] = int(diplomacy.get_diplomacy(my, target))
	if mode >= 0 and not diplomacy.can_dispatch(mode, mv_before):
		res["reason"] = "dispatch_blocked"; return res
	var merit := 0
	var lv := -1
	match work:
		9:   # 进贡 = 友好外交（0x4b5bcb）→ 同盟 + 外交=lv
			lv = diplomacy.friendly_success(int(opts.get("work_type", 0)), target, my)
			merit = DiplomacyRef.MERIT_FRIENDLY
		10:  # 威吓 = 高压外交（0x4b6095）→ 支配 + 外交=lv（0x47b5f0 恒成）
			lv = diplomacy.pressure_success(int(opts.get("work_type", 0)), target, my)
			merit = DiplomacyRef.MERIT_PRESSURE
		11:  # 朝廷工作（0x4b953c）：无关系写入点；得官位与否由 opts 声明
			merit = DiplomacyRef.MERIT_COURT_RANK if bool(opts.get("got_rank", false)) \
				else DiplomacyRef.MERIT_COURT_NO_RANK
		12:  # 收集情报（0x4b956e）：功勋 = 城数*(lv+5)+100；关系矩阵不变
			merit = DiplomacyRef.intel_merit(int(opts.get("g10", 0)),
				int(opts.get("g0d", 0)), province_city_count(target))
	res["lv"] = lv
	res["merit"] = merit
	res["dipl_after"] = int(diplomacy.get_diplomacy(my, target))
	res["mv_after"] = int(diplomacy.get_master_vassal(my, target))
	res["ok"] = true
	return res


# —— 城种派生辅助（§3.21.5）——
func _castle_type(castle: Dictionary) -> int:
	return int(castle.get("castle_type", 0)) & 7

## 農商上限 agri_capacity（0x49f9b0）：max(1, (規模 × 城種基档 × 4) ÷ 3)
func _agri_capacity(castle: Dictionary) -> int:
	var base: int = int(CASTLE_TYPE_BASE.get(_castle_type(castle), 0))
	var scale: int = int(castle.get("f09", 0))
	var v: int = (scale * base * 4) / 3
	return maxi(1, v)

## 改修(守城度)上限 castle_type_cap（0x49f9f0）
func _castle_type_cap_of(castle: Dictionary) -> int:
	return int(CASTLE_TYPE_CAP.get(_castle_type(castle), 0))


## 各主命对城资源的精确/占位 delta（字段名见 castles.json）。
## 返回 {field: 实际生效增量}（已按当前城状态 + 字段硬上限钳制，可直接累加）。
##   castle = 当前有效城状态；naisei = 実行者内政力；tier2 = 改建用 ent+0x10>>6（缺省 0）。
func _command_deltas(cmd_id: int, castle: Dictionary, naisei: int, tier2: int = 0) -> Dictionary:
	match cmd_id:
		# —— 以下三项为二进制精确（naisei_ref.work_kaiten/kaizen/chikujo 逐字节对齐）——
		4:  # 开垦农田（code6, 0x4aa290）→ 农商(+0x0c)
			var cur: int = int(castle.get("nousang", 0))
			var cap: int = _agri_capacity(castle)
			var delta: int = 1
			if naisei > 30:
				delta = int((naisei - 30) / 10.0) + 1   # div10(sat_sub(naisei,30)) + 1
			var add: int = delta
			if cap >= cur:
				add = mini(cap - cur, delta)
			var newv: int = mini(cur + add, NOUSANG_CAP)
			return {"nousang": newv - cur}
		5:  # 改建（code7, 0x4aa370）→ 守城度(+0x0d)
			var cur2: int = int(castle.get("f0d", 0))
			var cap2: int = _castle_type_cap_of(castle)
			var delta2: int = int(naisei / 10.0) + 5 * (tier2 + 1)   # div10(naisei) + 5*(tier2+1)
			var add2: int = delta2
			if cap2 >= cur2:
				add2 = mini(cap2 - cur2, delta2)
			var newv2: int = mini(cur2 + add2, F0D_CAP)
			return {"f0d": newv2 - cur2}
		6:  # 筑城（code8, 0x4ab530）→ 守城度(+0x0d) += 10（另置 築城済 flag 0x1c|=0x20，非资源字段）
			var cur3: int = int(castle.get("f0d", 0))
			var newv3: int = mini(cur3 + 10, F0D_CAP)
			return {"f0d": newv3 - cur3}
		# —— 以下为经济模拟占位（非 handler 级精确；详见本段顶部注释 + §3.21.4）——
		0:  return {"gunryo": -300, "shikin": 300}   # 贩卖军粮（真实转移走纳结算）
		1:  return {"gunryo": 300, "shikin": -300}   # 购买军粮
		2:  return {"shikin": -300, "f1a": 1}        # 购买军马（f1a=军马，全局物品池模拟）
		3:  return {"shikin": -400, "f18": 1}        # 购买洋枪（f18=铁炮）
		7:  return {"shikin": -200}                   # 进贡（关系变动，非城资源）
		8:  return {"shikin": -100}                   # 威吓
		9:  return {"shikin": -150}                   # 朝廷工作
		10: return {"shikin": -50}                    # 收集情报
		11: return {"shikin": -100}                   # 谋略（寝返り，忠诚变动）
		_:  return {}


# =====================================================================
# M3 兼容接口（简化：1 技能 +1 / 耗 20 体力 / 推 1 月；不计功勲，留作回归）
# =====================================================================
func train_skill(idx: int) -> Dictionary:
	var res := {"ok": false, "reason": ""}
	if not is_started():
		res["reason"] = "not_started"; return res
	if idx < 0 or idx >= ConstsRef.SKILL_NAMES.size():
		res["reason"] = "bad_idx"; return res
	var skills: Array = _effective_skills()
	if int(skills[idx]) >= ConstsRef.SKILL_CAP:
		res["reason"] = "capped"; return res
	if _effective_stamina() < TRAIN_STAMINA_COST:
		res["reason"] = "low_stamina"; return res
	skills[idx] = int(skills[idx]) + 1
	_skill_override[pid] = skills
	_consume_stamina(TRAIN_STAMINA_COST)
	advance_month()
	res["ok"] = true
	return res


## 休养：体力回满（到个人 stamina_max），推进 1 月
func rest() -> Dictionary:
	var res := {"ok": false, "reason": ""}
	if not is_started():
		res["reason"] = "not_started"; return res
	_stamina_override[pid] = _stamina_max()
	advance_month()
	res["ok"] = true
	return res


# =====================================================================
# 经济 / 背包（城下町设施交互，接 economy.gd / shop.gd）
# =====================================================================
func get_inventory() -> Dictionary:
	var out := {}
	for k in _inventory.keys():
		var q := int(_inventory[k])
		if q > 0:
			out[int(k)] = q
	return out


func count_item(id: int) -> int:
	return int(_inventory.get(id, 0))


func add_item(id: int, qty: int = 1) -> void:
	if qty <= 0:
		return
	_inventory[id] = int(_inventory.get(id, 0)) + qty


func spend_item(id: int, qty: int = 1) -> bool:
	if count_item(id) < qty:
		return false
	_inventory[id] = int(_inventory[id]) - qty
	return true


func get_medicines() -> int:
	return _medicines


## 扣钱（成功 true）。负/零成本直接成功；余额不足失败。
func spend_money(cost: int) -> bool:
	if cost <= 0:
		return true
	if _effective_money() < cost:
		return false
	_money_override[pid] = _effective_money() - cost
	return true


## 加钱（钳制 ≥0）
func gain_money(n: int) -> void:
	_money_override[pid] = maxi(0, _effective_money() + n)


## 商店买物品：价格 = economy.item_buy_price（真实价值 ×1.5）。成功入库 + 扣钱。
func shop_buy(item_id: int) -> Dictionary:
	var res := {"ok": false, "reason": "", "cost": 0, "name": ""}
	if not is_started():
		res["reason"] = "not_started"; return res
	var item: Dictionary = GameData.get_item(item_id)
	if item.is_empty():
		res["reason"] = "no_item"; return res
	var price: int = EconomyRef.item_buy_price(item)
	if _effective_money() < price:
		res["reason"] = "no_money"; return res
	spend_money(price)
	add_item(item_id, 1)
	res["ok"] = true
	res["cost"] = price
	res["name"] = str(item.get("name", ""))
	return res


## 商店卖物品：价格 = economy.item_sell_value（真实价值 /2）。成功出库 + 加钱。
func shop_sell(item_id: int, qty: int = 1) -> Dictionary:
	var res := {"ok": false, "reason": "", "gain": 0, "name": ""}
	if not is_started():
		res["reason"] = "not_started"; return res
	if qty <= 0:
		res["reason"] = "bad_qty"; return res
	if count_item(item_id) < qty:
		res["reason"] = "no_item"; return res
	var item: Dictionary = GameData.get_item(item_id)
	if item.is_empty():
		res["reason"] = "no_item"; return res
	var unit: int = EconomyRef.item_sell_value(item)
	var gain: int = unit * qty
	spend_item(item_id, qty)
	gain_money(gain)
	res["ok"] = true
	res["gain"] = gain
	res["name"] = str(item.get("name", ""))
	return res


## 医館买薬：服数 = shop.medicine_doses(money)，金额 = medicine_cost。成功入库 + 扣钱。
func buy_medicine(doses: int) -> Dictionary:
	var res := {"ok": false, "reason": "", "cost": 0, "doses": 0}
	if not is_started():
		res["reason"] = "not_started"; return res
	if doses <= 0:
		res["reason"] = "bad_doses"; return res
	var cost: int = ShopRef.medicine_cost(doses)
	if _effective_money() < cost:
		res["reason"] = "no_money"; return res
	spend_money(cost)
	_medicines += doses
	res["ok"] = true
	res["cost"] = cost
	res["doses"] = doses
	return res


## 用薬：恢复体力（满）并推进 1 月（简化休养）。
func use_medicine() -> Dictionary:
	var res := {"ok": false, "reason": ""}
	if _medicines <= 0:
		res["reason"] = "no_medicine"; return res
	_medicines -= 1
	_stamina_override[pid] = _stamina_max()
	advance_month()
	res["ok"] = true
	return res


# =====================================================================
# M7 事件解释器（效果执行层接线）—— 7 真实事件 id：0,1,9,10,13,14,15
# =====================================================================
#
# 真实运行期 vtable（event_id_dispatch_ref）：仅这 7 个 id 自断言 [ctx+0] 且经 FIRE 派发；
# 其余 id(2/3/4/5/6/7/8/11/16/17/29) 是菜单/UI/对话 applier，永不测 [ctx+0]，非事件调度成员。
#
# 触发模型（诚实）：
#   · 条件门控事件 10/13/14：按注入的运行期状态（evt_*/assoc）用 EventSys 已解码 opcode 评估，
#     匹配即 fire（poll_events 自动跑，由 advance_month 每月驱动）。
#   · effect 驱动事件 0/1/9/15：其「月度调度谓词」(0x4d0ca0 applier) 已证伪为 vtable 成员，
#     本复刻未建模其自动触发 → 仅暴露 force_event 供游戏月度调度器 / 测试显式驱动。
#   · 触发后叙事经 EventEffects.dispatch_event 发射 MSGX 文本并写入 event_log（UI 渲染源）。

## 更新玩家当前所在国 / 气候 / 事件关联国（进入城、移动大地图时调用）。
## province/climate 取国表；assoc 缺省跟随 province。
func set_event_location(province: int, climate: int, assoc: int = -1) -> void:
	evt_province = province
	evt_climate = climate
	evt_assoc = assoc if assoc >= 0 else province


## 运行期条件状态读取（供 EventSys.would_fire 注入 rt 对象）。
func current_province() -> int: return evt_province
func current_climate() -> int:  return evt_climate
func assoc_province() -> int:   return evt_assoc


## 返回本局事件叙事流（UI 事件面板）。
func get_event_log() -> Array:
	return event_log


## 收集 event_log[from_idx..] 的叙事文本行（供 UI 事件弹窗 / 回顾面板）。
## 有 MSG 的事件取其文本；narrative_pending 的事件（id13/14 等触发后叙事未逆）给诚实占位行。
func pending_event_lines(from_idx: int = 0) -> Array[String]:
	var log := get_event_log()
	var out: Array[String] = []
	for i in range(maxi(0, from_idx), log.size()):
		var e: Dictionary = log[i]
		for m in e.get("msgs", []):
			if str(m).length() > 0:
				out.append(str(m))
		if bool(e.get("narrative_pending", false)):
			out.append("[事件 %d 触发] 叙事待补（逆向缺口）" % int(e.get("id", 0)))
	return out


## 月度事件轮询：评估条件门控事件(10/13/14)并自动触发，写 event_log。
## 返回本次触发的结果数组（供 UI 即时弹窗）。
func poll_events() -> Array:
	if not is_started():
		return []
	var fired : Array = []
	for eid in [10, 13, 14]:
		var ctx : EventSysRef.EventCtx = EventSysRef.EventCtx.new()
		ctx.event_id = eid
		if _event_should_fire(eid, ctx):
			var res : Dictionary = event_effects.dispatch_event(eid, ctx, self)
			event_log.append(res)
			fired.append(res)
	return fired


## 条件门控事件的触发判定（仅覆盖已解码 opcode 10/13/14；其余返回 false）。
func _event_should_fire(eid: int, ctx: EventSysRef.EventCtx) -> bool:
	match eid:
		13:  # opcode 13：当前所在国 == arg（arg 缺省=当前国，作为 scaffold）
			return evt_province >= 0 and EventSysRef.eval_4e82c0(13, evt_province, evt_province, evt_climate)
		14:  # opcode 14：当前气候组 == arg
			return evt_climate >= 0 and EventSysRef.eval_4e82c0(14, evt_climate, evt_province, evt_climate)
		10:  # opcode 10：事件关联国 == arg（门控 [ctx+0xc]&2==0）
			return evt_assoc >= 0 and EventSysRef.eval_4e7e10(10, evt_assoc, evt_assoc, 0)
	return false


## 显式触发某事件（force 绕过条件门控）：effect 驱动事件 0/1/9/15 的月度调度入口，亦供测试。
## 返回 dispatch_event 结果并追加 event_log；未开局返回空。
func force_event(eid: int, arg: int = 0) -> Dictionary:
	if not is_started():
		return {}
	if not EventEffectsRef.REAL_EVENT_IDS.has(eid):
		return {}
	var ctx : EventSysRef.EventCtx = EventSysRef.EventCtx.new()
	ctx.event_id = eid
	ctx.arg = arg
	var res : Dictionary = event_effects.dispatch_event(eid, ctx, self)
	event_log.append(res)
	return res


# =====================================================================
# 时间推进
# =====================================================================
## 推进 n 天（自动跨月/跨年）；复刻 time_rollover 进位链（每月 30 天、12 月/年、无闰年）。
## 天气：原版全局时钟 counter 每 +4 即 tick 一次天气（简版，随当前月份季节变化）。
func advance_days(n: int) -> void:
	var yoff: int = year - START_YEAR
	var r: Array = CalendarRef.roll_days(n, day, month, yoff)
	day = int(r[0])
	month = int(r[1])
	year = START_YEAR + int(r[2])
	_weather_tick_counter += n
	var ticks: int = _weather_tick_counter / WEATHER_TICK_EVERY
	if ticks > 0:
		_weather_tick_counter %= WEATHER_TICK_EVERY
		for i in range(ticks):
			weather.tick_simple(month)


## 推进 1 月：自然回体力 + 月份滚动（12 月 → 次年 1 月）；复刻 time_rollover 进位链
func advance_month() -> void:
	_recover_stamina(MONTH_RECOVER)
	var yoff: int = year - START_YEAR
	var r: Array = CalendarRef.roll_months(1, day, month, yoff)
	day = 1                  # 主命耗时 1 月 → 日归 1
	month = int(r[1])
	year = START_YEAR + int(r[2])
	# 月度事件轮询：条件门控事件(10/13/14)按运行期状态自动触发，叙事写入 event_log
	poll_events()


# =====================================================================
# 内部：运行期覆盖访问
# =====================================================================
func _stamina_max() -> int:
	var o := GameData.get_officer(pid)
	return int(o.get("stamina_max", ConstsRef.STAMINA_CAP))


func _effective_stamina() -> int:
	if _stamina_override.has(pid):
		return int(_stamina_override[pid])
	return int(GameData.get_officer(pid).get("stamina", _stamina_max()))


func _consume_stamina(n: int) -> void:
	_stamina_override[pid] = maxi(0, _effective_stamina() - n)


func _recover_stamina(n: int) -> void:
	_stamina_override[pid] = mini(_stamina_max(), _effective_stamina() + n)


func _effective_skills() -> Array:
	if _skill_override.has(pid):
		return (_skill_override[pid] as Array).duplicate()
	var arr: Array = GameData.get_officer(pid).get("skill_levels", [])
	return arr.duplicate()


func _effective_forces() -> Dictionary:
	var base: Dictionary = GameData.get_officer(pid).get("forces", {})
	if _force_override.has(pid):
		var ov: Dictionary = _force_override[pid]
		var merged: Dictionary = base.duplicate()
		for k in ov.keys():
			merged[k] = ov[k]
		return merged
	return base.duplicate()


func _effective_loyalty() -> int:
	if _loyalty_override.has(pid):
		return int(_loyalty_override[pid])
	return int(GameData.get_officer(pid).get("loyalty", 0))


func _effective_merit() -> int:
	if _merit_override.has(pid):
		return int(_merit_override[pid])
	# 原版 0xFFFF(65535) 为"满"哨兵，有效上限为 MERIT_CAP(60000)
	return mini(int(GameData.get_officer(pid).get("merit", 0)), ConstsRef.MERIT_CAP)


func _effective_money() -> int:
	if _money_override.has(pid):
		return int(_money_override[pid])
	return START_MONEY


# —— 城资源覆盖层（12 主命）——
## 返回合并覆盖层的城状态（不污染 GameData 缓存）
func get_effective_castle(id: int) -> Dictionary:
	return _effective_castle(id)


func _effective_castle(id: int) -> Dictionary:
	var base: Dictionary = GameData.get_castle(id)
	if _castle_override.has(id):
		var ov: Dictionary = _castle_override[id]
		var merged: Dictionary = base.duplicate()
		for k in ov.keys():
			merged[k] = ov[k]
		return merged
	return base.duplicate()


func _mutate_castle(id: int, field: String, delta: int) -> void:
	var cur: int = int(_effective_castle(id).get(field, 0))
	if not _castle_override.has(id):
		_castle_override[id] = {}
	_castle_override[id][field] = cur + delta


# =====================================================================
# M5 職位晋升（§5.3 評定/晋升 + 城主任命 + 大名继承）
# =====================================================================
#
# 权威规格（二进制自校验 续63 / promo2_ref / promote3_ref）：
#  · 職位名表 0x50d850（9 项，见 ConstsRef.RANK_NAMES）
#  · 勲功阈值表 0x50bf88：rank 1..6 → 阈值 100/500/1500/5000/10000/30000，俸禄 1/10/30/50/100/200
#  · 晋升主逻辑 0x4ab1d0：new_rank=cur+1；须 new_rank < 主君職位；须 勲功>=阈值[new_rank]
#  · 城主(8) 是城表派生状态（word[城表+0x0a]=武将编号），不写進 3-bit 職位字段（set_rank 掩码 and 0xF8FF）
#  · 城主任命 0x4d7c20：rank>4 + 候选有效 + 城有效 + 礼法(byte[+0x11]&3)!=0
#  · 大名继承 0x4a3d70：继承人→大名(7)+勲功拉满；嫡系→宿老(6)+忠诚100；其它忠诚=max(30,rand+byte[+0x29])

## 通用覆盖层读取（任意武将 pid，不限于主角）
func _ov_rank(p: int) -> int:
	if _rank_override.has(p):
		return int(_rank_override[p])
	return int(GameData.get_officer(p).get("rank", 0))

func _ov_salary(p: int) -> int:
	if _salary_override.has(p):
		return int(_salary_override[p])
	return int(GameData.get_officer(p).get("salary", 0))

func _ov_city(p: int) -> int:
	if _city_override.has(p):
		return int(_city_override[p])
	return int(GameData.get_officer(p).get("city", ConstsRef.NONE_CITY))

func _ov_merit(p: int) -> int:
	if _merit_override.has(p):
		return int(_merit_override[p])
	return mini(int(GameData.get_officer(p).get("merit", 0)), ConstsRef.MERIT_CAP)

func _ov_skills(p: int) -> Array:
	if _skill_override.has(p):
		return (_skill_override[p] as Array).duplicate()
	return (GameData.get_officer(p).get("skill_levels", []) as Array).duplicate()

## 主角有效職位/俸禄/居城（便捷封装）
func _effective_rank() -> int:  return _ov_rank(pid)
func _effective_salary() -> int: return _ov_salary(pid)
func _effective_city() -> int:  return _ov_city(pid)

## 阈值/俸禄/職位 查表
func threshold_of(rank: int) -> int:
	return int(ConstsRef.RANK_MERIT_THRESHOLDS.get(rank, -1))

func stipend_of(rank: int) -> int:
	return int(ConstsRef.RANK_STIPENDS.get(rank, -1))

## 勲功 → 職位（0x49fc60：自高到低首个阈值<=勲功，兜底 1）
func rank_from_merit(merit: int) -> int:
	for r in [6, 5, 4, 3, 2, 1]:
		if merit >= threshold_of(r):
			return r
	return 1

func rank_ladder_name_of(rank: int) -> String:
	var idx: int = clampi(rank, 0, ConstsRef.RANK_NAMES.size() - 1)
	return ConstsRef.RANK_NAMES[idx]

# —— 城主派生状态（城堡表 f0a 字段 + 运行期覆盖层）——
## 返回城主武将编号；无城主返回 ConstsRef.NONE_CITY(255)
func get_castle_lord(castle_id: int) -> int:
	if _castle_lord_override.has(castle_id):
		return int(_castle_lord_override[castle_id])
	var c := GameData.get_castle(castle_id)
	if c.is_empty():
		return ConstsRef.NONE_CITY
	return int(c.get("f0a", ConstsRef.NONE_CITY))

## pid 是否为任意城的城主
func is_castle_lord(p: int) -> bool:
	for cid in range(ConstsRef.CASTLE_COUNT):
		if get_castle_lord(cid) == p:
			return true
	return false

# —— 勲功阈值晋升（复刻 0x4ab1d0）——
## 对 target_pid 尝试 +1 级。须满足：
##  · 同城规避：self_pid 非浪人且与 target 同城 → 跳过
##  · new_rank = cur+1 须 严格 < lord_rank（不得达到/超过主君）
##  · 勲功(word[+0x26]) >= 阈值表[new_rank]
## 返回 {ok, reason, pid, from, to}
func try_promote(target_pid: int, lord_rank: int, self_pid: int = -1) -> Dictionary:
	var res := {"ok": false, "reason": "", "pid": target_pid, "from": 0, "to": 0}
	var t := GameData.get_officer(target_pid)
	if t.is_empty():
		res["reason"] = "no_officer"; return res
	var cur: int = _ov_rank(target_pid)
	res["from"] = cur
	# ① 同城规避
	if self_pid >= 0 and self_pid != target_pid and _ov_rank(self_pid) != 0 \
			and _ov_city(self_pid) == _ov_city(target_pid):
		res["reason"] = "same_city"; return res
	# ② 逐级只升 1 级，且须严格小于主君職位
	var new_rank: int = cur + 1
	if new_rank >= lord_rank:
		res["reason"] = "not_below_lord"; return res
	# ③ 勲功达标判定
	var th: int = threshold_of(new_rank)
	if th < 0 or _ov_merit(target_pid) < th:
		res["reason"] = "merit_low"; return res
	# ④ 生效
	_rank_override[target_pid] = new_rank
	var sp: int = stipend_of(new_rank)
	if sp >= 0:
		_salary_override[target_pid] = sp
	res["ok"] = true
	res["to"] = new_rank
	return res

# —— 城主任命（复刻 0x4d7c20）——
## 门槛：rank > 4（家老5/宿老6）+ 候选有效(=target 存在) + 城有效 + 礼法(byte[+0x11]&3)!=0
## 返回 {ok, reason}
func can_appoint_castle_lord(target_pid: int, target_city: int) -> Dictionary:
	var res := {"ok": false, "reason": ""}
	var t := GameData.get_officer(target_pid)
	if t.is_empty():
		res["reason"] = "no_officer"; return res
	var r: int = _ov_rank(target_pid)
	if r <= ConstsRef.CASTLE_LORD_MIN_RANK:
		res["reason"] = "rank_too_low"; return res
	if target_city < 0 or target_city >= ConstsRef.CASTLE_COUNT:
		res["reason"] = "no_castle"; return res
	var sk: Array = _ov_skills(target_pid)
	var etq: int = int(sk[8]) if sk.size() > 8 else 0   # 礼法 = 技能索引 8
	if (etq & 3) == 0:
		res["reason"] = "no_etiquette"; return res
	res["ok"] = true
	return res

## 任命城主：写入城表派生状态 + 更新武将居城
## 返回 {ok, reason, pid, city}
func appoint_castle_lord(target_pid: int, target_city: int) -> Dictionary:
	var chk := can_appoint_castle_lord(target_pid, target_city)
	if not chk["ok"]:
		return {"ok": false, "reason": chk["reason"], "pid": target_pid, "city": target_city}
	_castle_lord_override[target_city] = target_pid
	_city_override[target_pid] = target_city
	return {"ok": true, "reason": "appointed", "pid": target_pid, "city": target_city}

# —— 大名继承（复刻 0x4a3d70）——
## 继承人→大名(7)+勲功拉满(60000)；嫡系(父ID==dead)==宿老(6)+忠诚100；
## 其它忠诚=max(30, rand_val + loyalty_base)。
## retainers: Array[Dictionary] = [{pid, father_id, rand_val, loyalty_base}]
## 返回 {ok, reason, heir_rank, heir_merit, retainers:[{pid,rank,loyalty}]}
func inherit_daimyo(dead_pid: int, heir_pid: int, retainers: Array) -> Dictionary:
	var res := {"ok": false, "reason": "", "heir_rank": -1, "heir_merit": -1, "retainers": []}
	var heir := GameData.get_officer(heir_pid)
	if heir.is_empty():
		res["reason"] = "no_heir"; return res
	# 继承人 → 大名 + 勲功拉满
	_rank_override[heir_pid] = 7
	_merit_override[heir_pid] = ConstsRef.MERIT_CAP
	res["heir_rank"] = 7
	res["heir_merit"] = ConstsRef.MERIT_CAP
	for r in retainers:
		var rp: int = int(r.get("pid", -1))
		if rp < 0:
			continue
		var rf: int = int(r.get("father_id", -1))       # word[+0x2a] 父ID
		var rnd: int = int(r.get("rand_val", 0))
		var lbase: int = int(r.get("loyalty_base", 0))  # byte[+0x29]
		var lo: int
		if rf == dead_pid:
			_rank_override[rp] = 6     # 宿老
			lo = 100
		else:
			lo = maxi(30, rnd + lbase)
		_loyalty_override[rp] = lo
		res["retainers"].append({"pid": rp, "rank": int(_rank_override.get(rp, _ov_rank(rp))), "loyalty": lo})
	res["ok"] = true
	return res
