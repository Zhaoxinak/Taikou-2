# _test_npc_names.gd — NPC 名表导出 + GameData 解析 校验
#
# 校验：
#   ① data/npc_names.json 由 scripts/export_npc_names.py 产出，含 special(1000..1339)/generic(3000..3278)，
#      无 Latin/PUA/\ufffd/控制符，关键条目正确（今井/戦/旅店主/坏）。
#   ② GameData.get_npc_name（autoload → DataLoader）端到端解析：名表内 id 返回真名，
#      2000..2999 运行时指针与名表外 id 返回 ""（council.gd 据此回退 "NPC{id}"）。
# 运行：Godot --headless --script res://tools/_test_npc_names.gd

extends SceneTree

var _pass := 0
var _fail := 0

func _c(cond: bool, msg: String) -> void:
	if cond:
		_pass += 1
		print("  [ok] ", msg)
	else:
		_fail += 1
		print("  [FAIL] ", msg)


func _run() -> void:
	# —— ① 数据文件完整性（直接读 JSON）——
	if not FileAccess.file_exists("res://data/npc_names.json"):
		_c(false, "data/npc_names.json 缺失（请先运行 scripts/export_npc_names.py）")
	else:
		var nj: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://data/npc_names.json"))
		_c(nj is Dictionary, "npc_names.json 解析为 Dictionary")
		if nj is Dictionary:
			var sp: Dictionary = nj.get("special", {})
			var ge: Dictionary = nj.get("generic", {})
			_c(sp.size() > 0 and ge.size() > 0, "special/generic 均非空 (sp=%d ge=%d)" % [sp.size(), ge.size()])
			_c(sp.get("1000", "") == "今井", "special[1000]=今井")
			_c(sp.get("1339", "") == "战", "special[1339]=战（末项）")
			_c(ge.get("3000", "") == "旅店主", "generic[3000]=旅店主")
			_c(ge.get("3278", "") == "坏", "generic[3278]=坏（末项）")
			# 纯净度：无 Latin/PUA/ufffd/控制符
			var bad := ""
			for k in sp.keys() + ge.keys():
				var v: String = (sp.get(k, "") if sp.has(k) else ge.get(k, ""))
				for ch in v:
					var o: int = ord(ch)
					if (0x41 <= o and o <= 0x5A) or (0x61 <= o and o <= 0x7A):
						bad = "Latin@%s=%s" % [k, v]
					elif 0xE000 <= o and o <= 0xF8FF:
						bad = "PUA@%s=%s" % [k, v]
					elif o == 0xFFFD:
						bad = "U+FFFD@%s=%s" % [k, v]
					elif o < 0x20 or o == 0x7F:
						bad = "CTRL@%s=%s" % [k, v]
			_c(bad == "", "special/generic 无 Latin/PUA/ufffd/控制符 (%s)" % bad)
			# 边界：名表外 id 不应出现
			_c(not sp.has("1756") and not sp.has("2000"), "special 不含 1756/2000（非名表）")
			_c(not ge.has("3400"), "generic 不含 3400（非名表）")

	# —— ② GameData autoload 端到端解析 ——
	var gd = root.get_node_or_null("/root/GameData")
	if gd != null and gd.has_method("get_npc_name"):
		_c(gd.get_npc_name(1000) == "今井", "GameData.get_npc_name(1000)=今井")
		_c(gd.get_npc_name(1339) == "战", "GameData.get_npc_name(1339)=战")
		_c(gd.get_npc_name(3000) == "旅店主", "GameData.get_npc_name(3000)=旅店主")
		_c(gd.get_npc_name(3278) == "坏", "GameData.get_npc_name(3278)=坏")
		_c(gd.get_npc_name(2000) == "", "GameData.get_npc_name(2000)=''（运行时指针，无静态名）")
		_c(gd.get_npc_name(1756) == "", "GameData.get_npc_name(1756)=''（名表外）")
		_c(gd.get_npc_name(3400) == "", "GameData.get_npc_name(3400)=''（名表外）")
	else:
		print("  [warn] GameData autoload 未载入，跳过 autoload 路径断言（数据文件断言已覆盖）")

	print("\nRESULT: %d/%d checks passed" % [_pass, _pass + _fail])
	quit(0 if _fail == 0 else 1)


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)
