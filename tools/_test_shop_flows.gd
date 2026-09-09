# _test_shop_flows.gd — 店铺设施内交互流程校验（续243）
#
# 依据：scripts/shop_facility_flows_ref.py（续243）—— 该 ref 为字节锚点校验脚本，
#       实跑 41/41 PASS，逐地址验证了本文每条门限/公式，本测试据此断言。
#
# 覆盖：
#   A 画师 slot7：袄绘依頼好感门 30、80 贯支付、天数 = 20+rand(41)、鉴定 5 贯
#   B 医师 slot10：就诊亲密度 +10、免费治疗判定、诊金公式、穷人流 cap3、药罐上限 10
#   C 教会 slot4：义工门 70 / +5·+10 分歧 / 好感钳 69 / 首回 bit 标记 / 魅力 cap100 /
#                 情报费 = 5 - 捐额/20、捐 100 免费、×10 支付
#   D 南蛮 slot3：陌生人门 favor==0、问候 693/694（门 50）、洋枪价 = 15 - 好感/30
#   E 通用 setter/getter：0x49bae0 药罐 = word>>12

extends SceneTree

const ShopFlows = preload("res://src/core/shop_flows.gd")

var _pass := 0
var _fail := 0


func check(cond: bool, msg: String) -> void:
	if cond:
		_pass += 1
		print("[ok] " + msg)
	else:
		_fail += 1
		print("[FAIL] " + msg)


