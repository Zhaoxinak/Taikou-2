extends RefCounted
## Diplomacy — 国関係マトリクス / 外交関係 / 主从関係 / 使者归还结算（Godot 复刻）
##
## 权威：scripts/diplomacy_spec.json（续95）
##       scripts/diplomacy2_ref.py（183/183 PASS，关系矩阵与核心 API）
##       scripts/diplomacy3_ref.py（2394/2394 PASS，关系变更点与通用数学）
##       scripts/ai_diplomacy_ref.py（续104，AI 主动外交）
##
## 内存布局（原版）：
##   国政治表   0x5179b8, stride 14 B, 49 条（索引 = (ptr-0x5179b8)/14）
##   关系矩阵   0x51dc60, 1176 B = 49*48/2   ★ 每个「国对」1 字节
##   关系名称表 0x5080d0, stride 5 B, 12 项
##   颜色表     0x503e68(word[8] 外交) / 0x503e78(word[4] 主从)
##
##   每字节两个位域：bit0-2 = 外交関係(8级)，bit3-4 = 主从関係(4级)，bit5-7 未用
##
## ⚠️ 三角索引：tri_index(i,j) = i*49 - i*(i+1)/2 + (j-i-1)   （i < j）
##    🔴 已数值证伪：diplomacy_spec.json 里那句 asm 改写
##       「0x51dc5f + (j + 48*i - i*(i-1)/2)」是错的 —— 其最大值 1222 超出矩阵 1176，
##       且不能一一覆盖 0..1175。以 spec 的 "equivalent" 与 diplomacy2_ref.tri_index 为准
##       （实测 0..1175 全覆盖且唯一，见 tools/_test_diplomacy.gd）。
##
## ⚠️ 主从関係是【有向关系存于无向矩阵】：存储值 2/3 在 i>j 时镜像为 5-v（2<->3）。
##    即 A 侧读到「支配(3)」时，B 侧读到「从属(2)」。
##
## 范围：纯逻辑核心（矩阵位域 + 索引 + 筛选 + 关系变更点 + 使者功勋结算），可无头单测。
##  ⚠️ 不声明 class_name（--script 无头模式不建全局类缓存，统一用 preload 引用）。
##  ⚠️ 自含逻辑，不依赖 GameData autoload。

const N_PROV : int = 49
const INVALID : int = 49
const REL_MATRIX_N : int = 1176   # 49*48/2

# 名称表（0x5080d0 stride5，12 项 = 外交 8 + 主从 4）
const DIPL_NAMES : Array[String] = ["盟友", "亲密", "良好", "普通", "敌视", "险恶", "绝交", "交战"]
const MV_NAMES : Array[String] = ["", "同盟", "从属", "支配"]
# 颜色表（0x503e68 / 0x503e78）
const DIPL_COLOR : Array = [1, 1, 0, 0, 0, 2, 2, 2]
const MV_COLOR : Array = [0, 4, 2, 1]

# 语义常量
const DIPL_NEUTRAL : int = 3   # 普通（初始化值）
const DIPL_SEVERED : int = 6   # 绝交
const DIPL_WAR : int = 7       # 交战（恶化上限）
const MV_NONE : int = 0        # 空白
const MV_ALLY : int = 1        # 同盟
const MV_VASSAL : int = 2      # 从属
const MV_DOMINION : int = 3    # 支配

# 位域掩码
const DIPL_MASK : int = 0x07
const MV_CLEAR : int = 0xE7    # ~0x18，清 bit3-4

# 使者工作指令码（0x4c5699 写入 武将+0x16 低6位）
const WORK_SELL_FOOD : int = 2
const WORK_BUY_FOOD : int = 3
const WORK_BUY_HORSE : int = 4
const WORK_FRIENDLY : int = 9
const WORK_PRESSURE : int = 10
const WORK_COURT : int = 11
const WORK_INTEL : int = 12

# 功勋常量（0x4b9250 结算主分派）
const MERIT_FRIENDLY : int = 600
const MERIT_PRESSURE : int = 1000
const MERIT_COURT_NO_RANK : int = 800
const MERIT_COURT_RANK : int = 1000

