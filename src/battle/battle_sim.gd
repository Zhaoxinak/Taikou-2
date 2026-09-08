# battle_sim.gd — 太阁立志传2 合战「兵力消耗（attrition）」结算引擎（M2）
#
# 纯逻辑移植，零 Node / UI 依赖（src/battle 分层铁律：可无头批量跑）。
# 公式来源：docs/specs/BATTLE_SPEC.md §9，主函数 0x42d270。
# 权威参考实现：scripts/battle_formula_ref.py（Python，自检通过）。
# 本文件与 Python ref 逐行对应，可由 tools/_test_battlesim.gd 做 bit-for-bit 校验。
#
# ⚠️ 数值契约（复刻直接照抄，勿改）：
#   - side0 恒 ×80%（同类大将再 ×80%）→ 不对称写死，删则平衡崩。
#   - 每回合每存活单位至少掉 1 兵 → 战斗必然收敛，不会僵持。

class_name BattleSim
extends RefCounted

# —— 常量表（来自 EXE，见 BATTLE_SPEC §9.3/§9.4/§9.5）——
const ATTACK_DIVISOR_TABLE: PackedInt32Array = [
	10, 12, 15, 7, 7, 15, 100, 100,
	10, 10, 12, 7, 7, 10, 10, 8,
	100, 100, 12, 12]
const ATTACK_DIV_WINDOW_FLAG_SET := 0   # battle_type != 0 -> 基址 0x503770
const ATTACK_DIV_WINDOW_FLAG_CLR := 8   # battle_type == 0 -> 基址 0x503778
const DEF_STAT_DIVISOR_BASE := 50
const ATTACK_NUMERATOR := 7             # (x<<3)-x
const STRENGTH_DIVISOR := 23            # 魔数 0xb21642c9/sar4 == //23
const MORALE_SCALE_DIV := 10
const EQUIP_W_CAT1 := 15
const FLAT_CAT1 := 20
const EQUIP_W_CAT2 := 25
const FLAT_CAT2 := 10
const MIN_UNIT_STRENGTH := 10

# 部署图左右军 ASCII 特判集（BATTLE_SPEC §3 解码器）
const LEFT_ARMY_CHARS := ["/", "1", "7", "9"]
const RIGHT_ARMY_CHARS := ["+", "-", "3", "5"]
# 每阵营单位槽上限（原版 15 槽；deploy 格远多于 15，采样对齐）
const MAX_UNITS_PER_SIDE := 15


# ============================================================== 数据结构

class BattleUnit:
	extends RefCounted
	var troops: int = 0          # +0x0c 兵力（结算后回写）
	var morale: int = 0           # +0x11
	var morale_loss: int = 0      # +0x12
	var state: int = 0            # +0x13 低2位=兵种类别, 高4位!=0=已退场
	var side_flag: int = 0        # +0x15 bit2=阵营
	var stat_atk: int = 0         # 0x43e200 obj[0x0b]
	var stat_def: int = 0         # 0x43e260 obj[0x0a]
	var equip_tier: int = 0       # 0x43e220 0..3
	var indirect: bool = false    # 由 [slot] 间接解析 -> stat 减半

	func active() -> bool:
		return (state & 0xF0) == 0

	func category() -> int:
		return state & 3

	func side() -> int:
		return 1 if (side_flag & 4) else 0

	func atk() -> int:
		return stat_atk >> 1 if indirect else stat_atk

	func dfn() -> int:
		return stat_def >> 1 if indirect else stat_def


class BattleCommander:
	extends RefCounted
	var col: int = 0      # +0x00 -> section A 列 c (0..19)
	var row: int = 0      # +0x02 -> section A 行 a (0..8)
	var kind: int = 0     # +0x04 两将相同 -> 额外 80% 衰减
	var flags: int = 0    # +0x2c bit4 -> 对方战力减半


