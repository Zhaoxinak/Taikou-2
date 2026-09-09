extends RefCounted
## ShopFlows — 店铺「设施内交互流程」Godot 复刻（M7 店铺/商业 子项）
##
## 权威：scripts/shop_facility_flows_ref.py（续243）—— 该 ref 为字节锚点校验脚本，
##       逐地址验证了本文实现的每一条门限/公式；本文件把那些流程落成可单测的纯逻辑。
##
## 覆盖设施（slot = ID_SLOT_TABLE 槽位，见 shop.gd）：
##   slot7  画师   (shop_id 19,20)  袄绘依頼 / 鉴定
##   slot10 医师   (shop_id 26,27,28) 就诊 / 治疗 / 诊金 / 穷人流 / 买药
##   slot4  教会   (shop_id 11,12)  义工 / 大名情报 / 介绍信
##   slot3  南蛮商馆(shop_id 9,10)  陌生人门 / 问候 / 洋枪
##
## 记录字段复用 shop.gd 的 12B 布局：
##   +0x07 favor(好感) / +0x08 word(设施状态) / +0x0a byte(进度计数) / +0x0b byte(事件旗)
##
## 原版 setter/getter（续243 §E，已逐字节校验）：
##   0x49bfc0  word[ecx+8]  = arg     0x49bfd0  byte[ecx+0xa] = arg
##   0x49bfe0  byte[ecx+0xb]= arg     0x49bae0  (word[ecx+0x26] >> 12) & 0xffff
##
## 设计：与 shop.gd 一致，纯逻辑、可无头单测；随机结果由调用方传入随机值
##       （r41 = rand(41)、r100 = rand(100)），保证测试确定性。
##
## ⚠️ 不声明 class_name（--script 无头模式不建全局类缓存，统一用 preload 引用）。

# ───────────────────────── 通用工具 ─────────────────────────

static func _idiv(a: int, b: int) -> int:
	if b == 0:
		return 0
	return floori(float(a) / float(b))


## 0x49bae0：药罐数 = (word[S6+0x26] >> 12) & 0xffff
static func medicine_kits(word26: int) -> int:
	return (int(word26) >> 12) & 0xffff


## 0x49bfc0：word[+0x08] = v（设施状态字；医师=就诊亲密度，画师=制作中标记）
static func set_word08(rec: Dictionary, v: int) -> void:
	rec["facility"] = int(v) & 0xffff


## 0x49bfd0：byte[+0x0a] = v（画师=袄绘剩余天数，医师=免费治疗计数）
static func set_byte0a(rec: Dictionary, v: int) -> void:
	rec["progress"] = int(v) & 0xff


## 0x49bfe0：byte[+0x0b] = v（教会=义工首回标记 bit0/bit1）
static func set_byte0b(rec: Dictionary, v: int) -> void:
	rec["flags"] = int(v) & 0xff


# ───────────────────── A. 画师 slot7（id19,20） ─────────────────────

const PAINTER_FAVOR_GATE  : int = 30   # 0x1e（@0x444508 cmp byte[ecx+7],0x1e）
const PAINTER_FUSUMA_COST : int = 80   # 0x320 贯（@0x44457f push 0x320 → 0x44e350）
const PAINTER_APPRAISE_FEE: int = 5    # msg 1390 鉴定 5 贯
const PAINTER_DAYS_BASE   : int = 20   # 20 + rand(41)
const PAINTER_DAYS_RAND   : int = 41   # @0x44458c push 0x29(41)

## 袄绘依頼好感门：favor >= 30
static func painter_can_request_fusuma(favor: int) -> bool:
	return int(favor) >= PAINTER_FAVOR_GATE


## 完成剩余天数 = 20 + rand(41)（r41 ∈ [0,40]）
static func painter_fusuma_days(r41: int) -> int:
	return PAINTER_DAYS_BASE + int(r41)