# work -> 说明（diplomacy2_ref WORK_SETTLE）
const WORK_NAMES : Dictionary = {
	2: "卖出军粮", 3: "购入军粮", 4: "购入军马", 5: "购入洋枪", 6: "开垦农田",
	7: "筑城", 9: "友好外交", 10: "高压外交", 11: "朝廷工作", 12: "收集情报",
	13: "谋略", 18: "训练", 46: "武者修行",
}

var buf : PackedByteArray


func _init() -> void:
	reset()


func reset() -> void:
	buf = PackedByteArray()
	buf.resize(REL_MATRIX_N)


# ---------------------------------------------------------------- 索引
## 标准上三角序号（要求 i < j）。tri = i*49 - i*(i+1)/2 + (j-i-1)
func tri_index(i: int, j: int) -> int:
	return int(i * N_PROV - i * (i + 1) / 2 + (j - i - 1))


## 0x49fd80 的等价：返回 buf 下标；非法（越界/自身/负）返回 -1（= 原版 NULL 指针）。
func rel_offset(i: int, j: int) -> int:
	if i < 0 or j < 0 or i >= N_PROV or j >= N_PROV or i == j:
		return -1
	if i > j:
		var t : int = i
		i = j
		j = t
	return tri_index(i, j)


func _rec(i: int, j: int) -> int:
	return rel_offset(i, j)


# ---------------------------------------------------------------- 外交関係 (bit0-2)
## 0x49fd60
func get_diplomacy(i: int, j: int) -> int:
	var r : int = _rec(i, j)
	return 0 if r < 0 else int(buf[r] & DIPL_MASK)


## 0x49fe40 —— 只改 bit0-2（异或掩码惯用法）
func set_diplomacy(i: int, j: int, v: int) -> void:
	var r : int = _rec(i, j)
	if r < 0:
		return
	var old : int = int(buf[r])
	buf[r] = (old ^ ((v ^ old) & DIPL_MASK)) & 0xFF


# ---------------------------------------------------------------- 主从関係 (bit3-4, 有向镜像)
## 存储值 2/3 在 i>j 时镜像为 5-v（2<->3）
static func mirror(v: int, i: int, j: int) -> int:
	if (v == MV_VASSAL or v == MV_DOMINION) and i > j:
		return 5 - v
	return v


## 0x49fe70
func get_master_vassal(i: int, j: int) -> int:
	var r : int = _rec(i, j)
	if r < 0:
		return 0
	var lv : int = int(buf[r] >> 3) & 3
	return mirror(lv, i, j)


## 0x49ff10 —— 先镜像再只改 bit3-4（掩码 0xE7）
func set_master_vassal(i: int, j: int, v: int) -> void:
	var r : int = _rec(i, j)
	if r < 0:
		return
	var vv : int = mirror(v & 3, i, j)
	buf[r] = ((int(buf[r]) & MV_CLEAR) | ((vv & 3) << 3)) & 0xFF


# ---------------------------------------------------------------- 名称
func dipl_name(i: int, j: int) -> String:
	return DIPL_NAMES[get_diplomacy(i, j)]


func mv_name(i: int, j: int) -> String:
	return MV_NAMES[get_master_vassal(i, j)]


func work_name(work: int) -> String:
	return str(WORK_NAMES.get(work, ""))


# ---------------------------------------------------------------- 目标国可派筛选 0x4c4270
## mode: 0=高压外交 1=友好外交 2=收集情报
## ⚠️ 过滤用的是【主从関係】而非外交関係
func can_dispatch(mode: int, mv_rel: int) -> bool:
	if mode == 0:
		return mv_rel != MV_VASSAL and mv_rel != MV_DOMINION
	if mode == 1:
		return mv_rel == MV_NONE
	if mode == 2:
		return true
	return false


# ---------------------------------------------------------------- 关系变更点
## 0x4c2e4e —— 与所有有效国设为 普通/无主从；与 foe 设为 绝交
func init_relations(my: int, others: Array, foe: int = -1) -> void:
	for j in others:
		var jj : int = int(j)
		if jj == my:
			continue
		set_diplomacy(my, jj, DIPL_NEUTRAL)
		set_master_vassal(my, jj, MV_NONE)
	if foe >= 0:
		set_diplomacy(my, foe, DIPL_SEVERED)


