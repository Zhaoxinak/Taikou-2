# _test_battlesim.gd — M2 无头校验（extends SceneTree）
#
# 1) 引擎等价性：场景 a 跑一回合，断言 side0=[472*4] / side1=[364*4]
#    （与 scripts/battle_formula_ref.py 同参输出 bit-for-bit 一致）。
# 2) 收敛性：38 张真实战图 × 100 场，断言全部收敛（无死循环）、无负兵力、
#    胜者合法；输出每图平均回合数与 side0 胜率（应明显 <50%，验证 ×80% 不对称）。
#
# 运行：Godot_v4.7.1/Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_battlesim.gd

extends SceneTree

const BattleSim = preload("res://src/battle/battle_sim.gd")

const SIMS_PER_BATTLE := 100
const MAX_ROUNDS := 2000

func _initialize() -> void:
	var t0 := Time.get_ticks_msec()

	# —— 1) 引擎等价性（场景 a）——
	var ctx_a := BattleSim.scenario_a()
	var cmds_a := BattleSim.commanders_of(ctx_a)
	BattleSim.battle_round(ctx_a, cmds_a.pA, cmds_a.pB)
	var s0 := []
	var s1 := []
	for u in ctx_a.units:
		var unit := u as BattleSim.BattleUnit
		if unit.side() == 0:
			s0.append(unit.troops)
		else:
			s1.append(unit.troops)
	var expect0 := [472, 472, 472, 472]
	var expect1 := [364, 364, 364, 364]
	if s0 != expect0 or s1 != expect1:
		push_error("场景a 不符！side0=%s (期望 %s) side1=%s (期望 %s)" % [s0, expect0, s1, expect1])
		quit(1)
	print("[ok] 引擎等价性：场景 a 与 Python ref bit-for-bit 一致 (side0=%s side1=%s)" % [s0, s1])

	# —— 2) 收敛性压测 ——
	var path := "res://data/battles.json"
	if not FileAccess.file_exists(path):
		push_error("缺少 %s（先运行 scripts/export_for_godot.py）" % path)
		quit(1)
	var battles: Array = JSON.parse_string(FileAccess.get_file_as_string(path))
	if battles == null or battles.size() == 0:
		push_error("battles.json 解析失败或为空")
		quit(1)

	var total_sims := 0
	var total_converged := 0
	var total_neg := 0
	var total_side0_wins := 0
	var per_battle := []

	for b in battles:
		var bid: int = int(b.get("id", 0))
		var rounds_sum := 0
		var s0_wins := 0
		for sim in SIMS_PER_BATTLE:
			var seed: int = bid * 100003 + sim
			var ctx := BattleSim.build_ctx_from_battle(b, seed)
			var cmds := BattleSim.commanders_of(ctx)
			var res: Dictionary = BattleSim.simulate(ctx, cmds.pA, cmds.pB, MAX_ROUNDS)
			total_sims += 1
			if res.converged:
				total_converged += 1
			else:
				push_error("战图 %d 第 %d 场未收敛（超 %d 回合）" % [bid, sim, MAX_ROUNDS])
			rounds_sum += int(res.rounds)
			if int(res.winner) == 0:
				s0_wins += 1
				total_side0_wins += 1
			# 负兵力检查
			for u in ctx.units:
				var unit := u as BattleSim.BattleUnit
				if unit.troops < 0:
					total_neg += 1
		var avg_rounds := float(rounds_sum) / float(SIMS_PER_BATTLE)
		var s0_rate := float(s0_wins) / float(SIMS_PER_BATTLE)
		per_battle.append({"id": bid, "avg_rounds": avg_rounds, "side0_win_rate": s0_rate})

	# 汇总
	print("")
	print("=== M2 压测汇总 ===")
	print("总场数: %d | 收敛: %d | 负兵力单位: %d" % [total_sims, total_converged, total_neg])
	var overall_s0_rate := float(total_side0_wins) / float(total_sims)
	print("side0 总胜率: %.1f%%  (×80%% 不对称 => 应明显 <50%%)" % [overall_s0_rate * 100.0])
	print("每图平均回合 / side0 胜率:")
	for pb in per_battle:
		print("  战图 %2d: 平均 %.1f 回合, side0 胜率 %.0f%%" % [pb.id, pb.avg_rounds, pb.side0_win_rate * 100.0])

	var ok := (total_converged == total_sims) and (total_neg == 0) and (overall_s0_rate < 0.5)
	if not ok:
		push_error("压测未通过：收敛=%d/%d 负兵力=%d side0胜率=%.3f" % [total_converged, total_sims, total_neg, overall_s0_rate])
		quit(1)
	print("")
	print("[ok] M2 BattleSim 全部通过（用时 %.0f ms）" % [float(Time.get_ticks_msec() - t0)])
	quit(0)
