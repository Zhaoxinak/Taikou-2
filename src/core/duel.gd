extends RefCounted
## DuelSim — 单挑（一骑讨）卡牌对战 伤害与 AI 决策 Godot 复刻
##
## 权威结构：
##   scripts/duel_spec.json            （续62/91/92/93）
##   scripts/duel_ref.py               （伤害基表/上限表/三段式，11/11 自检）
##   scripts/duel2_ref.py              （跳表 + 大额公式 + 暴击 + 瞬杀，15/15 自检）
##   scripts/duel3_ref.py              （AI 一击必杀决策 + 派发，21/21 自检）
##   scripts/duel_hp_ref.py            （初值=体力状态值，17/17 自检）
##
## 反汇编锚点：
##   跳表 0x4684c0（5 个 dword 目标，索引=动作码 0..4）
##   常规三段式 0x4687b0→0x4698d0→0x466340（4×7 基表 0x505020 + 上限表 0x504d40）
##   大额公式 0x467c80/0x468000；暴击 0x467a70；瞬杀阈值 0x468000
##   AI 一击必杀决策 0x469310（仅 {普通攻击(0), 一击必杀(4)}，续93 实锤）
##
## ⚠️ 不声明 class_name（--script 无头模式不建全局类缓存，统一用 preload 引用）。
##   DuelRng 作为内部类提供；取实例用 DuelSim.new_rng()（避免无头模式内部类引用歧义）。

# ============================================================ 常量
const ACTION_NORMAL  : int = 0   # 普通攻击
const ACTION_AIM     : int = 1   # 瞄准
const ACTION_QUICK   : int = 2   # 快刀
const ACTION_VITAL   : int = 3   # 击中要害
const ACTION_IKILL   : int = 4   # 一击必杀

# 派发表 0x4684c0（索引=动作码 → handler VA）
const JUMP_TABLE : Dictionary = {
	0: 0x468457,
	1: 0x468489,
	2: 0x468495,
	3: 0x4684a0,
	4: 0x4684a9,
}
const ACTION_NAMES : Dictionary = {
	0: "普通攻击", 1: "瞄准", 2: "快刀", 3: "击中要害", 4: "一击必杀",
}

# 0x466470：行动代码 ∈ {3,4,5} → 1
const IKILL_ACTIONS : Array = [3, 4, 5]
# 0x469310 阈值封顶
const THRESH_CAP : int = 0x46   # 70
# 续93：AI 单挑行动谱严格 = {普通攻击(0), 一击必杀(4)}
const AI_ACTION_REPERTOIRE : Array = [0, 4]

# 伤害基表 4×7 word（0x505020，值 0..3）— 续63 自校验
const DMG_BASE_TABLE : Array = [
	[0, 0, 0, 0, 0, 1, 1],
	[0, 0, 0, 1, 1, 1, 2],
	[0, 0, 1, 1, 1, 2, 2],
	[0, 1, 1, 1, 2, 2, 3],
]
# 上限表 4 word（0x504d40）：[1,2,2,3]
const DMG_CAP_TABLE : Array = [1, 2, 2, 3]
const TIER_COLS : int = 7
const BONUS_P15 : int = 15   # 15%
const BONUS_P55 : int = 55   # 55%

# ============================================================ 运行期状态
var hp_a : int = 100   # word[0x514995] 侧 A 体力
var hp_b : int = 100   # word[0x514835] 侧 B 体力
var attacker_flag : int = 0   # dword[0x514808]：!=0 扣 B，==0 扣 A（0x466340 语义）

# 大额公式全局（0x514xxx）— 由 _set_globals_for() 从战斗员派生（来源 still_unknown，见下）
var g978 : int = 0   # >>2 &3 = 系数A / 暴击概率基数
var g993 : int = 0   # //3 加伤
var g833 : int = 0   # 一击必杀瞬杀阈值用 //3
var g818 : int = 0   # &3 = 系数B
var g81a : int = 0   # &0x38 → 伤害减半
var g995 : int = 0   # <20 → +20

# 技能档（0x466e80）：acting side 取 skill_tier_a，否则 skill_tier_b（&3）
var skill_tier_a : int = 0
var skill_tier_b : int = 0