## 0x4c7734 —— 势力灭亡：关系恶化一级。
## 跳过灭亡方与 skip（原版硬编码跳过国 #24 = 0x517b08，疑为京/朝廷中立国）；
## 仅当 主从(p, 灭亡方)==0 且 外交 < 7(交战) 时 +1。返回 [[p, old, new], ...]
func worsen_on_conquest(conqueror: int, alive: Array, skip: Array = []) -> Array:
	var changed : Array = []
	var skipset : Dictionary = {}
	for s in skip:
		skipset[int(s)] = true
	for p in alive:
		var pi : int = int(p)
		if pi == conqueror or skipset.has(pi):
			continue
		if get_master_vassal(pi, conqueror) != MV_NONE:
			continue
		var cur : int = get_diplomacy(pi, conqueror)
		if cur >= DIPL_WAR:
			continue
		set_diplomacy(pi, conqueror, cur + 1)
		changed.append([pi, cur, cur + 1])
	return changed


# ---------------------------------------------------------------- 通用数学
## 0x4ebcd0: (a>b)? a-b : 0（饱和减）
static func diff(a: int, b: int) -> int:
	return (a - b) if a > b else 0


## 0x4ebcf0: min((a+b) & 0xff, c) —— 先截断再取小
static func min_trunc(a: int, b: int, c: int) -> int:
	var s : int = (a & 0xff) + (b & 0xff)
	return s if s < c else c


# ---------------------------------------------------------------- 外交成功关系变更
## 0x4b5bcb 友好外交成功：set_master_vassal=1(同盟) + set_diplomacy=lv
func friendly_success(work_type: int, target: int, me: int) -> int:
	var lv : int
	if work_type < 2:
		lv = diff(1, work_type)
	elif work_type == 2:
		lv = 0
	else:
		lv = 2
	set_diplomacy(target, me, lv)
	set_master_vassal(target, me, MV_ALLY)
	return lv


## 0x4b6095 高压外交/屈服成功：set_master_vassal=3(支配) + set_diplomacy=lv
func pressure_success(work_type: int, target: int, me: int) -> int:
	var lv : int = diff(1, work_type) if work_type < 3 else 2
	set_diplomacy(target, me, lv)
	set_master_vassal(target, me, MV_DOMINION)
	return lv


## 0x47b5f0 —— 高压外交成败判定恒为成功（无随机失败分支）
static func pressure_succeeds() -> bool:
	return true


# ---------------------------------------------------------------- 使者归还结算：功勋
## 0x4b95a9..0x4b95d8: lv = min((general[0x10] & 3) + general[0x0d]/20 + 1, 7)
## （除数 20 由 magic 0x66666667 + sar 3 实测确认，非 10）
static func mission_level(g0x10: int, g0x0d: int) -> int:
	var lv : int = int((g0x10 & 3) + (g0x0d / 20) + 1)
	if lv > 7:
		lv = 7
	return lv


## 0x4b95ea..0x4b95f3: 收集情报功勋 = 城数*(lv+5) + 100
static func intel_merit(g0x10: int, g0x0d: int, city_count: int) -> int:
	return city_count * (mission_level(g0x10, g0x0d) + 5) + 100


## 工作指令码 -> 功勋（0x4b9250 结算主分派）
func mission_merit(work: int, val: int = 0, city_count: int = 0,
		g0x10: int = 0, g0x0d: int = 0, got_rank: bool = false) -> int:
	match work:
		WORK_SELL_FOOD, WORK_BUY_FOOD:
			return val * 2 + 50
		WORK_BUY_HORSE:
			return val * 4 + 100
		WORK_FRIENDLY:
			return MERIT_FRIENDLY
		WORK_PRESSURE:
			return MERIT_PRESSURE
		WORK_COURT:
			return MERIT_COURT_RANK if got_rank else MERIT_COURT_NO_RANK
		WORK_INTEL:
			return intel_merit(g0x10, g0x0d, city_count)
		_:
			return 0
