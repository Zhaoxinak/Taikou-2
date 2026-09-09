# _test_gun_penalty.gd — 洋枪雨天/雪天战力惩罚（0x42d62e）跨模块一致性校验
#
# 背景：原版 0x42d62e —— 降水（wet 旗 dword[0x51352c]）且兵种 kind==2 ⇒ 战力 ×2/3。
# 本复刻里该规则**有两处实现**，此前均未测：
#   ① weather.gd      `gun_strength_penalty(strength, wet_flag, kind)`
#   ② battle_sim.gd   `army_strength`：cat==2 且 `ctx.mode_m2` ⇒ `idiv(atk*2,3)`
#       （cat = BattleUnit.state & 3，即兵种类别；mode_m2 对应 0x51352c wet 旗）
# 本测试闭合两处实现的一致性 + 兵种特异性。
#
# 构造：士气=0/士气损失=0（m=0 ⇒ 士气因子 idiv(v*100,100)=v 恒等）；
#       兵力=100（troop_scale(100)=100）；equip_tier=0。
#       ⇒ army_strength 只剩 v = idiv(base*100, 23)（STRENGTH_DIVISOR=23）。
# 运行：Godot --headless --script res://tools/_test_gun_penalty.gd

extends SceneTree

const BattleSim = preload("res://src/battle/battle_sim.gd")
const Weather = preload("res://src/core/weather.gd")

var _pass := 0
var _fail := 0

func _c(cond: bool, msg: String) -> void:
	if cond:
		_pass += 1
		print("  [ok] ", msg)
	else:
		_fail += 1
		print("  [FAIL] ", msg)


func _mk(cat: int, atk: int) -> BattleSim.BattleUnit:
	var u := BattleSim.BattleUnit.new()
	u.state = cat            # 低2位=兵种类别；高4位=0 ⇒ active() 为真
	u.stat_atk = atk
	u.side_flag = 0          # side 0
	u.equip_tier = 0
	u.morale = 0
	u.morale_loss = 0
	u.troops = 100           # troop_scale(100) = 100
	return u


func _strength(cat: int, atk: int, mode_m2: int) -> int:
	var ctx := BattleSim.BattleCtx.new()
	ctx.units = [_mk(cat, atk)]
	ctx.mode_m2 = mode_m2
	return BattleSim.army_strength(ctx, 0)


func _run() -> void:
	var A := 300
	# ——— ① battle_sim：cat==2（洋枪）惩罚分支 ———
	var wet_gun := _strength(2, A, 1)     # mode_m2=1（降水）
	var dry_gun := _strength(2, A, 0)     # mode_m2=0
	_c(wet_gun == 869, "cat2+mode_m2 ⇒ ×2/3：strength=%d（期望 869 = idiv(idiv(300*2,3)*100,23)）" % wet_gun)
	_c(dry_gun == 1347, "cat2+干燥：strength=%d（期望 1347 = idiv((300+10)*100,23)）" % dry_gun)
	_c(wet_gun < dry_gun, "降水使洋枪战力下降（%d < %d）" % [wet_gun, dry_gun])

	# ——— ② 兵种特异性：非洋枪不受 mode_m2 影响 ———
	_c(_strength(1, A, 0) == _strength(1, A, 1), "cat1（骑兵）不受 mode_m2 影响")
	_c(_strength(0, A, 0) == _strength(0, A, 1), "cat0（步兵）不受 mode_m2 影响")
	_c(_strength(3, A, 0) == _strength(3, A, 1), "cat3 不受 mode_m2 影响")

	# ——— ③ weather.gd 纯函数 ———
	_c(Weather.gun_strength_penalty(A, 1, 2) == 200, "weather: 湿+洋枪 ⇒ 200（= idiv(300*2,3)）")
	_c(Weather.gun_strength_penalty(A, 0, 2) == 300, "weather: 干+洋枪 ⇒ 不变 300")
	_c(Weather.gun_strength_penalty(A, 1, 1) == 300, "weather: 湿+非洋枪 ⇒ 不变 300")
	_c(Weather.gun_strength_penalty(A, 1, 0) == 300, "weather: 湿+kind0 ⇒ 不变 300")

	# ——— ④ 跨模块一致性：battle_sim 的 mode_m2 base == weather 的惩罚结果 ———
	var wbase := Weather.gun_strength_penalty(A, 1, 2)      # = idiv(A*2,3) = 200
	_c(idiv(wbase * 100, 23) == wet_gun,
		"跨模块一致：weather 惩罚后经同一缩放 == battle_sim 降水流（%d == %d）" % [idiv(wbase * 100, 23), wet_gun])

	print("\nRESULT: %d/%d checks passed" % [_pass, _pass + _fail])
	quit(0 if _fail == 0 else 1)


static func idiv(a: int, b: int) -> int:
	return int(a / b) if b != 0 else 0


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)
