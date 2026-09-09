extends RefCounted
## DataLoader — 运行时数据层（src/data/）
##
## 载入 data/*.json（由 scripts/export_for_godot.py 生成，已 gitignore）并建**内存索引**，
## 供各玩法系统按 id / 索引查询。不引用任何 Node/UI，可无头批量跑。
##
## 各 JSON 形状（export_for_godot.py 产出）：
##   officers.json  : Array[700]                 每条含 "id"
##   castles.json   : {castles: Array[200]}       每条含 "id"
##   provinces.json : {provinces: Array[49]}      每条含 "id","name"
##   battles.json   : Array[38]                   每条含 "id"
##   text.json      : Dict{id_str: String}        已按 id 索引（MSGX 6211 条）
##   consts.json    : Dict（常量 + 名称表）
##   gaiji.json     : {single: Dict{code: rec}, ...}
##   skills.json    : {names: Array[10], ...}
##   items.json     : Array[189]                  每条含 "id"（物品表，由 scripts/item_table.json 生成）
##   names.json     : {province_names, castle_town_names, role_type_names, extra_place_names}

const DATA_DIR := "res://data/"

# —— 按 id 索引（id -> 记录）——
var officers: Dictionary = {}
var castles: Dictionary = {}
var provinces: Dictionary = {}
var battles: Dictionary = {}
var items: Dictionary = {}
# —— 名称 / 常量（按位置或键）——
var skill_names: Array = []
var rank_names: Array = []
var force_names: Array = []
var province_names: Array = []
var castle_town_names: Array = []
var role_type_names: Array = []
var extra_place_names: Array = []
var gaiji_single: Dictionary = {}
var texts: Dictionary = {}
var consts: Dictionary = {}
var loaded: bool = false

func load_all() -> void:
	var o = _load_json("officers.json")
	if o is Array:
		officers = _index_by_id(o)
	var c = _load_json("castles.json")
	castles = _index_by_id(c.get("castles", []) if c is Dictionary else [])
	var p = _load_json("provinces.json")
	provinces = _index_by_id(p.get("provinces", []) if p is Dictionary else [])
	var b = _load_json("battles.json")
	if b is Array:
		battles = _index_by_id(b)
	var it = _load_json("items.json")
	items = _index_by_id(it if it is Array else [])
	texts = _load_json("text.json")
	consts = _load_json("consts.json")
	var g = _load_json("gaiji.json")
	gaiji_single = g.get("single", {}) if g is Dictionary else {}
	var sk = _load_json("skills.json")
	skill_names = sk.get("names", []) if sk is Dictionary else []
	var nm = _load_json("names.json")
	province_names = nm.get("province_names", []) if nm is Dictionary else []
	castle_town_names = nm.get("castle_town_names", []) if nm is Dictionary else []
	role_type_names = nm.get("role_type_names", []) if nm is Dictionary else []
	extra_place_names = nm.get("extra_place_names", []) if nm is Dictionary else []
	rank_names = consts.get("RANK_NAMES", []) if consts is Dictionary else []
	force_names = consts.get("FORCE_NAMES", []) if consts is Dictionary else []
	loaded = true

## 把 [{id:.., ...}] 转成 {id: rec}
## ⚠️ Godot 的 JSON.parse_string 把所有数字都解析成 float（13 → 13.0），
## 因此必须用 int(rec["id"]) 归一化键，否则 get_officer(13)（int）会查不到 13.0 键。
func _index_by_id(arr: Array) -> Dictionary:
	var d := {}
	for rec in arr:
		if rec is Dictionary and rec.has("id"):
			d[int(rec["id"])] = rec
	return d

func _load_json(fname: String) -> Variant:
	var path := DATA_DIR + fname
	if not FileAccess.file_exists(path):
		push_warning("DataLoader: 缺少 %s（请先运行 scripts/export_for_godot.py）" % path)
		return {}
	var txt := FileAccess.get_file_as_string(path)
	var parsed: Variant = JSON.parse_string(txt)
	if parsed == null:
		push_error("DataLoader: %s 解析失败" % path)
		return {}
	return parsed

# —— 查询 API（全部按 id / 索引，O(1)）——
func get_officer(id: int) -> Dictionary:
	return officers.get(id, {})

func get_castle(id: int) -> Dictionary:
	return castles.get(id, {})

func get_province(id: int) -> Dictionary:
	return provinces.get(id, {})

func get_battle(id: int) -> Dictionary:
	return battles.get(id, {})

func get_item(id: int) -> Dictionary:
	return items.get(id, {})

func get_province_name(id: int) -> String:
	if id >= 0 and id < province_names.size():
		return province_names[id]
	return ""

func get_castle_town_name(idx: int) -> String:
	if idx >= 0 and idx < castle_town_names.size():
		return castle_town_names[idx]
	return ""

func get_role_type_name(idx: int) -> String:
	if idx >= 0 and idx < role_type_names.size():
		return role_type_names[idx]
	return ""

func get_skill_name(idx: int) -> String:
	if idx >= 0 and idx < skill_names.size():
		return skill_names[idx]
	return ""

func get_rank_name(idx: int) -> String:
	if idx >= 0 and idx < rank_names.size():
		return rank_names[idx]
	return ""

func get_force_name(idx: int) -> String:
	if idx >= 0 and idx < force_names.size():
		return force_names[idx]
	return ""

func get_text(id: Variant) -> String:
	return texts.get(str(id), "")

func get_gaiji(code: String) -> Dictionary:
	return gaiji_single.get(code, {})

func get_const(key: String, default_value: Variant = null):
	return consts.get(key, default_value)