## 袄绘依頼：所持金 >= 80 贯才可支付。返回 {ok, cost, days}
static func painter_request_fusuma(gold: int, r41: int) -> Dictionary:
	if int(gold) < PAINTER_FUSUMA_COST:
		return {"ok": false, "cost": 0, "days": 0}
	return {"ok": true, "cost": PAINTER_FUSUMA_COST, "days": painter_fusuma_days(r41)}


# ───────────────── B. 医师 slot10（id26,27,28） ─────────────────

const DOCTOR_VISIT_GAIN    : int = 10   # @0x4450be add edi,0xa
const DOCTOR_FREE_INTIMACY : int = 100  # 0x64：就诊亲密度 ==100 → 免费（@0x4450c7）
const DOCTOR_FAVOR_PENALTY : int = 5    # 不免 → 0x44e540(5) 好感 -5
const DOCTOR_FEE_MIN       : int = 10   # 最低 10（@0x4453xx cmp ax,0xa）
const DOCTOR_CHARITY_CAP   : int = 3    # 免费治疗计数 cap 3（0x4ebca0）
const DOCTOR_CHARITY_FAVOR : int = 10   # 计满 3 → 0x44e560(0xa) 好感 -10
const DOCTOR_KIT_CAP       : int = 10   # 药罐上限 10（cmp ax,0xa）

## 就诊：亲密度(word +0x08) += 10（0x49bfc0 直写，无饱和）
static func doctor_visit_intimacy(cur: int) -> int:
	return int(cur) + DOCTOR_VISIT_GAIN


## 治疗是否免费（@0x4451be）：好感==100 必免；否则 rand(100) < 好感 - 10
static func doctor_is_free_treatment(favor: int, r100: int) -> bool:
	var f : int = int(favor)
	if f == 100:
		return true
	return int(r100) < (f - 10)


## 诊金公式（0x4453a0）：
##   gap = byte[实体+0x20] - byte[实体+0x21]（体力上限 - 当前体力）
##   身分 = (word[实体+0x2c] >> 8) & 7
##   fee = gap × (100 - 亲密度) × 身分 / 100   （÷100 魔数 0x51eb851f sar5）
##   fee = (fee / 10) × 10                     （÷10 魔数 0x66666667 sar2，取 10 的倍数）
##   最低 10
static func doctor_fee(gap: int, intimacy: int, status: int) -> int:
	var v : int = int(gap) * (100 - int(intimacy)) * int(status)
	v = _idiv(v, 100)
	v = _idiv(v, 10) * 10
	if v < DOCTOR_FEE_MIN:
		v = DOCTOR_FEE_MIN
	return v


## 穷人流：免费治疗计数饱和 +1，cap 3（0x4ebca0）
static func doctor_charity_count(cur: int) -> int:
	var v : int = int(cur) + 1
	if v > DOCTOR_CHARITY_CAP:
		v = DOCTOR_CHARITY_CAP
	return v


## 买药可买服数：受药罐上限 10 约束
static func doctor_buyable_doses(kits: int) -> int:
	var k : int = int(kits)
	if k > DOCTOR_KIT_CAP:
		k = DOCTOR_KIT_CAP
	if k < 0:
		k = 0
	return k


# ───────────────── C. 教会 slot4（id11,12） ─────────────────

const CHURCH_VOLUNTEER_GATE   : int = 70  # 0x46：好感>=70 才 +5（@0x44c337）
const CHURCH_VOLUNTEER_BASE   : int = 5   # 好感>=70 → 0x4a3630(5)
const CHURCH_VOLUNTEER_BONUS_A: int = 5   # 0x49f7a0()==0 → +5
const CHURCH_VOLUNTEER_BONUS_B: int = 10  # 0x49f7a0()!=0 → +10
const CHURCH_FAVOR_CAP        : int = 69  # 0x45：义工好感增长钳 69（@0x44c384）
const CHURCH_CHARM_CAP        : int = 100 # 0x64：魅力 sat_add cap100（0x4a3000）
const CHURCH_INTEL_BASE       : int = 5   # 情报费 = 5 - 捐额/20 贯
const CHURCH_INTEL_FREE_DON   : int = 100 # 捐 100 贯 → 免费（cmp ax,0x64）
const CHURCH_INTEL_UNIT       : int = 10  # 支付 = 费 × 10（0x44e350）

