# Consts.gd — 全局常量集中定义（避免散落魔法数）
# 权威源：docs/specs/GAME_DATA_SPEC.md §1.2（续200 布局）+ §3.3

class_name Consts
extends RefCounted

# ---------------------------------------------------------------------------
# 哨兵值
# ---------------------------------------------------------------------------
const NONE_PROVINCE : int = 255
const NONE_CITY     : int = 255
const RONIN_LORD    : int = 0xFFFF
const MERIT_MAX     : int = 0xFFFF
const FATHER_NONE   : int = 0xFFFF
const SENTINEL_FFFF : int = 0xFFFF

# ---------------------------------------------------------------------------
# 数值钳制
# ---------------------------------------------------------------------------
const STAMINA_CAP   : int = 100
const FORCE_CAP     : int = 100
const SKILL_CAP     : int = 3
const MERIT_CAP     : int = 60000          # 功勲饱和加封顶
const LOYALTY_RANGE := [0, 100]            # 忠诚值域

# ---------------------------------------------------------------------------
# 规模常量
# ---------------------------------------------------------------------------
const OFFICER_COUNT         : int = 700   # 695 真实 + 5 占位
const REAL_OFFICER_COUNT    : int = 695
const OFFICER_RECORD_SIZE   : int = 59
const ENTITY_POOL_SLOTS     : int = 370
const ENTITY_STRIDE         : int = 47
const CASTLE_COUNT          : int = 200
const PROVINCE_COUNT        : int = 49
const MSGX_TOTAL            : int = 6211
const BATTLE_MAPS           : int = 38
const SFX_COUNT             : int = 39

const BATTLE_UNIT_SLOTS     : int = 15
const BATTLE_UNIT_STRIDE    : int = 24

# ---------------------------------------------------------------------------
# 攻击除数表（0x503770，20B）
# 索引 = section A 低 4 位，按 battle_type 取 +0 或 +8 窗口
# 7 = 最强档，8/10/12/15 = 常规，100 ≈ 零伤害档（本阵/辅助）
# ---------------------------------------------------------------------------
const ATK_DIVISORS : Array[int] = [
	10, 12, 15,  7,  7, 15, 100, 100,
	10, 10, 12,  7,  7, 10,  10,   8,
	100, 100, 12, 12
]

# ---------------------------------------------------------------------------
# 名称表
# ---------------------------------------------------------------------------
const SKILL_NAMES : Array[String] = [
	"口才", "马术", "算术", "剑术", "忍术", "兵法", "洋枪", "筑城", "礼法", "茶道"
]
# ★ 職位 ladder 名表（0x50d850，9 项；二进制自校验 续63 实证，原版真实显示字符串）
#   rank 字段仅 3 bit(0..7)；索引 8=城主 仅用于"城主派生状态"显示映射，不写進实体字段
const RANK_NAMES : Array[String] = [
	"浪人", "步兵头", "队长", "侍大将", "部将", "家老", "宿老", "大名", "城主"
]

# —— M5 職位晋升（0x50bf88 阈值表，6 条 {rank:(勲功阈值, 俸禄)}）——
const RANK_MERIT_THRESHOLDS : Dictionary = {1: 100, 2: 500, 3: 1500, 4: 5000, 5: 10000, 6: 30000}
const RANK_STIPENDS : Dictionary = {1: 1, 2: 10, 3: 30, 4: 50, 5: 100, 6: 200}
const CASTLE_LORD_MIN_RANK : int = 4   # 城主任命门槛：rank 必须 > 4（家老5/宿老6 方可）
const FORCE_NAMES : Array[String] = ["lead", "martial", "domestic", "diplomacy", "charm"]
const FORCE_CN    : Array[String] = ["统率", "武力", "内政", "外交", "魅力"]
const ARCHETYPE_NAMES : Dictionary = {
	0: "木下藤吉郎",
	1: "明智光秀",
	2: "柴田胜家",
	4: "一般武将A",
	5: "一般武将B",
	6: "一般武将C",
	7: "织田信长",
	8: "上杉谦信/本愿寺显如",
}

# ---------------------------------------------------------------------------
# 数据文件路径（相对工程根）
# ---------------------------------------------------------------------------
const DATA_DIR := "res://../data/"   # Godot 工作目录 = 工程根 → res://../data 解析不便，统一用绝对
# 推荐：直接用 GameState 单例持有 DataLoader，UI 层通过 GameState.officer(id) 访问
