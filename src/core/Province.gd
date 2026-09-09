# Province.gd — 国实体（数据模型，镜像 Officer.gd）
# 数据源：data/provinces.json（由 scripts/export_for_godot.py 生成）
# 权威布局：docs/specs/GAME_DATA_SPEC.md §国情表（stride5×49 @ 0x519548）+ 国政治表（stride14×49 @ 0x5179b8）

class_name Province
extends RefCounted

var id   : int = 0
var name : String = ""

# 国政治表原始记录（stride14，含外交等级等），按需由消费者解析；模型层仅透传
var politics : Variant = null

# 从 JSON Dictionary 填充
# 用法：var p := Province.new(); p.load_from_dict(dict)
func load_from_dict(d: Dictionary) -> void:
	id   = int(d.get("id", 0))
	name = d.get("name", "")
	if d.has("politics_raw"):
		politics = d.get("politics_raw")