## 义工好感增量：好感 >= 70 → +5，否则 0
static func church_volunteer_base(favor: int) -> int:
	return CHURCH_VOLUNTEER_BASE if int(favor) >= CHURCH_VOLUNTEER_GATE else 0


## 义工 +5/+10 分歧（neg/sbb/and5/add5）：0x49f7a0() 返回 0 → 5，否则 10
static func church_volunteer_bonus(decider_zero: bool) -> int:
	return CHURCH_VOLUNTEER_BONUS_A if decider_zero else CHURCH_VOLUNTEER_BONUS_B


## 义工好感增长上限钳 0x45(69)（0x49bfb0）
static func church_clamp_favor(v: int) -> int:
	if int(v) > CHURCH_FAVOR_CAP:
		return CHURCH_FAVOR_CAP
	if int(v) < 0:
		return 0
	return int(v)


## 义工首回标记：+0x0b bit1 未置 → +5 且置 bit1；bit0 未置 → +5 且置 bit0。
## 返回 {gain, flags}
static func church_first_time_flags(flags: int) -> Dictionary:
	var f : int = int(flags) & 0xff
	var gain : int = 0
	if (f & 0x02) == 0:
		gain += 5
		f |= 0x02          # or ebx,2 → 0x49bfe0
	if (f & 0x01) == 0:
		gain += 5
		f |= 0x01
	return {"gain": gain, "flags": f}


## 义工受益：魅力(实体+0x0e) +1，饱和 cap 100（0x4a3000）
static func church_charm_add(charm: int) -> int:
	var v : int = int(charm) + 1
	if v > CHURCH_CHARM_CAP:
		v = CHURCH_CHARM_CAP
	return v


## 大名情报费（贯）= 5 - 捐额/20（÷20 魔数 0x666667 sar3）；捐 100 贯免费
static func church_intel_fee(donation: int) -> int:
	if int(donation) >= CHURCH_INTEL_FREE_DON:
		return 0
	return CHURCH_INTEL_BASE - _idiv(int(donation), 20)


## 情报实际支付额 = 费 × 10（0x44e350）
static func church_intel_cost(fee: int) -> int:
	return int(fee) * CHURCH_INTEL_UNIT


# ─────────────── D. 南蛮商馆 slot3（id9,10） ───────────────

const NANBAN_STRANGER_MSG : int = 738  # 「不和陌生人做生意」(@0x450c97 push 0x2e2)
const NANBAN_GREET_LOW    : int = 693  # 「欢迎」  favor < 50
const NANBAN_GREET_HIGH   : int = 694  # 「多买点」favor >= 50
const NANBAN_GREET_GATE   : int = 50   # 0x32
const NANBAN_GUN_BASE     : int = 15   # 洋枪 10 支 = 15 - 好感/30 贯
const NANBAN_GUN_FAVOR_MAX: int = 100  # 好感 ==100 → 特殊路径 0x4508d0

## 陌生人门：favor == 0 → 拒做买卖（走介绍信流）
static func nanban_is_stranger(favor: int) -> bool:
	return int(favor) == 0


## 问候 msg = 0x2b6 + sbb（cmp favor,0x32）：favor < 50 → 693，否则 694
static func nanban_greeting_msg(favor: int) -> int:
	return NANBAN_GREET_LOW if int(favor) < NANBAN_GREET_GATE else NANBAN_GREET_HIGH


## 洋枪 10 支价（贯）= 15 - 好感/30（÷30 魔数 0x88888889 sar4）
static func nanban_gun_price(favor: int) -> int:
	return NANBAN_GUN_BASE - _idiv(int(favor), 30)


## 好感 == 100 → 原版走特殊路径 0x4508d0（定价逻辑待逆向，此处仅标记分流）
static func nanban_gun_is_special(favor: int) -> bool:
	return int(favor) >= NANBAN_GUN_FAVOR_MAX
