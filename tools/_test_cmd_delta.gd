# _test_cmd_delta.gd — 12 主命 精确 delta 无头校验（extends SceneTree）
#
# 覆盖：城种派生上限辅助 + 开垦/改建/筑城 二进制精确 delta（naisei_ref.work_kaiten/
# kaizen/chikujo 逐字节对齐）+ issue_command 端到端应用。
# 规格对齐 naisei_ref.py（续153，66/66 自校验）与 GAME_DATA_SPEC §3.21。
# 运行：Godot_v4.7.1/Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_cmd_delta.gd

extends SceneTree

var _fails: int = 0

func check(cond: bool, msg: String) -> void:
	if cond:
		print("[ok] " + msg)
	else:
		push_error("[FAIL] " + msg)
		_fails += 1

func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)

func _run() -> void:
	var gs = root.get_node("/root/GameState")
	var gd = root.get_node("/root/GameData")

	# —— 0) 开局 ——
	check(gs.start_new_game(13), "#13 织田信长 开局成功")

	# —— 1) 城种派生辅助（§3.21.5）——
	check(gs._castle_type({"castle_type": 1034}) == 2, "castle_type=1034 → 城種 = 2 (&7)")
	check(gs._castle_type({"castle_type": 7}) == 7, "castle_type=7 → 城種 = 7")
	check(gs._agri_capacity({"f09": 130, "castle_type": 7}) == 520,
		"農商上限(規模130,城種7) = (130*3*4)/3 = 520")
	check(gs._agri_capacity({"f09": 12, "castle_type": 1034}) == 32,
		"農商上限(規模12,城種2) = (12*2*4)/3 = 32")
	check(gs._agri_capacity({"f09": 100, "castle_type": 0}) == 1,
		"農商上限下限保护 = 1（城種0 基档0）")
	check(gs._castle_type_cap_of({"castle_type": 7}) == 250, "改修上限(城種7) = 250")
	check(gs._castle_type_cap_of({"castle_type": 1034}) == 150, "改修上限(城種2) = 150")
	check(gs._castle_type_cap_of({"castle_type": 0}) == 0, "改修上限(城種0) = 0")

	# —— 2) 开垦农田（code6, 0x4aa290）naisei 精确 ——
	# 城種7, 規模130, 农商=7, naisei=80 → delta=(80-30)//10+1=6
	var r_k1: Dictionary = gs._command_deltas(4, {"nousang": 7, "f09": 130, "castle_type": 7}, 80)
	check(int(r_k1.get("nousang", -99)) == 6, "开垦 naisei=80 → 农商 +6 (got %d)" % int(r_k1.get("nousang", -99)))
	# naisei=20 → sat_sub<0 → delta=1
	var r_k2: Dictionary = gs._command_deltas(4, {"nousang": 7, "f09": 130, "castle_type": 7}, 20)
	check(int(r_k2.get("nousang", -99)) == 1, "开垦 naisei=20 → 农商 +1（下限）")
	# 残容量钳制：农商已 99，cap( agri_cap=520) 内，硬上限 100 → +1
	var r_k3: Dictionary = gs._command_deltas(4, {"nousang": 99, "f09": 130, "castle_type": 7}, 99)
	check(int(r_k3.get("nousang", -99)) == 1, "开垦 农商 99 → 硬上限100 钳 +1")
	# agri_capacity 钳制：城種2 規模12 → cap=32，农商=30，naisei=99(delta=8) → min(2,8)=2
	var r_k4: Dictionary = gs._command_deltas(4, {"nousang": 30, "f09": 12, "castle_type": 1034}, 99)
	check(int(r_k4.get("nousang", -99)) == 2, "开垦 残容量钳(30→32) +2 (got %d)" % int(r_k4.get("nousang", -99)))

	# —— 3) 改建（code7, 0x4aa370）naisei + tier2 精确 ——
	# 城種7 cap=250, 守城=240, naisei=70, tier2=1 → 70//10 + 5*2 = 17; min(10,17)=10
	var r_g1: Dictionary = gs._command_deltas(5, {"f0d": 240, "f09": 130, "castle_type": 7}, 70, 1)
	check(int(r_g1.get("f0d", -99)) == 10, "改建 naisei=70 tier2=1 → 守城 +10(钳至250) (got %d)" % int(r_g1.get("f0d", -99)))
	# 空城 → 不受残容量限制 → +17
	var r_g2: Dictionary = gs._command_deltas(5, {"f0d": 0, "f09": 130, "castle_type": 7}, 70, 1)
	check(int(r_g2.get("f0d", -99)) == 17, "改建 空城 naisei=70 tier2=1 → +17 (got %d)" % int(r_g2.get("f0d", -99)))
	# tier2=0 → +5 基底：naisei=70 → 7+5=12
	var r_g3: Dictionary = gs._command_deltas(5, {"f0d": 0, "f09": 130, "castle_type": 7}, 70, 0)
	check(int(r_g3.get("f0d", -99)) == 12, "改建 tier2=0 → naisei//10 + 5 = 12 (got %d)" % int(r_g3.get("f0d", -99)))
	# 硬上限钳：守城=248 → +10 cap250 → +2
	var r_g4: Dictionary = gs._command_deltas(5, {"f0d": 248, "f09": 130, "castle_type": 7}, 99, 3)
	check(int(r_g4.get("f0d", -99)) == 2, "改建 硬上限钳(248→250) +2 (got %d)" % int(r_g4.get("f0d", -99)))

	# —— 4) 筑城（code8, 0x4ab530）固定 +10 ——
	check(int(gs._command_deltas(6, {"f0d": 240}, 0).get("f0d", -99)) == 10, "筑城 +10")
	check(int(gs._command_deltas(6, {"f0d": 248}, 0).get("f0d", -99)) == 2, "筑城 硬上限钳(248→250) +2")

	# —— 5) issue_command 端到端（信长 domestic=92 @ 清洲城66）——
	gs.start_new_game(13)
	var before: Dictionary = gs.get_effective_castle(66)
	var naisei: int = int(gs._effective_forces().get("domestic", 0))
	check(naisei == 92, "実行者内政力 = 92 (got %d)" % naisei)
	var m0: int = gs.month
	var res_k: Dictionary = gs.issue_command(4)   # 开垦
	check(res_k.get("ok", false), "issue_command(4 开垦) 成功")
	# 清洲: 城種2 規模12 → agri_cap=32; 农商13; naisei92 → delta=(92-30)/10+1=7
	check(int(res_k.get("deltas", {}).get("nousang", -99)) == 7, "开垦 delta=7 (got %d)" % int(res_k.get("deltas", {}).get("nousang", -99)))
	var after_k: Dictionary = gs.get_effective_castle(66)
	check(int(after_k.get("nousang", -1)) == int(before.get("nousang", 0)) + 7,
		"清洲农商 13 → 20 (got %d)" % int(after_k.get("nousang", -1)))
	check(gs.month == m0 + 1, "主命推进 1 月")
	# 改建 delta = 14（守城70, 城種2 cap150, naisei92, tier2=0 → 9+5=14）
	var res_g: Dictionary = gs.issue_command(5)
	check(int(res_g.get("deltas", {}).get("f0d", -99)) == 14, "改建 delta=14 (got %d)" % int(res_g.get("deltas", {}).get("f0d", -99)))
	check(int(gs.get_effective_castle(66).get("f0d", -1)) == 70 + 14, "清洲守城 70 → 84")
	# 覆盖层不污染原表
	check(int(gd.get_castle(66).get("nousang", -1)) == 13, "GameData 原表农商仍为 13（未被污染）")

	# —— 6) 占位命令（非 handler 精确，仅验证接口不报错）——
	var res_p: Dictionary = gs.issue_command(0)   # 贩卖军粮
	check(res_p.get("ok", false) and res_p.get("deltas", {}).has("shikin"), "贩卖军粮 占位 delta 接口正常")

	# —— 收尾 ——
	print("")
	if _fails == 0:
		print("[CMD-DELTA PASS] 全部断言通过 ✅")
		quit(0)
	else:
		push_error("[CMD-DELTA FAIL] %d 项断言失败 ❌" % _fails)
		quit(1)
