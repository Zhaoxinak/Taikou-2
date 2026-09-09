# ai_diplomacy.gd — AI 主动外交决策（原版 0x4a84e0）
#
# 逆向依据：scripts/ai_diplomacy_ref.py（续104）+ 本机实机反汇编 0x49faf0 / 0x49fbb0 /
# 0x4ebc50 / 0x4ebca0（capstone，_unpacked_mem.bin 扁平映射 off = va - 0x400000）。
#
# 调用链
# ------
#   0x4a0d50  AI 回合总驱动（每大名每回合）
#     -> 0x4a6ba0  AI think 入口（若 dword[0x52060c] != 0 则整块跳过）
#       -> 0x4a70b0  逐国派发（49 国 @0x5179b8 stride 14；要求 word[+4] < 370 且状态字节匹配）
#         -> 0x4a84e0  ★ AI 外交决策（本文件）
#
# 决策语义（确定性，无 RNG）
# --------------------------
#   LOOP 1：在「lord < 370 且 get_master_vassal(esi, self) == 2（主从=2）」的国中，
#           挑 **国力最大** 的那个 esi：
#             set_master_vassal(self, esi, 0)          ; 解除主从
#             set_diplomacy(self, esi, min(rel+2, 7))  ; 外交 +2，上限 7
#             announce MSGX 0xd1f
#   LOOP 2：由城邻接得到的邻国列表（主从 == 1），逐个同样处理，announce MSGX 0xd1e
#   净效果：AI 每回合把层级主从关系「摊平」为友好外交关系，并优先拉拢国力最强者。
#
# 国力（0x49faf0，已逐指令还原）
# -----------------------------
#   castle_sum(prov) = Σ over 该国城链表：
#       contrib = (seisan × nousang) / 25 + 100
#       若 (castle_type & 8) != 0 → contrib += 500
#       若 判定 0x49ace0 为假     → contrib /= 2      ⚠️ 见下方「未决项」
#       acc = min(acc + contrib, 60000)               ; 0x4ebca0 = min(a+b, c)
#   国力 = castle_sum(自国)
#   对每国 esi（≠自国，word[esi+4] < 370，get_master_vassal(esi, 自国) == 3）：
#       国力 = min(国力 + castle_sum(esi) × 2 / 3, 60000)   ; 0x4ebc50 = (a*b)/c
#   国力 = min(国力 × (byte[0x0c] & 0x0f) + 20) / 20, 60000)  ; 魔数 0x66666667 + sar3 = /20
#   若 (byte[0x0d] & 3) == 3 → 国力 = min(国力 × 2, 60000)
#
# ⚠️ 未决项（明确标注，勿当作已逆向）
# ----------------------------------
#   0x49ace0（判定城贡献是否减半）函数体较大（sub esp,0x1a8），本轮未完全还原。
#   本模块将其抽象为 castle 的 `full_value` 入参（默认 true = 不减半）。
#
# 设计：与 diplomacy.gd 一致，**自含、不依赖 GameData**，全部数据由 ctx 注入，便于测试。

class_name AiDiplomacy
extends RefCounted

# ── 常量（原版实测）────────────────────────────────────────
const POWER_CAP      := 60000   # 0xea60
const LORD_VALID_MAX := 370     # 0x172：word[prov+4] 需 < 370
const PROV_COUNT     := 49
const DIPLO_CAP      := 7
const DIPLO_GAIN     := 2
const MSGX_VASSAL    := 0xd1f   # LOOP 1 播报
const MSGX_NEIGHBOR  := 0xd1e   # LOOP 2 播报

const MV_VASSAL_OF_SELF := 3    # LOOP「国力」：他国 esi 主从 == 3（受 self 支配）
const MV_LOOP1_TARGET   := 2    # LOOP 1 目标：主从 == 2
const MV_LOOP2_TARGET   := 1    # LOOP 2 目标：主从 == 1
const MV_CLEAR          := 0    # 解除主从


# 整数除法（非负；避开 GDScript 整型除法语义歧义）
static func _idiv(a: int, b: int) -> int:
	if b == 0:
		return 0
	return floori(float(a) / float(b))


static func _min_cap(a: int, b: int) -> int:
	return mini(POWER_CAP, a + b)


# ── 城 / 国 国力 ───────────────────────────────────────────

## 单城贡献：(seisan × nousang) / 25 + 100；城種 & 8 → +500；full_value=false → 减半。
static func castle_contribution(seisan: int, nousang: int,
		castle_type: int, full_value: bool = true) -> int:
	var v := _idiv(seisan * nousang, 25) + 100
	if (castle_type & 8) != 0:
		v += 500
	if not full_value:
		v = _idiv(v, 2)
	return v


