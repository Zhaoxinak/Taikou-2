# Battle.gd — 合战地图实体（数据模型，镜像 Officer.gd）
# 数据源：data/battles.json（由 scripts/export_for_godot.py 生成，38 张）
# 消费方：src/battle/battle_sim.gd（§9 公式逐位对齐 Python ref）

class_name Battle
extends RefCounted

var id                : int = 0
var unit_table        : Array = []   # [side0, side1]，每侧 {raw:[20], nibbles:[40]}
var unit_nibble_hist  : Array = []
var terrain           : Array = []   # 地形网格（HJMAPDAT 19×40）
var terrain_type_hist : Array = []
var deploy            : Array = []   # 部署信息

# 从 JSON Dictionary 填充
func load_from_dict(d: Dictionary) -> void:
	id               = int(d.get("id", 0))
	unit_table       = d.get("unit_table", [])
	unit_nibble_hist = d.get("unit_nibble_hist", [])
	terrain          = d.get("terrain", [])
	terrain_type_hist = d.get("terrain_type_hist", [])
	deploy           = d.get("deploy", [])

# 单元组数量（每组合 20 raw / 40 nibbles）
func group_count() -> int:
	return unit_table.size()

# 第 i 组的有效单位数（nibble != 0 计为有效）
func group_unit_count(i: int) -> int:
	if i < 0 or i >= unit_table.size():
		return 0
	var rec: Variant = unit_table[i]
	if not (rec is Dictionary):
		return 0
	var nibs: Array = rec.get("nibbles", [])
	var n := 0
	for v in nibs:
		if int(v) != 0:
			n += 1
	return n

# 全部单元组的有效单位总数
func total_units() -> int:
	var n := 0
	for i in unit_table.size():
		n += group_unit_count(i)
	return n