# ============================================================ DuelRng（确定性随机源）
class DuelRng:
	var _queue : Array = []
	var _seed : int = 1
	var _state : int = 1

	func seed(n: int) -> void:
		_seed = int(n) & 0x7FFFFFFF
		_state = _seed if _seed != 0 else 1

	func _next_lcg() -> int:
		_state = (1103515245 * _state + 12345) & 0x7FFFFFFF
		return _state

	## 脚本化队列：注入确定随机序列（按 FIFO 消费），用于无头自测对齐 Python ref。
	func push_queue(values: Array) -> void:
		_queue.append_array(values)

	## 消费队首脚本值；无脚本则 LCG 折到 [a,b]（b>=a）。
	func next_int(a: int, b: int) -> int:
		if _queue.size() > 0:
			return int(_queue.pop_front())
		var span : int = b - a + 1
		if span <= 0:
			return a
		return a + (_next_lcg() % span)

	## 0x4ebd60 保护：n<2 直接 0（无除零风险）。
	func rand_n(n: int) -> int:
		if n < 2:
			return 0
		return next_int(0, n - 1)

	## 概率 p%（0..100）命中。
	func next_percent(p: int) -> bool:
		return next_int(0, 99) < p


## 工厂：取一个 DuelRng 实例（无头模式内部类引用安全）。static 便于 DuelRef.new_rng() 直接取。
static func new_rng() -> DuelRng:
	return DuelRng.new()


# ============================================================ 技能档
func skill_tier(acting_side_flag: int) -> int:
	return (skill_tier_a if acting_side_flag else skill_tier_b) & 3


# ============================================================ 常规三段式伤害
## 0x4687b0：档位 → word[0x5149a4]
func damage_tier(tier_idx: int, action_code: int, might: int, r_base: int, r_bonus: int) -> int:
	var base : int = int(DMG_BASE_TABLE[tier_idx][r_base % TIER_COLS])
	if action_code != 3 and action_code != 4 and might < 60:
		var mod : int = 4 - int(might / 20)
		if mod >= 2:
			base += r_bonus % mod
	base = min(base, int(DMG_CAP_TABLE[tier_idx]))
	return base


## 0x4698d0：伤害值 = bonus(rand%100) + rand()%tier
func damage_value(tier: int, r100: int, r_rand: int) -> int:
	var bonus : int
	if r100 < BONUS_P15:
		bonus = 0
	elif r100 < BONUS_P55:
		bonus = 1
	else:
		bonus = 2
	if tier >= 2:
		return bonus + (r_rand % tier)
	return bonus


## 0x4687b0→0x4698d0 完整一次常规伤害（档位, 伤害值）。
func duel_damage(tier_idx: int, action_code: int, might: int, r_base: int, r_bonus: int, r100: int, r_rand: int) -> Array:
	var t : int = damage_tier(tier_idx, action_code, might, r_base, r_bonus)
	return [t, damage_value(t, r100, r_rand)]


## 运行期常规伤害（消耗随机，域 0..4）。
func compute_regular_damage(rng: DuelRng, action_code: int, might: int, acting_side_flag: int) -> int:
	var tier_idx : int = skill_tier(acting_side_flag)
	var r_base : int = rng.next_int(0, TIER_COLS - 1)
	var r_bonus : int = rng.next_int(0, 99)
	var t : int = damage_tier(tier_idx, action_code, might, r_base, r_bonus)
	var r100 : int = rng.next_int(0, 99)
	var r_rand : int = rng.rand_n(t)
	return damage_value(t, r100, r_rand)


## 0x466340：逐点扣血（每点一帧动画）。attacker_flag!=0 扣 B，否则扣 A。
func apply_damage(hp_a: int, hp_b: int, attacker_flag: int, dmg: int) -> Array:
	var a : int = hp_a
	var b : int = hp_b
	var n : int = max(0, dmg)
	for _i in n:
		if attacker_flag != 0:
			b -= 1
		else:
			a -= 1
	return [a, b]


# ============================================================ 大额伤害路径（击中要害/一击必杀）
## 复刻 0x467c80/0x468000 大额公式。返回 {damage, halved}。
func large_damage(rng: DuelRng) -> Dictionary:
	var dmg : int = rng.next_int(0, 39)            # rand() % 0x28 (40)
	var A : int = (g978 >> 2) & 3
	dmg += A * 10                                  # (0x514978>>2)&3 * 10
	dmg += int(g993 / 3)                           # 0x514993 / 3
	if g995 < 0x14:                                # 0x514995 < 20
		dmg += 0x14                                # +20
	var B : int = g818 & 3
	dmg += B * 10                                  # (0x514818 & 3) * 10
	var halved : bool = (g81a & 0x38) != 0
	if halved:
		dmg = int(dmg / 2)                         # 减半
	return {"damage": dmg, "halved": halved}