## 一国城力和：Σ min(acc + contrib, 60000)。
## entries: [{seisan, nousang, castle_type, full_value?}]
static func castle_sum(entries: Array) -> int:
	var acc := 0
	for e in entries:
		var fv: bool = e.get("full_value", true)
		acc = _min_cap(acc, castle_contribution(
			int(e.get("seisan", 0)),
			int(e.get("nousang", 0)),
			int(e.get("castle_type", 0)), fv))
	return acc


## 国力（0x49faf0）。
## ctx 需含：
##   castle_sums : Array[int](49)  每国 castle_sum
##   lord        : Array[int](49)  word[prov+4]
##   b0c, b0d    : Array[int](49)  byte[prov+0xc] / byte[prov+0xd]
##   get_mv      : Callable(i, j) -> int   主从関係
static func prov_power(ctx: Dictionary, idx: int) -> int:
	var sums: Array = ctx.get("castle_sums", [])
	var lord: Array = ctx.get("lord", [])
	if idx < 0 or idx >= sums.size():
		return 0

	var power: int = int(sums[idx])
	var gm: Callable = ctx.get("get_mv", Callable())

	for i in sums.size():
		if i == idx:
			continue
		if i < lord.size() and int(lord[i]) >= LORD_VALID_MAX:
			continue
		if gm.is_valid() and gm.call(i, idx) != MV_VASSAL_OF_SELF:
			continue
		var v: int = _idiv(int(sums[i]) * 2, 3)
		power = _min_cap(power, v)

	# 国力 × (n + 20) / 20，上限 60000
	var n: int = int(ctx.get("b0c", [])[idx] if idx < ctx.get("b0c", []).size() else 0) & 0x0f
	power = mini(POWER_CAP, _idiv(power * (n + 20), 20))

	# byte[0x0d] & 3 == 3 → 翻倍
	var d: int = int(ctx.get("b0d", [])[idx] if idx < ctx.get("b0d", []).size() else 0) & 3
	if d == 3:
		power = _min_cap(power, power)
	return power


## 建 49 国国力表（对应原版 0x4a8840 填 0x5259e8）
static func build_power_table(ctx: Dictionary) -> Array:
	var out: Array = []
	for i in PROV_COUNT:
		out.append(prov_power(ctx, i))
	return out


# ── AI 外交决策（0x4a84e0）──────────────────────────────────

## 返回计划变更列表（纯函数，不改动数据）：
##   [{prov, master_vassal, diplo_delta, msgx}]
## 调用方按 diplomacy.gd 的 set_master_vassal / set_diplomacy(min(rel+2,7)) 落地。
##
## ctx 额外需含：
##   power     : Array[int](49)  国力表（可由 build_power_table 产出）
##   neighbors : Array[int]      邻国（城邻接；由调用方提供）
static func decide(ctx: Dictionary, self_prov: int) -> Array:
	var out: Array = []

	# 全局开关：原版 dword[0x52060c] != 0 或 ai_active_guard 时整块跳过
	if bool(ctx.get("skip", false)) or not bool(ctx.get("ai_active", true)):
		return out

	var pw: Array = ctx.get("power", [])
	if pw.is_empty():
		pw = build_power_table(ctx)
	var lord: Array = ctx.get("lord", [])
	var gm: Callable = ctx.get("get_mv", Callable())

	# LOOP 1：主从 == 2 且 lord < 370 中，国力最大者
	var best := -1
	var best_pw := -1
	for i in mini(pw.size(), PROV_COUNT):
		if i == self_prov:
			continue
		if i < lord.size() and int(lord[i]) >= LORD_VALID_MAX:
			continue
		if gm.is_valid() and gm.call(i, self_prov) != MV_LOOP1_TARGET:
			continue
		var p: int = int(pw[i])
		if p > best_pw:
			best_pw = p
			best = i
	if best >= 0:
		out.append({
			"prov": best,
			"master_vassal": MV_CLEAR,
			"diplo_delta": DIPLO_GAIN,
			"msgx": MSGX_VASSAL,
		})

	# LOOP 2：邻国（主从 == 1）
	for i in ctx.get("neighbors", []):
		var pi: int = int(i)
		if pi == self_prov:
			continue
		if pi < lord.size() and int(lord[pi]) >= LORD_VALID_MAX:
			continue
		if gm.is_valid() and gm.call(pi, self_prov) != MV_LOOP2_TARGET:
			continue
		out.append({
			"prov": pi,
			"master_vassal": MV_CLEAR,
			"diplo_delta": DIPLO_GAIN,
			"msgx": MSGX_NEIGHBOR,
		})

	return out


## 落地后的外交关系值：min(rel + delta, 7)
static func apply_diplo_gain(rel: int, delta: int = DIPLO_GAIN) -> int:
	return mini(DIPLO_CAP, rel + delta)
