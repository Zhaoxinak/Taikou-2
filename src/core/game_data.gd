extends Node
## GameData — 全局数据单例（Autoload）
##
## 委托给 src/data/data_loader.gd 做实际载入与内存索引；本文件只暴露全局查询 API。
## 注意：不要声明 `class_name GameData`（会与 autoload 名冲突，报 "Class hides an autoload singleton"），
## 全局名由 project.godot 的 autoload 注册提供。

const DataLoaderRef = preload("res://src/data/data_loader.gd")
const ConstsRef     = preload("res://src/core/Consts.gd")

# —— 数据模型类（typed getters 用，镜像 Officer.gd 范式）——
const CastleRef    = preload("res://src/core/Castle.gd")
const ProvinceRef  = preload("res://src/core/Province.gd")
const SkillRef     = preload("res://src/core/Skill.gd")
const BattleRef    = preload("res://src/core/Battle.gd")
const ItemRef      = preload("res://src/core/Item.gd")

var _loader = null
var loaded: bool = false

func _ready() -> void:
	_loader = DataLoaderRef.new()
	_loader.load_all()
	loaded = _loader.loaded if _loader != null else false
	if _loader != null:
		print("[GameData] 载入完成：武将 %d / 城 %d / 国 %d / 合战 %d / 物品 %d / 文本 %d" % [
			_loader.officers.size(), _loader.castles.size(), _loader.provinces.size(),
			_loader.battles.size(), _loader.items.size(), _loader.texts.size()
		])

# —— 转发查询（保持全局 API 稳定）——
func get_officer(id: int) -> Dictionary:
	return _loader.get_officer(id) if _loader != null else {}

func get_castle(id: int) -> Dictionary:
	return _loader.get_castle(id) if _loader != null else {}

func get_province(id: int) -> Dictionary:
	return _loader.get_province(id) if _loader != null else {}

func get_battle(id: int) -> Dictionary:
	return _loader.get_battle(id) if _loader != null else {}

func get_item(id: int) -> Dictionary:
	return _loader.get_item(id) if _loader != null else {}

func get_item_ids() -> Array:
	return _loader.items.keys() if _loader != null else []

# —— 类型化模型 getter（返回强类型实例，方便玩法/UI 直接调用便捷方法）——
func get_castle_obj(id: int) -> Castle:
	var c := CastleRef.new()
	c.load_from_dict(get_castle(id))
	return c

func get_province_obj(id: int) -> Province:
	var p := ProvinceRef.new()
	p.load_from_dict(get_province(id))
	return p

func get_battle_obj(id: int) -> Battle:
	var b := BattleRef.new()
	b.load_from_dict(get_battle(id))
	return b

func get_skill_obj(id: int) -> Skill:
	var s := SkillRef.new()
	s.load_from(id, get_skill_name(id), ConstsRef.SKILL_CAP)
	return s

# —— 大地图城坐标查询（data/castle_map.json，聚类近似坐标）——
func get_castle_pos(id: int) -> Vector2:
	return _loader.castle_map.get(id, Vector2.ZERO) if _loader != null else Vector2.ZERO

func get_castle_positions() -> Dictionary:
	return _loader.castle_map if _loader != null else {}

func get_map_size() -> Vector2:
	return Vector2(_loader.map_w, _loader.map_h) if _loader != null else Vector2.ZERO

func has_castle_map() -> bool:
	return _loader != null and _loader.castle_map.size() > 0

func get_item_obj(id: int) -> Item:
	var it := ItemRef.new()
	it.load_from_dict(get_item(id))
	return it

func get_province_name(id: int) -> String:
	return _loader.get_province_name(id) if _loader != null else ""

func get_castle_town_name(idx: int) -> String:
	return _loader.get_castle_town_name(idx) if _loader != null else ""

func get_role_type_name(idx: int) -> String:
	return _loader.get_role_type_name(idx) if _loader != null else ""

func get_skill_name(idx: int) -> String:
	return _loader.get_skill_name(idx) if _loader != null else ""

func get_rank_name(idx: int) -> String:
	return _loader.get_rank_name(idx) if _loader != null else ""

func get_force_name(idx: int) -> String:
	return _loader.get_force_name(idx) if _loader != null else ""

func get_text(id: Variant) -> String:
	return _loader.get_text(id) if _loader != null else ""

func get_gaiji(code: String) -> Dictionary:
	return _loader.get_gaiji(code) if _loader != null else {}

func get_const(key: String, default_value: Variant = null):
	return _loader.get_const(key, default_value) if _loader != null else default_value
