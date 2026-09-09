extends RefCounted
## Shop — 店铺/商业核心逻辑 Godot 复刻（M7 店铺/商业，纯逻辑可无头单测）
##
## 权威：scripts/shop_record_head_ref.py（续247：记录头 30×12B 布局 + 买药÷50 魔数 + slot3/4/10 msg）
##       scripts/shop_npc_record_ref.py（续242：入店分发器 0x44e710 + 关系值 favor setter 三件套 + 槽跳表）
##       scripts/msgx_text_tables.json['S8_dialogue_30x12B']（30 条记录已解析，本复刻导出为 data/shops.json）
##
## 原版记录布局（30×12B @0x517850，运行时区；本复刻用静态导出 data/shops.json）：
##   +0x00 word name_key  人名/对话键 (1000+idx → 姓@0x5077b0/名@0x507888 stride7；兼对话 MSGX 1000..1029)
##   +0x02 word shop_msg  商店对话 MSGX (700..728；#29 闇商人 = 0xffff)
##   +0x04 byte job       职业码 0..11（名表@0x5076f0 stride11）
##   +0x05 byte province  所属国 0..48（与 [0x520603] 匹配过滤）
##   +0x06 byte rank      技艺等级 1..3
##   +0x07 byte favor     店主对主角关系值（饱和 0..100）
##   +0x08 word facility  设施状态
##   +0x0a byte progress  进度计数
##   +0x0b byte flags     事件旗
##
## 范围：本文件复刻可无头单测的纯逻辑核心（记录模型 + 入店分发器 + favor 饱和运算 + 买药÷50 公式）。
##  设施内交互流程（品茶/鉴定/铁炮打工/试合/忍里修业/30日修行/学做生意 + 闇商人事件流 0x460890）
##  属 UI/对话驱动层，留待后续子项（shop_facility_flows_ref 续）。
##
## ⚠️ 不声明 class_name（--script 无头模式不建全局类缓存，统一用 preload 引用）。
## ⚠️ 本文件自含数据加载（FileAccess 读 res://data/shops.json），不依赖 GameData autoload，
##    规避非 autoload 取 GameData 全局名的编译期限制。

const SHOP_COUNT : int = 30

# 12 职业名（shop_record_head_ref B1，stride 11 @0x5076f0）
const JOB_NAMES : Array[String] = [
	"大商人", "茶道大师", "洋枪铸造", "南蛮商人", "传教士",
	"剑客", "公卿", "画匠", "僧侣", "忍者", "名医", "神秘商人"
]

# id→slot 字节表（shop_npc_record_ref A5，30 项；第31字节 0x0b 为哨兵，shop_id≥30 不入店）
# slot==job 类型索引 0..11（slot 0=商家…slot11=神秘商人）；slot 12 = 出店/闇商人专属事件流路径
const ID_SLOT_TABLE : Array = [
	0, 0, 0, 0, 0, 1, 2, 2, 2, 3, 3, 4, 4, 5, 5, 5,
	6, 6, 6, 7, 7, 8, 8, 8, 9, 9, 10, 10, 10, 12
]

# 买药金额魔数：有符号整数 ÷50（0x51eb851f + sar4）— 等价 gold // 50（游戏内 gold≥0）
const MEDICINE_PRICE_UNIT : int = 50   # 每服 5 贯 = 50 内单位
const MEDICINE_MIN_GOLD : int = 50     # 买药门槛 gold >= 0x32（0x445647 cmp si,0x32）

# 关系值饱和边界
const FAVOR_CAP : int = 100
const FAVOR_FLOOR : int = 1

var records : Array = []   # 30 条 Dictionary（data/shops.json）


func _init() -> void:
	load_db()


## 载入 30 条店铺记录（res://data/shops.json，由 msgx_text_tables.json S8 导出）。
func load_db() -> void:
	var f := FileAccess.open("res://data/shops.json", FileAccess.READ)
	if f == null:
		push_error("[Shop] 无法载入 res://data/shops.json")
		return
	var txt := f.get_as_text()
	f.close()
	var parsed = JSON.parse_string(txt)
	if parsed == null or not (parsed is Array):
		push_error("[Shop] shops.json 解析失败")
		return
	records = parsed


# ---------------------------------------------------------------- 记录访问
func get_record(shop_id: int) -> Dictionary:
	if shop_id < 0 or shop_id >= SHOP_COUNT:
		return {}
	if shop_id >= records.size():
		return {}
	return records[shop_id]


## 入店分发器（0x44e710 序言 + 0x44e753 lea / 0x44e75b·0x44e7d4 置 NULL）：
## shop_id ∈ [0,30) → 返回记录；否则空（=原版 [0x52063c]=NULL，离店尾恒置 NULL）。
func enter_shop(shop_id: int) -> Dictionary:
	return get_record(shop_id)


func slot_of(shop_id: int) -> int:
	if shop_id < 0 or shop_id >= SHOP_COUNT:
		return -1
	return int(ID_SLOT_TABLE[shop_id])


## 设施类型名：slot==job 类型索引 0..11 → JOB_NAMES[slot]；slot 12 = 闇商人专属事件流（非普通设施）。
func facility_name_of(shop_id: int) -> String:
	var s := slot_of(shop_id)
	if s == 12:
		return "闇商人(专属事件流)"
	if s < 0 or s >= JOB_NAMES.size():
		return ""
	return JOB_NAMES[s]


func job_name(job_code: int) -> String:
	if job_code < 0 or job_code >= JOB_NAMES.size():
		return ""
	return JOB_NAMES[job_code]


# ---------------------------------------------------------------- 关系值（favor / +0x07）饱和运算
## 饱和加 cap 100（0x4a3630 sat_add(thiscall)）
func favor_add(cur: int, delta: int) -> int:
	var v : int = cur + delta
	if v > FAVOR_CAP:
		v = FAVOR_CAP
	if v < 0:
		v = 0
	return v


## 饱和减 floor 1（0x44e560 消费站：max(1, N-arg) → 0x49bfb0）
func favor_sub(cur: int, delta: int) -> int:
	var v : int = cur - delta
	if v < FAVOR_FLOOR:
		v = FAVOR_FLOOR
	return v


## 直写钳位 0..100（0x49bfb0 byte[ecx+7]=al；0x45/0x64 上限写站）
func favor_set(v: int) -> int:
	if v > FAVOR_CAP:
		v = FAVOR_CAP
	if v < 0:
		v = 0
	return v


# ---------------------------------------------------------------- 买药（0x445679 ÷50 魔数 0x51eb851f）
## 最多可买服数 = 有符号 gold ÷ 50（原版 imul 0x51eb851f; sar edx,4 对负数向负无穷取整）
static func medicine_doses(gold: int) -> int:
	var g : int = int(gold)
	if g >= 0:
		return g / MEDICINE_PRICE_UNIT
	# 负数：等价 floor(g/50)
	return -((-g + MEDICINE_PRICE_UNIT - 1) / MEDICINE_PRICE_UNIT)


## 支付金额 = 服数 × 50（0x4456fd 0x44e350(doses×50)）
static func medicine_cost(doses: int) -> int:
	return doses * MEDICINE_PRICE_UNIT


## 买药门槛：gold >= 50（0x445647 cmp si,0x32）
func can_buy_medicine(gold: int) -> bool:
	return int(gold) >= MEDICINE_MIN_GOLD
