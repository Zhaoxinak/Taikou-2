extends RefCounted
## EventEffects — 事件解释器「效果执行层」（MSGX 事件派发 / 条件门控 / 效果主体）
##
## 权威（按逆向证据层级，诚实标注）：
##   scripts/event_id_dispatch_ref.py  真实运行期 vtable（仅 7 个事件 id：0,1,9,10,13,14,15）
##   scripts/event_handlers_full_ref.py 49 handler → 自断言 id（含 id29 纠正、0x490c0 笔误剔除）
##   scripts/event_predicates_ref.py    49 handler 元数据（kind/semantics/conf）
##   scripts/event_year_ref.py          时间全局(0x5205f0=年-1560) + 无集中年表（事件分散硬编码 cmp）
##
## 复刻边界（诚实）：
##   ✅ 已执行：7 事件 id 的效果主体「叙事显示」——按各自 handler 的 MSGX id 序列经 GameData
##      取文本并产出（id0/1→0x7d；id9→0x1224..0x1227；id10→0x845/0x846；id15→0x44/0x53/0x2b/0x21/0x24/0x2f）。
##   🔴 未接（需原版运行期全局，本复刻未建模，仅记录 outcome 占位）：
##      · id0/1 概率分支(msg 0x8f/0x7f) + FIRE 后的状态写入([ctx+4]/[ctx+6]) —— 依赖 0x49f430 存储值 + RNG。
##      · id13/14 仅 province/climate 门控条件(0x4e82c0)已解码，触发后的「历史事件叙事」未逆 → narrative_pending。
##      · id9 条件 0x4b4b20（调 0x49f430(arg) 返回值==存储值）未建模全局 → 由 GameState 调度层决定能否触发。
##      · 0x4d0ca0 月度 applier（id0/1 的调度谓词）已证伪为 vtable 成员，故 0/1/9/15 的「自动月度触发」未接，
##        仅暴露 force_event 供游戏月度调度器/测试显式驱动。
##
## ⚠️ 不声明 class_name（--script 无头模式不建全局类缓存，统一用 preload 引用）。

const EventSysRef = preload("res://src/core/event_sys.gd")

# GameData autoload 实例（依赖注入；取 MSGX 通用文本）。
# 本脚本非 autoload，编译期无法解析 GameData 全局名，由 GameState._ready 注入。
var data : Object = null

# 真实事件 id → 效果 handler 地址（源自 event_id_dispatch_ref.VTABLE_HANDLERS 的 effect 方法）。
# id10/13/14 条件方法即其「fire 时执行体」，故一并列入。
const EFFECT_HANDLERS : Dictionary = {
	0:  [0x4499f0],                       # id0/1 主效果（0x490c0 近同构兄弟，差异仅尾部 getter，叙事同 0x7d）
	1:  [0x4499f0],
	9:  [0x44ca90],                       # id9 EFFECT（4 段叙事）
	10: [0x4e7e10],                       # id10 CONDITION（fire 经 sub-eval 0x49f610 显示 0x845/0x846）
	13: [0x4e82c0],                       # id13/14 CONDITION（仅 province/climate 门控）
	14: [0x4e82c0],
	15: [0x4b3ac0],                       # id15 EFFECT（七路跳表，公共尾 6 msg）
}

# 各事件「已解码」显示的 MSGX id 序列（取自 DECODED_CONDITIONS / event_predicates semantics）。
# 13/14 无叙事 MSG（仅门控）→ 不列入（narrative_pending=true）。
const EVENT_MSGS : Dictionary = {
	0:  [0x7d],                                       # id0/1：主效果 msg 0x7d（概率分支 0x8f/0x7f 待 global 模型）
	1:  [0x7d],
	9:  [0x1224, 0x1225, 0x1226, 0x1227],            # id9：四段叙事
	10: [0x845, 0x846],                               # id10：sub-eval 0x49f610 显示
	15: [0x44, 0x53, 0x2b, 0x21, 0x24, 0x2f],        # id15：七路跳表公共尾 msgs
}

# 真实运行期 vtable 的 7 个事件 id（event_id_dispatch_ref.VTABLE_HANDLERS 键集）
const REAL_EVENT_IDS : Array = [0, 1, 9, 10, 13, 14, 15]


## 取 MSGX 文本（注入 GameData 后可用）。
func _resolve(mid: int) -> String:
	if data == null:
		return ""
	return str(data.get_text(mid))


## 执行某事件的效果主体：返回结构化结果，供游戏循环写入事件流 / UI 渲染。
##   event_id : 事件 id（须 ∈ REAL_EVENT_IDS）
##   ctx      : EventSys.EventCtx（[ctx+0] id / [ctx+8] arg 等）
##   rt       : 运行期状态对象（预留：未来接 0x49f430 存储值 / RNG 时消费）
## 返回 {id, handlers, msg_ids, msgs, outcome, narrative_pending}
func dispatch_event(event_id: int, ctx: EventSysRef.EventCtx, rt: Object) -> Dictionary:
	var handlers : Array = EFFECT_HANDLERS.get(event_id, [])
	var msg_ids : Array = EVENT_MSGS.get(event_id, [])
	var msgs : Array[String] = []
	for m in msg_ids:
		msgs.append(_resolve(int(m)))
	return {
		"id": event_id,
		"handlers": handlers,
		"msg_ids": msg_ids,
		"msgs": msgs,
		"outcome": _build_outcome(event_id, ctx),
		"narrative_pending": not EVENT_MSGS.has(event_id),
	}


## 效果结果的结构化记录（本复刻仅占位，未写原版全局）。
func _build_outcome(event_id: int, ctx: EventSysRef.EventCtx) -> Dictionary:
	match event_id:
		0, 1:  return {"kind": "gift_or_event", "arg": ctx.arg}
		9:     return {"kind": "local_event", "arg": ctx.arg}
		10:    return {"kind": "province_event", "assoc": ctx.arg}
		13:    return {"kind": "scenario_trigger", "province": ctx.arg}
		14:    return {"kind": "scenario_trigger", "climate": ctx.arg}
		15:    return {"kind": "audience_or_multi", "arg": ctx.arg}
	return {}


## 查询：某事件 id 是否「效果已解码（有叙事 MSG）」
static func has_narrative(event_id: int) -> bool:
	return EVENT_MSGS.has(event_id)