## 复刻 0x467a70：概率门 ((0x514978>>2)&3)*3 % → 暴击。
func crit_roll(rng: DuelRng) -> bool:
	var p : int = ((g978 >> 2) & 3) * 3
	return rng.next_int(0, 99) < p


## 单次攻击总管（对齐 duel2_ref.attack_damage）。
## action 0/1/2 → 常规域；action 3/4 → 大额路径（3 走暴击，4 走瞬杀阈值）。
func attack_damage(action: int, rng: DuelRng) -> Dictionary:
	if action == 0 or action == 1 or action == 2:
		var dmg : int = compute_regular_damage(rng, action, might(), action_as_flag_for_self())
		return {"action": action, "name": ACTION_NAMES[action], "damage": dmg,
		        "large": false, "crit": false, "instakill": false}
	var res : Dictionary = large_damage(rng)
	var dmg : int = int(res["damage"])
	var halved : bool = res["halved"]
	var crit : bool = false
	var instakill : bool = false
	if action == 3:
		crit = crit_roll(rng)
	else:   # action == 4
		var threshold : int = int(g833 / 3) + (g818 & 3) * 10
		if dmg > threshold:
			instakill = true
	return {"action": action, "name": ACTION_NAMES[action], "damage": dmg,
	        "large": true, "crit": crit, "instakill": instakill, "halved": halved}


# 普通攻击时 acting_side 视为我方（flag=0）；仅为 compute_regular_damage 取技能档用。
func action_as_flag_for_self() -> int:
	return 0


# 当前 attacker 武力（普通攻击路径用）。默认取 A 侧；auto_battle 会按需覆盖。
var _might_override : int = -1
func might() -> int:
	return _might_override if _might_override >= 0 else 50


## 复刻跳表 0x4684c0：动作码 → handler VA；非法代码返回 -1。
func dispatch(action: int) -> int:
	if not JUMP_TABLE.has(action):
		return -1
	return int(JUMP_TABLE[action])


# ============================================================ AI 一击必杀决策（0x469310）
## 0x466470：行动代码 ∈ {3,4,5} → 1。
func check_action_code(action: int) -> int:
	return 1 if (action == 3 or action == 4 or action == 5) else 0


## 0x469310 阈值（不含 0x21 / strength 比较）。bit5 置位封顶 70。
func compute_threshold(tier: int, enemy_hp: int, char8_bit5: bool) -> int:
	var t : int = tier * 10 + enemy_hp
	if char8_bit5:
		return min(t, THRESH_CAP)
	return t + 0x0A


## AI 是否发动一击必杀（0x469310）。
## char 字段（原版角色结构体偏移）：
##   0xb 武力/强度；0xf 高2位(>>6) 熟练档；0x8 bit5 阈值封顶；0x21 >=0x41 才有必杀技。
func ai_decide_ikill(char: Dictionary, enemy_hp: int, tier: int) -> bool:
	var strength : int = int(char[0xb]) + ((int(char[0xf]) >> 6) * 10)
	var char8_bit5 : bool = (int(char[0x8]) & 0x20) != 0
	var threshold : int = compute_threshold(tier, enemy_hp, char8_bit5)
	return int(char[0x21]) >= 0x41 and strength > threshold


## 综合 AI 选牌：默认普通攻击(0)；满足 0x469310 条件升级一击必杀(4)。
## 返回 {action, ikill_flag}（续93：AI 行动谱严格 = {0,4}）。
func ai_select_action(char: Dictionary, enemy_hp: int, tier: int) -> Dictionary:
	if ai_decide_ikill(char, enemy_hp, tier):
		return {"action": 4, "ikill_flag": 1}
	return {"action": 0, "ikill_flag": 0}


