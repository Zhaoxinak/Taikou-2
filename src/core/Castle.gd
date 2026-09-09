# Castle.gd — 城实体（数据模型，镜像 Officer.gd）
# 数据源：data/castles.json（由 scripts/export_for_godot.py 生成）
# 权威布局：docs/specs/GAME_DATA_SPEC.md §城表（31B×200 @ 0x51eb88）
#
# 字段语义（导出器已命名）：
#   officer_entity 在城武将单链表头 / castle_ref 城引用 / province 国 / f09 状态
#   f0a 城主 / nousang 农商 / minkok 民力 / seisan 生产 / gunryo 兵力
#   kome 米 / shikin 资金 / castle_type 城种 / unused_ffff 哨兵

class_name Castle
extends RefCounted

const ConstsRef = preload("res://src/core/Consts.gd")

# --- 身份 ---
var id            : int = 0
var name          : String = ""

# --- 结构引用 ---
var officer_entity : int = 0      # 在城武将单链表头（实体索引）
var castle_ref    : int = 0
var province_id   : int = ConstsRef.NONE_PROVINCE   # 国 0..48，255=无
var status        : int = 0       # f09

# --- 数值状态 ---
var lord          : int = ConstsRef.RONIN_LORD      # f0a 城主（武将 id；0xFFFF=无）
var farmer        : int = 0       # nousang 农商
var f0d           : int = 0
var people        : int = 0       # minkok 民力
var produ         : int = 0       # seisan 生产
var troops        : int = 0       # gunryo 兵力
var rice          : int = 0       # kome 米
var gold          : int = 0       # shikin 资金
var f16           : int = 0
var f18           : int = 0
var f1a           : int = 0
var keep_type     : int = 0       # castle_type 城种
var unused        : int = ConstsRef.SENTINEL_FFFF   # unused_ffff

# --- 便捷方法 ---
func has_lord() -> bool:
	return lord != ConstsRef.RONIN_LORD

func is_empty() -> bool:
	return id < 0 or name == ""

# 从 JSON Dictionary 填充（导出器产物）
# 用法：var c := Castle.new(); c.load_from_dict(dict)
func load_from_dict(d: Dictionary) -> void:
	id            = int(d.get("id", 0))
	name          = d.get("name", "")
	officer_entity = int(d.get("officer_entity", 0))
	castle_ref    = int(d.get("castle_ref", 0))
	province_id   = int(d.get("province", ConstsRef.NONE_PROVINCE))
	status        = int(d.get("f09", 0))
	lord          = int(d.get("f0a", ConstsRef.RONIN_LORD))
	farmer        = int(d.get("nousang", 0))
	f0d           = int(d.get("f0d", 0))
	people        = int(d.get("minkok", 0))
	produ         = int(d.get("seisan", 0))
	troops        = int(d.get("gunryo", 0))
	rice          = int(d.get("kome", 0))
	gold          = int(d.get("shikin", 0))
	f16           = int(d.get("f16", 0))
	f18           = int(d.get("f18", 0))
	f1a           = int(d.get("f1a", 0))
	keep_type     = int(d.get("castle_type", 0))
	unused        = int(d.get("unused_ffff", ConstsRef.SENTINEL_FFFF))