class BattleCtx:
	extends RefCounted
	var units: Array = []              # 15 槽（实际可 >15，采样对齐原版）
	var sect_a: PackedByteArray = PackedByteArray()  # HJMAPDAT section A：9*20 字节
	var battle_type: int = 3          # 0x513548 选攻击除数窗口（3=野戦 !=0）
	var mode_m1: int = 0              # 0x511bf8 !=0 -> side1 免伤 & 战力÷8(配合 parity)
	var mode_m2: int = 0              # 0x51352c !=0 -> cat2 走 2/3 分支
	var parity_flag: int = 0          # 0x513540 & 1
	var handle_stat: int = 0          # 0x513534 +0x0d
	var aux_zero: bool = true         # 0x43e870(c,a) 指向字节是否为 0
	var cmd_a: BattleCommander = null # 构建时附带的大将 A
	var cmd_b: BattleCommander = null # 构建时附带的大将 B


# ============================================================== 基础原语

static func idiv(a: int, b: int) -> int:
	return int(a / b) if b != 0 else 0


static func satsub(a: int, b: int) -> int:
	return maxi(a - b, 0)


static func muldiv(a: int, b: int, c: int) -> int:
	return 0xFFFF if c == 0 else idiv(a * b, c)


# 兵力边际收益曲线（0x43cd10，分段线性处处连续）
static func troop_scale(troops: int) -> int:
	var t: int = troops
	if t <= 100:
		return t
	if t <= 300:
		return idiv(t, 2) + 50
	if t <= 500:
		return idiv(t, 4) + 125
	if t <= 1000:
		return idiv(t, 5) + 150
	return idiv(3 * t, 20) + 200


# ============================================================== section A

static func sect_a_lo(ctx: BattleCtx, c: int, a: int) -> int:
	var idx: int = a * 20 + c
	if idx < 0 or idx >= ctx.sect_a.size():
		return 0
	return ctx.sect_a[idx] & 0x0F


static func sect_a_hi(ctx: BattleCtx, c: int, a: int) -> int:
	var idx: int = a * 20 + c
	if idx < 0 or idx >= ctx.sect_a.size():
		return 0
	return ctx.sect_a[idx] >> 4


# 攻击除数（0x43a9c0）：v==10 时叠加 handle_stat 修正
static func attack_divisor(ctx: BattleCtx, c: int, a: int) -> int:
	var v: int = sect_a_lo(ctx, c, a)
	var d: int
	if ctx.battle_type != 0:
		d = ATTACK_DIVISOR_TABLE[ATTACK_DIV_WINDOW_FLAG_SET + v]
	else:
		d = ATTACK_DIVISOR_TABLE[ATTACK_DIV_WINDOW_FLAG_CLR + v]
		if v == 10:
			d += idiv(ctx.handle_stat, 50 if ctx.aux_zero else 100)
	return d


# ============================================================== 战力汇总

static func army_strength(ctx: BattleCtx, side: int) -> int:
	var total := [0, 0]
	for u in ctx.units:
		var unit := u as BattleUnit
		if unit == null or not unit.active():
			continue
		var cat: int = unit.category()
		var v: int
		if cat == 1:
			v = unit.atk() + EQUIP_W_CAT1 * unit.equip_tier + FLAT_CAT1
		elif cat == 2:
			if ctx.mode_m2:
				v = idiv(unit.atk() * 2, 3)
			else:
				v = unit.atk() + EQUIP_W_CAT2 * unit.equip_tier + FLAT_CAT2
		else:
			v = unit.atk()
		var m: int = satsub(unit.morale, unit.morale_loss)
		v = idiv(v * (100 + idiv(m, MORALE_SCALE_DIV)), 100)
		v = maxi(v, MIN_UNIT_STRENGTH)
		v = idiv(v * troop_scale(unit.troops), STRENGTH_DIVISOR)
		total[unit.side()] += v
	return total[side]


static func count_side(ctx: BattleCtx, side: int) -> int:
	var n := 0
	for u in ctx.units:
		var unit := u as BattleUnit
		if unit != null and unit.active() and unit.side() == side:
			n += 1
	return n


static func side1_strength(ctx: BattleCtx) -> int:
	var v: int = army_strength(ctx, 1)
	if ctx.mode_m1 and ctx.parity_flag:
		v >>= 3
	return v


# side0 总战力：恒定 ×80%，同类大将再 ×80%（0x42d730，不读任何 flags 位）
static func side0_strength(ctx: BattleCtx, pA: BattleCommander, pB: BattleCommander) -> int:
	var v: int = army_strength(ctx, 0)
	v = idiv(4 * v, 5)
	if pA.kind == pB.kind:
		v = idiv(4 * v, 5)
	return v


