# Item.gd — 物品实体（数据模型，镜像 Officer.gd）
# 数据源：data/items.json（由 scripts/item_table.json 189 件生成，
#         经 scripts/item_pool_spec.json 的 27→8 类目归并）
# 权威布局：docs/specs/GAME_DATA_SPEC.md §对象池（@0x51e1f0，续25 闭合）
#
# 字段：
#   def_cat 定义表 27 类(0..26)  cat 主池 8 类(0..7)  cat_name 类目中文名
#   val 价值（getValue 公式基准，unit=贯）  tier 等级/品质  flag 位标志（bit7 且 cat!=7 → 技能菜单复用池）  unk 未解析字节

class_name Item
extends RefCounted

const ConstsRef = preload("res://src/core/Consts.gd")

const CAT_NAMES : Array[String] = [
	"酒", "书籍", "道具", "财宝", "武器", "南蛮物", "美术品", "茶具"
]

var id       : int = 0
var name     : String = ""
var def_cat  : int = 0       # 定义表 27 类 (0..26)
var cat      : int = 0       # 主池 8 类 (0..7)
var cat_name : String = ""
var val      : int = 0       # 价值（getValue 公式基准，单位：贯）
var tier     : int = 0       # 等级/品质
var flag     : int = 0       # 位标志
var unk      : int = 0       # 未解析字节

# --- 便捷方法 ---
func is_skill_pool() -> bool:
	# bit7 置位且非茶具(7) → 技能菜单复用对象池
	return (flag & 0x80) != 0 and cat != 7

func is_weapon() -> bool:  return cat == 4
func is_book()   -> bool:  return cat == 1
func is_tea()    -> bool:  return cat == 7
func is_art()    -> bool:  return cat == 6

# 从 JSON Dictionary 填充
func load_from_dict(d: Dictionary) -> void:
	id       = int(d.get("id", 0))
	name     = d.get("name", "")
	def_cat  = int(d.get("def_cat", 0))
	cat      = int(d.get("cat", 0))
	cat_name = d.get("cat_name", "")
	if cat_name == "" and cat >= 0 and cat < CAT_NAMES.size():
		cat_name = CAT_NAMES[cat]
	val      = int(d.get("val", 0))
	tier     = int(d.get("tier", 0))
	flag     = int(d.get("flag", 0))
	unk      = int(d.get("unk", 0))