func _run() -> void:
	# ── E. 通用 getter（先测，其余依赖）──
	check(ShopFlows.medicine_kits(0x1234) == 1,
		"0x49bae0 药罐 = word>>12：0x1234 → 1（实得 %d）" % ShopFlows.medicine_kits(0x1234))
	check(ShopFlows.medicine_kits(0xA000) == 10,
		"药罐 0xA000 → 10（实得 %d）" % ShopFlows.medicine_kits(0xA000))

	# ── A. 画师 slot7 ──
	check(ShopFlows.painter_can_request_fusuma(30), "袄绘依頼门 favor>=30：30 → true")
	check(not ShopFlows.painter_can_request_fusuma(29), "袄绘依頼门：29 → false")
	check(ShopFlows.painter_fusuma_days(0) == 20, "天数 = 20 + rand(41)：r=0 → 20")
	check(ShopFlows.painter_fusuma_days(40) == 60, "天数：r=40 → 60（实得 %d）" % ShopFlows.painter_fusuma_days(40))
	var pr := ShopFlows.painter_request_fusuma(80, 0)
	check(bool(pr["ok"]) and int(pr["cost"]) == 80 and int(pr["days"]) == 20,
		"袄绘依頼 gold=80 → ok/80贯/20天（实得 %s）" % str(pr))
	check(not bool(ShopFlows.painter_request_fusuma(79, 0)["ok"]), "gold=79 不足 → 不可依頼")
	check(ShopFlows.PAINTER_APPRAISE_FEE == 5, "鉴定费 5 贯")

	# ── B. 医师 slot10 ──
	check(ShopFlows.doctor_visit_intimacy(0) == 10, "就诊亲密度 0 → 10")
	check(ShopFlows.doctor_visit_intimacy(95) == 105, "就诊亲密度 95 → 105（无饱和）")
	check(ShopFlows.doctor_is_free_treatment(100, 99), "好感 100 → 必免治疗")
	check(ShopFlows.doctor_is_free_treatment(50, 39), "好感 50：rand=39 < 40 → 免费")
	check(not ShopFlows.doctor_is_free_treatment(50, 40), "好感 50：rand=40 不 < 40 → 不免费")
	check(ShopFlows.doctor_fee(20, 0, 3) == 60,
		"诊金 gap20/亲密0/身分3 = 20*100*3/100=60（实得 %d）" % ShopFlows.doctor_fee(20, 0, 3))
	check(ShopFlows.doctor_fee(1, 90, 1) == 10,
		"诊金极低 → 保底 10（实得 %d）" % ShopFlows.doctor_fee(1, 90, 1))
	check(ShopFlows.doctor_fee(30, 50, 2) == 30,
		"诊金 gap30/亲密50/身分2 = 30*50*2/100=30（实得 %d）" % ShopFlows.doctor_fee(30, 50, 2))
	check(ShopFlows.doctor_charity_count(0) == 1, "穷人流计数 0 → 1")
	check(ShopFlows.doctor_charity_count(3) == 3, "穷人流计数 cap 3（实得 %d）" % ShopFlows.doctor_charity_count(3))
	check(ShopFlows.doctor_buyable_doses(15) == 10, "药罐 15 → 上限 10（实得 %d）" % ShopFlows.doctor_buyable_doses(15))
	check(ShopFlows.doctor_buyable_doses(4) == 4, "药罐 4 → 4")

	# ── C. 教会 slot4 ──
	check(ShopFlows.church_volunteer_base(70) == 5, "义工好感>=70 → +5")
	check(ShopFlows.church_volunteer_base(69) == 0, "义工好感 69 → +0")
	check(ShopFlows.church_volunteer_bonus(true) == 5, "分歧 0x49f7a0()==0 → +5")
	check(ShopFlows.church_volunteer_bonus(false) == 10, "分歧 !=0 → +10")
	check(ShopFlows.church_clamp_favor(80) == 69, "义工好感钳 69（实得 %d）" % ShopFlows.church_clamp_favor(80))
	check(ShopFlows.church_clamp_favor(50) == 50, "未超上限保持 50")
	var ff := ShopFlows.church_first_time_flags(0)
	check(int(ff["gain"]) == 10 and int(ff["flags"]) == 3,
		"首回双标 → +10, flags=0x03（实得 %s）" % str(ff))
	var ff2 := ShopFlows.church_first_time_flags(0x03)
	check(int(ff2["gain"]) == 0 and int(ff2["flags"]) == 3, "已标记 → +0, flags 不变")
	var ff3 := ShopFlows.church_first_time_flags(0x02)
	check(int(ff3["gain"]) == 5 and int(ff3["flags"]) == 3, "仅 bit0 未置 → +5")
	check(ShopFlows.church_charm_add(99) == 100, "魅力 99 → 100（实得 %d）" % ShopFlows.church_charm_add(99))
	check(ShopFlows.church_charm_add(100) == 100, "魅力已满 100 保持")
	check(ShopFlows.church_intel_fee(0) == 5, "情报费 捐0 → 5（实得 %d）" % ShopFlows.church_intel_fee(0))
	check(ShopFlows.church_intel_fee(40) == 3, "情报费 捐40 → 5-2=3（实得 %d）" % ShopFlows.church_intel_fee(40))
	check(ShopFlows.church_intel_fee(100) == 0, "捐 100 贯 → 免费")
	check(ShopFlows.church_intel_cost(3) == 30, "支付 = 费×10 = 30")

	# ── D. 南蛮商馆 slot3 ──
	check(ShopFlows.nanban_is_stranger(0), "favor 0 → 陌生人（拒做买卖）")
	check(not ShopFlows.nanban_is_stranger(1), "favor 1 → 非陌生人")
	check(ShopFlows.nanban_greeting_msg(49) == 693, "favor<50 → msg 693「欢迎」")
	check(ShopFlows.nanban_greeting_msg(50) == 694, "favor>=50 → msg 694「多买点」")
	check(ShopFlows.nanban_gun_price(0) == 15, "洋枪 好感0 → 15 贯")
	check(ShopFlows.nanban_gun_price(30) == 14, "洋枪 好感30 → 14 贯（实得 %d）" % ShopFlows.nanban_gun_price(30))
	check(ShopFlows.nanban_gun_price(60) == 13, "洋枪 好感60 → 13 贯（实得 %d）" % ShopFlows.nanban_gun_price(60))
	check(ShopFlows.nanban_gun_is_special(100), "好感 100 → 特殊路径 0x4508d0")
	check(not ShopFlows.nanban_gun_is_special(99), "好感 99 → 常规路径")

	# 注意：headless 下 process_frame 可能永不触发，禁止 await，直接 quit 退出
	if _fail == 0:
		print("ALL PASS (%d checks)" % _pass)
	else:
		print("FAILURES: %d / %d" % [_fail, _pass])
	quit(1 if _fail > 0 else 0)