# ============================================================== 一回合结算（0x42d270）

static func battle_round(ctx: BattleCtx, pA: BattleCommander, pB: BattleCommander) -> Dictionary:
	var n0: int = count_side(ctx, 0)
	var n1: int = count_side(ctx, 1)
	var S1: int = side1_strength(ctx)
	var S0: int = side0_strength(ctx, pA, pB)

	# 除以「对方」单位数 —— 攻击力摊薄到防守方每个单位
	var E1: int = idiv(S1, n0) * 2 if n0 > 0 else 0
	var E0: int = idiv(S0, n1) * 2 if n1 > 0 else 0

	var hiB: int = sect_a_hi(ctx, pB.col, pB.row)
	var hiA: int = sect_a_hi(ctx, pA.col, pA.row)

	var modB: int = attack_divisor(ctx, pB.col, pB.row)
	if ctx.battle_type == 0:
		if hiB > hiA:
			modB += 1
		elif hiB < hiA:
			modB -= 1
	var base_vs_side0: int = idiv(E1 * ATTACK_NUMERATOR, modB) if modB != 0 else 0

	var modA: int = attack_divisor(ctx, pA.col, pA.row)
	if ctx.battle_type == 0:
		if hiA > hiB:
			modA += 1
		elif hiA < hiB:
			modA -= 1
	var base_vs_side1: int = idiv(E0 * ATTACK_NUMERATOR, modA) if modA != 0 else 0

	var casualties := [0, 0]
	var totals := [0, 0]
	for u in ctx.units:
		var unit := u as BattleUnit
		if unit == null or not unit.active():
			continue
		var side: int = unit.side()
		totals[side] += unit.troops
		var base: int = base_vs_side0 if side == 0 else base_vs_side1
		var dmg: int = idiv(base, idiv(unit.dfn(), 4) + DEF_STAT_DIVISOR_BASE) + 1
		if side == 1 and ctx.mode_m1:
			dmg = 0                      # 0x42d446 side1 免伤
		var remain: int = satsub(unit.troops, dmg)
		casualties[side] += unit.troops - remain
		unit.troops = remain            # 0x42d468 写回
	return {
		"casualties_side0": casualties[0],
		"casualties_side1": casualties[1],
		"loss_pct_side0": muldiv(casualties[0], 100, totals[0]),
		"loss_pct_side1": muldiv(casualties[1], 100, totals[1]),
	}


# ============================================================== 整场模拟

static func alive_troops(ctx: BattleCtx, side: int) -> int:
	var s := 0
	for u in ctx.units:
		var unit := u as BattleUnit
		if unit != null and unit.active() and unit.side() == side:
			s += unit.troops
	return s


# 跑完整场（多回合），直到某方兵力归零或达 max_rounds。
# 返回 {winner, rounds, side0_troops, side1_troops, converged}
static func simulate(ctx: BattleCtx, pA: BattleCommander, pB: BattleCommander,
		max_rounds: int = 2000) -> Dictionary:
	var rounds := 0
	while rounds < max_rounds:
		battle_round(ctx, pA, pB)
		rounds += 1
		if alive_troops(ctx, 0) <= 0 or alive_troops(ctx, 1) <= 0:
			break
	var s0 := alive_troops(ctx, 0)
	var s1 := alive_troops(ctx, 1)
	var winner := -1
	if s0 <= 0 and s1 <= 0:
		winner = -1
	elif s0 <= 0:
		winner = 1
	elif s1 <= 0:
		winner = 0
	return {
		"winner": winner,
		"rounds": rounds,
		"side0_troops": s0,
		"side1_troops": s1,
		"converged": rounds < max_rounds,
	}


# ============================================================== 从 battles.json 构建（M2 fixture）