# ============================================================ auto_battle（收尾驱动）
## 由武将 char 字典（build_char_from_officer 产物，含 0xb/0xf/0x8/0x21 + hp/might/skill_tier）
## 驱动一场单挑到一方 HP<=0。返回 {winner, rounds, a_hp, b_hp, log}。
##
## ⚠️ 大额公式全局(0x514xxx)的来源原版未完全逆向（still_unknown），
##    _set_globals_for 用武将字段近似派生供模拟；伤害公式本身精确。
func auto_battle(a_char: Dictionary, b_char: Dictionary, rng: DuelRng, max_rounds: int = 300) -> Dictionary:
	var a_hp : int = int(a_char.get("hp", 100))
	var b_hp : int = int(b_char.get("hp", 100))
	var log : Array = []
	var rounds : int = 0
	while rounds < max_rounds and a_hp > 0 and b_hp > 0:
		rounds += 1
		# A 行动（AI，acting=A → flag 0）
		_set_globals_for(a_char, false)
		_might_override = int(a_char.get("might", int(a_char.get(0xb, 50))))
		skill_tier_a = int(a_char.get("skill_tier", (int(a_char.get(0xf, 0)) >> 6) & 3)) & 3
		var a_sel : Dictionary = ai_select_action(a_char, b_hp, skill_tier_a)
		var a_res : Dictionary = _resolve_attack(int(a_sel["action"]), rng, _might_override, false)
		b_hp -= int(a_res["damage"])
		log.append({"round": rounds, "side": "A", "action": a_sel["action"], "dmg": a_res["damage"]})
		if b_hp <= 0:
			break
		# B 行动（AI，acting=B → flag 非0）
		_set_globals_for(b_char, true)
		_might_override = int(b_char.get("might", int(b_char.get(0xb, 50))))
		skill_tier_b = int(b_char.get("skill_tier", (int(b_char.get(0xf, 0)) >> 6) & 3)) & 3
		var b_sel : Dictionary = ai_select_action(b_char, a_hp, skill_tier_b)
		var b_res : Dictionary = _resolve_attack(int(b_sel["action"]), rng, _might_override, true)
		a_hp -= int(b_res["damage"])
		log.append({"round": rounds, "side": "B", "action": b_sel["action"], "dmg": b_res["damage"]})
	var winner : String = "draw"
	if a_hp <= 0 and b_hp <= 0:
		winner = "draw"
	elif b_hp <= 0:
		winner = "A"
	elif a_hp <= 0:
		winner = "B"
	return {"winner": winner, "rounds": rounds, "a_hp": max(0, a_hp), "b_hp": max(0, b_hp), "log": log}


## 解析一次攻击（action + 随机 → 伤害结果字典）。
func _resolve_attack(action: int, rng: DuelRng, might_val: int, acting_side_flag: int) -> Dictionary:
	if action == 0 or action == 1 or action == 2:
		var dmg : int = compute_regular_damage(rng, action, might_val, acting_side_flag)
		return {"action": action, "damage": dmg, "large": false, "crit": false, "instakill": false}
	var res : Dictionary = large_damage(rng)
	var dmg : int = int(res["damage"])
	var crit : bool = false
	var instakill : bool = false
	if action == 3:
		crit = crit_roll(rng)
	else:
		var threshold : int = int(g833 / 3) + (g818 & 3) * 10
		if dmg > threshold:
			instakill = true
	return {"action": action, "damage": dmg, "large": true, "crit": crit, "instakill": instakill}


## 用武将字段近似派生大额公式全局（来源 still_unknown，仅供模拟）。
func _set_globals_for(char: Dictionary, acting_side_flag: int) -> void:
	var st : int = int(char.get("skill_tier", (int(char.get(0xf, 0)) >> 6) & 3)) & 3
	g978 = (st & 3) << 2
	g993 = int(char.get("might", int(char.get(0xb, 0))))
	g833 = int(char.get("hp", 100))
	g818 = st & 3
	g81a = 0
	g995 = int(char.get("hp", 100))


## 由 GameData 武将字典构造 AI 决策用的 raw-offset char 字典。
## ⚠️ 原版角色结构体(0xb/0xf/0x8/0x21 偏移)到本复刻 officer 字段的映射未完全逆向，
##    此处用 武力/技能档 近似派生；伤害/AI 决策公式本身精确。
static func build_char_from_officer(officer: Dictionary) -> Dictionary:
	var forces : Dictionary = officer.get("forces", {})
	var martial : int = int(forces.get("martial", 50))
	var skill_tier : int = int(clamp(martial / 25, 0, 3))   # 近似技能档 0..3
	var has_ikill : bool = martial >= 90                     # 近似：强力武将具必杀技
	var hp : int = int(officer.get("stamina_max", 100))
	var f_byte : int = (skill_tier & 3) << 6
	var eight : int = 0x20 if has_ikill else 0
	var twentyone : int = 0x50 if has_ikill else 0x30
	return {
		0xb: martial,
		0xf: f_byte,
		0x8: eight,
		0x21: twentyone,
		"hp": hp,
		"might": martial,
		"skill_tier": skill_tier,
	}
