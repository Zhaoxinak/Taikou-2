extends RefCounted
## council.gd — 評定 / 任务分配 纯逻辑核心（复刻 council_ref.py + council_report_ref.py）
##
## 复刻依据（capstone 反汇编 + 二进制自校验，续64/续69）：
##   · 12 主命名表 0x504b28（菜单构建 0x46336c）；13 报告 handler 表 0x504898（分发 0x4603f0）
##   · 报告选取状态机 0x460420（council_report_ref.py，18/18 自校验）
##   · 対象ID → 名称 四段路由 0x49c2b0（council_ref.py）；菜单构建 0x460320；分发特例 0x460550
##
## 设计：与 weather.gd / diplomacy.gd 一致，**自含、不依赖 GameData**；
##   名称解析经 resolver 注入（武将名由 GameData 提供；NPC 名表由 data/npc_names.json 经
##   GameData.get_npc_name 解析，已由 scripts/export_npc_names.py 从原版导出）。
##
## 名表诚实状态：対象ID 段 1000..1999（特殊NPC）/ 3000+（一般NPC）已导出真实名
##   （续148/export_npc_names.py，GBK 解码 + 三层纯净过滤）；2000..2999 为运行时指针
##   （dword[0x506c54]）无静态名表，resolver 返回 "" → target_name 回退 "NPC{id}"。

# ── 常量 ──────────────────────────────────────────
const HANDLER_COUNT : int = 13          # 0x504898 表项数
const FLAG_ASKED    : int = 0x8000      # bit15：已询问过
const ID_MERCHANT   : int = 17          # 0x11，菜单特例「商　人」
const ID_CASTLE     : int = 22          # 0x16，分发特例「築城業者」(0x460550)

# 12 主命（0x504b28），与 GameState.COMMAND_NAMES 一致
const TASK_NAMES : Array[String] = [
	"贩卖军粮", "购买军粮", "军马", "洋枪", "开垦农田", "改建",
	"筑城", "进贡", "威吓", "朝廷工作", "收集情报", "谋略"
]

# 报告 handler idx -> MSGX id（council_ref.py REPORT_MSG）
const REPORT_MSG : Dictionary = {
	1: 0x1202, 2: 0x1203, 3: 0x1204, 4: 0x1205, 5: 0x1206, 6: 0x1207,
	7: 0x1208, 8: 0x1209, 9: 0x120A, 10: 0x120B, 11: 0x120C, 12: 0x120E
}

const STR_MERCHANT : String = "商　人"   # 0x504888
const STR_STOP     : String = "停　止"   # 0x504890


## handler idx → MSGX id（无映射返回 -1）
static func report_msg_id(idx: int) -> int:
	return int(REPORT_MSG.get(idx, -1)) if REPORT_MSG.has(idx) else -1


## 0x460500：统计菜单条目表中 bit15 已置位的条目数
static func count_asked(menu_entries: Array) -> int:
	var c := 0
	for w in menu_entries:
		if int(w) & FLAG_ASKED:
			c += 1
	return c


## 0x460530：rand()%13 反复挑，直到 slots[i] != 0；全 0 则退化返回 0（游戏保证至少 1 可用）
static func rand_avail(slots: Array, rng: Callable) -> int:
	if slots.size() == 0:
		return 0
	# ⚠️ GDScript 无 Python 的 for...else 语法，需显式标志位
	var any_avail := false
	for s in slots:
		if int(s) != 0:
			any_avail = true
			break
	if not any_avail:
		return 0
	while true:
		var i: int = int(rng.call(13)) % 13
		if i >= 0 and i < slots.size() and int(slots[i]) != 0:
			return i
	return 0   # 不可达兜底：GDScript 要求所有路径有返回值