# ⚠️ 真实「武将→战单位」映射尚未导出（属 M3+ 玩法层）。这里用部署图 + section A
# 构造一个**确定性合成**的 BattleCtx，目的是在 38 张真实地形/sectionA 上验证引擎收敛与不变量。
# 单位数值为合成 fixture（非原版真实 roster），但结算公式与 §9 逐位一致。
static func build_ctx_from_battle(battle: Dictionary, seed: int) -> BattleCtx:
	var ctx := BattleCtx.new()

	# section A：unit_table[a]["raw"] 是 9×20 字节（实测高4位恒0，低4位即 divisor 索引）
	var sect := PackedByteArray()
	for row in battle.get("unit_table", []):
		for v in row.get("raw", []):
			sect.append(int(v) & 0xFF)
	ctx.sect_a = sect

	# 部署图 -> 左右军单元格（每个非中性格一个单位）
	var left := []
	var right := []
	var deploy: Array = battle.get("deploy", [])
	var y := 0
	for row in deploy:
		var x := 0
		for ch in row:
			var side := -1
			if ch in LEFT_ARMY_CHARS:
				side = 0
			elif ch in RIGHT_ARMY_CHARS:
				side = 1
			if side >= 0:
				if side == 0:
					left.append({"x": x, "y": y})
				else:
					right.append({"x": x, "y": y})
			x += 1
		y += 1

	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	left = _sample(left, MAX_UNITS_PER_SIDE, rng)
	right = _sample(right, MAX_UNITS_PER_SIDE, rng)
	for cell in left:
		ctx.units.append(_synth_unit(cell, 0, rng))
	for cell in right:
		ctx.units.append(_synth_unit(cell, 1, rng))

	# 大将 fixture：col/row 取 section A 首两格；kind 错开 -> 不触发额外 80%
	var pA := BattleCommander.new()
	pA.col = 0; pA.row = 0; pA.kind = 1
	var pB := BattleCommander.new()
	pB.col = 0; pB.row = 1; pB.kind = 2
	ctx.cmd_a = pA
	ctx.cmd_b = pB
	return ctx


# 取出构建时附带的大将（build_ctx_from_battle 写入）
static func commanders_of(ctx: BattleCtx) -> Dictionary:
	return {"pA": ctx.cmd_a, "pB": ctx.cmd_b}


static func _sample(arr: Array, n: int, rng: RandomNumberGenerator) -> Array:
	if arr.size() <= n:
		return arr
	var out := []
	var step := float(arr.size()) / float(n)
	for i in n:
		out.append(arr[int(i * step)])
	return out


static func _synth_unit(cell: Dictionary, side: int, rng: RandomNumberGenerator) -> BattleUnit:
	var u := BattleUnit.new()
	u.troops = 250 + int(rng.randi_range(0, 450))
	u.morale = 60 + int(rng.randi_range(0, 40))
	u.morale_loss = int(rng.randi_range(0, 25))
	u.equip_tier = int(rng.randi_range(0, 3))
	u.stat_atk = 35 + int(rng.randi_range(0, 55))
	u.stat_def = 30 + int(rng.randi_range(0, 45))
	u.state = int(rng.randi_range(0, 2))   # 低2位=兵种类别（cat = state & 3）
	u.side_flag = 4 if side == 1 else 0
	u.indirect = false
	return u


# 场景 a（与 scripts/battle_formula_ref.py 自检同参）：用于 bit-for-bit 等价校验
static func scenario_a() -> BattleCtx:
	var ctx := BattleCtx.new()
	ctx.sect_a = PackedByteArray()
	for i in 180:
		ctx.sect_a.append(3)
	ctx.battle_type = 3
	for i in 4:
		var u := BattleUnit.new()
		u.troops = 500; u.morale = 80; u.morale_loss = 10; u.state = 1
		u.side_flag = 0; u.stat_atk = 70; u.stat_def = 60; u.equip_tier = 2
		ctx.units.append(u)
	for i in 4:
		var u := BattleUnit.new()
		u.troops = 400; u.morale = 60; u.morale_loss = 20; u.state = 1
		u.side_flag = 4; u.stat_atk = 55; u.stat_def = 50; u.equip_tier = 1
		ctx.units.append(u)
	var pA := BattleCommander.new(); pA.col = 0; pA.row = 0; pA.kind = 1
	var pB := BattleCommander.new(); pB.col = 1; pB.row = 0; pB.kind = 2
	ctx.cmd_a = pA; ctx.cmd_b = pB
	return ctx
