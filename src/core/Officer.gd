# Officer.gd — 武将实体（语义映射运行期 47B）
# 数据源：data/officers.json（由 scripts/export_for_godot.py 生成）
# 权威布局：docs/specs/GAME_DATA_SPEC.md §1.2（续200）

class_name Officer
extends RefCounted

# 显式 preload（不依赖 class_name 全局注册顺序，避免解析期 "Identifier not declared"）
const ConstsRef = preload("res://src/core/Consts.gd")

# --- 身份 ---
var id          : int = 0
var surname     : String = ""     # 姓
var given       : String = ""     # 名
var bushou_id   : int = 0
var is_placeholder : bool = false
var is_selectable  : bool = false  # 主角候选

# --- 五维 ---
var forces : Dictionary = {}      # {lead, martial, domestic, diplomacy, charm}

# --- 技能（10×2bit 已在导出时解包为 0..3 整数）---
var skills : Array[int] = []      # 顺序 = ConstsRef.SKILL_NAMES

# --- 数值状态 ---
var compat          : int = 0     # 相性字（bit 11-14 有效）
var birth_year      : int = 0     # 绝对年（已 +1490）
var father_id       : int = ConstsRef.FATHER_NONE
var home_idx        : int = 0     # 出身地 → 国 0..48
var stamina_max     : int = 0
var stamina         : int = 0
var stamina_drain   : int = 0
var ambition        : int = 50    # 全表恒 50

# --- 关系 / 状态 ---
var province : int = ConstsRef.NONE_PROVINCE   # 国 0..48，255=无
var city     : int = ConstsRef.NONE_CITY       # 城 0..199，255=浪人
var merit    : int = 0
var salary   : int = 0
var loyalty  : int = 0
var lord     : int = ConstsRef.RONIN_LORD      # 0xFFFF=浪人
var rank     : int = 0                      # 0..7（已 &7）
var archetype : int = 0                     # 0..8


# --- 便捷方法 ---
func full_name() -> String:
	return surname + given

func is_ronin() -> bool:
	return lord == ConstsRef.RONIN_LORD

func has_home_castle() -> bool:
	return city != ConstsRef.NONE_CITY

func rank_name() -> String:
	return ConstsRef.RANK_NAMES[rank] if rank < ConstsRef.RANK_NAMES.size() else "?"

func archetype_name() -> String:
	return ConstsRef.ARCHETYPE_NAMES.get(archetype, "?")

func skill_level(k: int) -> int:
	return skills[k] if k >= 0 and k < skills.size() else 0

# 从 JSON Dictionary 填充（导出器产物）
# 用法：var o := Officer.new(); o.load_from_dict(dict)
func load_from_dict(d: Dictionary) -> void:
	id            = d.get("id", 0)
	surname       = d.get("surname", "")
	given         = d.get("given", "")
	bushou_id     = d.get("bushou_id", 0)
	is_placeholder = d.get("is_placeholder", false)
	is_selectable  = d.get("is_selectable", false)
	forces        = d.get("forces", {})
	skills        = d.get("skill_levels", [])
	compat        = d.get("compat", 0)
	birth_year    = d.get("birth_year", 0)
	father_id     = d.get("father_id", ConstsRef.FATHER_NONE)
	home_idx      = d.get("home_idx", 0)
	stamina_max   = d.get("stamina_max", 0)
	stamina       = d.get("stamina", 0)
	stamina_drain = d.get("stamina_drain", 0)
	ambition      = d.get("ambition", 50)
	province      = d.get("province", ConstsRef.NONE_PROVINCE)
	city          = d.get("city", ConstsRef.NONE_CITY)
	merit         = d.get("merit", 0)
	salary        = d.get("salary", 0)
	loyalty       = d.get("loyalty", 0)
	lord          = d.get("lord", ConstsRef.RONIN_LORD)
	rank          = d.get("rank", 0)
	archetype     = d.get("archetype", 0)
