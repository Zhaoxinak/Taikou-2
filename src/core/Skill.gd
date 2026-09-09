# Skill.gd — 技能目录项（数据模型，镜像 Officer.gd）
# 数据源：data/skills.json（names / cap / packing）+ GameData.skill_names
# 说明：技能本身不独立成表，而是每武将 10×2bit（见 Officer.skills）。
#       本类表示「技能目录项」：id（0..9）、名称、封顶等级（cap=3）。
#       实例等级请通过 Officer.skill_level(k) 取。

class_name Skill
extends RefCounted

const ConstsRef = preload("res://src/core/Consts.gd")

var id   : int = 0
var name : String = ""
var cap  : int = ConstsRef.SKILL_CAP   # 3

# 由 GameData 构造：传入 id、名称、封顶
func load_from(id_: int, name_: String, cap_: int = ConstsRef.SKILL_CAP) -> void:
	id   = id_
	name = name_
	cap  = cap_

func load_from_dict(d: Dictionary) -> void:
	id   = int(d.get("id", 0))
	name = d.get("name", "")
	cap  = int(d.get("cap", ConstsRef.SKILL_CAP))

func is_maxed(level: int) -> bool:
	return level >= cap