## 0x460420（由 0x4603f0 分发器调用；di = word[0x516610] = 当前選択ID）
## 返回 handler 索引 0..12；调用方随后清 word[0x513fe0+idx*2]=0。
## 入参：
##   di    当前選択ID（菜单类别）
##   count 总报告条目数 word[0x513fcc]
##   asked 已询问数（0x460500）
##   flag6 slots[11]（馬販子 handler 11 可用性，0x45f0xx 写）
##   flag8 slots[12]（米価   handler 12 可用性）
##   slots 13 个报告槽（word[i*2]，非零=可展示）
##   rng   随机源 Callable(n:int)->int（均匀 [0,n)），prob 用 rng(100)、rand_avail 用 rng(13)
static func report_index(di: int, count: int, asked: int, flag6: int, flag8: int, slots: Array, rng: Callable) -> int:
	# prob(p)：0x4ebe40(p) = (rand()%100) < p
	if di == 9:
		if count >= 3:
			if asked == 1:
				return 0
			elif asked == 2:
				return 1
			elif asked == 3:
				return rand_avail(slots, rng)
			else:                       # asked >= 4 -> esi 保持 0
				return 0
		else:                           # count < 3
			if asked == 1:
				return 1 if rng.call(100) < 0x28 else 0   # 0x28 = 40%
			else:
				return rand_avail(slots, rng)
	else:                               # di != 9
		if asked == 1:
			if count > 1:
				return 1 if rng.call(100) < 0x28 else 0
			# count <= 1 -> 落入 generic（不消耗 prob）
		# generic (0x4604ad)
		if asked == 2 and count >= 2:
			if di == 0 or di == 1:
				return 12 if flag8 != 0 else rand_avail(slots, rng)   # 米価 handler 12
			elif di == 2:
				return 11 if flag6 != 0 else rand_avail(slots, rng)   # 馬販子 handler 11
			else:
				return rand_avail(slots, rng)
		else:
			return rand_avail(slots, rng)


# ── 対象ID → 名称 四段路由（0x49c2b0）──
## resolver: Callable(target_id:int)->String（注入；id 0..999 由 GameData 武将名解析，
##   id 1000..1999 / 3000+ 由 GameData.get_npc_name 解析已导出名表，id 2000..2999 返回 ""）。
## resolver 返回 "" 时：NPC 段回退 "NPC{id}"，武将段返回 ""（缺失武将）。
static func target_name(target_id: int, resolver: Callable = Callable()) -> String:
	var i: int = int(target_id) & 0xFFFF
	if i == ID_MERCHANT:
		return STR_MERCHANT
	if i < 1000:
		if resolver.is_valid():
			var r: String = resolver.call(target_id)
			if r != "":
				return r
		return ""
	if i < 2000:
		if resolver.is_valid():
			var r: String = resolver.call(target_id)
			if r != "":
				return r
		return "NPC%d" % i          # 特殊 NPC 名表待导出（续64）
	if i < 3000:
		return "NPC%d" % i          # 运行时指针（dword[0x506c54]），无静态名表
	if resolver.is_valid():
		var r: String = resolver.call(target_id)
		if r != "":
			return r
	return "NPC%d" % i             # 一般 NPC 名表待导出


## 0x460320 菜单项取名：entry_id & 0x7fff；<30 走対象槽，=17 特例，其余空
static func slot_label(entry_id: int, target_words: Array = [], resolver: Callable = Callable()) -> String:
	var e: int = int(entry_id) & 0x7FFF
	if e == ID_MERCHANT:
		return STR_MERCHANT
	if e < 30:
		var tid: int = 0
		if e < target_words.size():
			tid = int(target_words[e])
		return target_name(tid, resolver)
	return ""


## 0x460320：count 个条目 + 末项「停　止」
static func menu_items(entries: Array, target_words: Array = [], resolver: Callable = Callable()) -> Array[String]:
	var labels: Array[String] = []
	for e in entries:
		labels.append(slot_label(int(e), target_words, resolver))
	labels.append(STR_STOP)
	return labels


## 0x4603f0 分发：ID==22 → 築城業者特例；否则走 handler 表
static func dispatch(entry_id: int) -> Dictionary:
	var e: int = int(entry_id) & 0x7FFF
	if e == ID_CASTLE:
		return {"kind": "special_22"}
	return {"kind": "handler"}
