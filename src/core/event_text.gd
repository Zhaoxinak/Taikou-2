extends RefCounted
## EventText — S15 历史事件 MSGX 文本渲染（承接 event_flags 结构层）
##
## 权威：scripts/s15_event_bits_named.py（14 bit 语义定名 + MSGX 锚点）
##       msgx_all_texts.json（6211 条；GameData.get_text 按全局 id 查）
##       event_text_xor_ref.py（HEXMES 第 5 容器；战斗/事件文本轨道闭合，续156）
##
## 职责：给定一个已发生的历史事件 bit，返回其叙事 MSGX 文本序列，并把模板 `%s`
##       填充为「主角名」（玩家向事件文本：bits 2/5/7 的 %s 均指主角，已由 MSGX 文本铁证）。
##
## ⚠️ 仅 bit 2/5/6/7/8/9/10/11/14/15 有 MSGX 显示文本锚点（s15_event_bits_named BITS）。
##   bit 1/3/4/38 为 const/ref 锚点（駿河/下间赖照/岐阜/大阪落城），其显示文本未在
##   MESSAGE1~4 索引内（bit3 文本在 HEXMES 第 5 容器，续156；bit1/4/38 属地图/筑城事件
##   演出），本层暂不渲染，留待事件解释器接入 HEXMES 时补全。
##
## ⚠️ 不声明 class_name（--script 无头模式不建全局类缓存，统一用 preload 引用）。

const EventFlagsRef = preload("res://src/core/event_flags.gd")

# GameData autoload 实例（依赖注入）。本脚本非 autoload，编译期无法解析 GameData 全局名，
# 且本工程 Godot 构建下 Engine.get_singleton("GameData") 返回 null（autoload 仅挂树 /root/GameData），
# 故由 GameState._ready 注入，测试也可手动 et._data = root.get_node("/root/GameData")。
var _data : Object = null

# 各命名事件 bit → MSGX 显示文本 id 序列（取自 s15_event_bits_named.py BITS 锚点）。
# 一事件多段叙事按原版 handler 文本顺序（宣布/结果）。
# 值用 16 进制字面（GDScript 中即十进制 int，GameData.get_text 按 str(id) 查全局 id）。
const EVENT_DISPLAY : Dictionary = {
	2:  [0x195c, 0x1962],   # 将军暗杀/追放(1573)：0x195c 惊愕 / 0x1962「…被%s掌握」
	5:  [0x19f2, 0x19f0],   # 义昭上洛/将军奉戴(1568)：0x19f2 宣布 / 0x19f0「%s大人，信长主公…」
	6:  [0x19f7, 0x1a12],   # 二条城筑城/将军宣下(1568)：0x19f7 / 0x1a12
	7:  [0x1a42, 0x1a46],   # 金崎撤退(1570)：0x1a42「啊，%s大人！」 / 0x1a46「哦，%s，回来了！」
	8:  [0x1a83, 0x1a86],   # 安土城筑城(1576)：0x1a83 / 0x1a86
	9:  [0x1ad1, 0x1ad3],   # 本能寺之变→山崎(1582)：0x1ad1 / 0x1ad3
	10: [0x1b28, 0x1a9a],   # 光秀讨伐/山崎(1582)：0x1b28 / 0x1a9a
	11: [0x1b40, 0x1b41],   # 长篠合战(1575)：0x1b40 / 0x1b41
	14: [0x1b2f, 0x1b4e],   # 将军家(足利)断交：0x1b2f / 0x1b4e
	15: [0x1b71],           # 今滨→长滨 改名(1573)：0x1b71
}

# 含 %s 且 %s = 主角名的事件 bit 集合（玩家向文本，MSGX 铁证）
const PROTAGONIST_ARGS : Dictionary = {
	2:  true,   # 0x1962「…被%s掌握」
	5:  true,   # 0x19f0「%s大人，…」
	7:  true,   # 0x1a42 / 0x1a46「%s大人 / %s，回来了」
}


## 渲染单个历史事件：返回填充后的叙事文本序列（按 EVENT_DISPLAY 顺序）。
## protagonist_name 用于填充 %s（玩家向事件）。
## 无 MSGX 锚点的 bit（1/3/4/38）返回空数组。
func render_event(bit: int, protagonist_name: String) -> Array[String]:
	if not EVENT_DISPLAY.has(bit):
		return []
	var out: Array[String] = []
	for mid in EVENT_DISPLAY[bit]:
		var t: String = _resolve_text(mid)
		if PROTAGONIST_ARGS.has(bit):
			t = t.replace("%s", protagonist_name)
		out.append(t)
	return out


## 渲染某 EventFlags 实例中所有「已解决」的命名事件文本（按 NAMED_BITS 序）。
## 用于「本局已触发的历史事件回顾」面板。
func render_resolved(event_flags: RefCounted, protagonist_name: String) -> Array[String]:
	var out: Array[String] = []
	var keys: Array = EventFlagsRef.NAMED_BITS.keys()
	keys.sort()
	for bit in keys:
		if event_flags.is_event_resolved(int(bit)):
			var lines: Array[String] = render_event(int(bit), protagonist_name)
			for ln in lines:
				out.append(ln)
	return out


## 取事件中文名（委託 event_flags 的 NAMED_BITS）。
func event_name(bit: int) -> String:
	return EventFlagsRef.NAMED_BITS.get(bit, "")


## 按全局 MSGX id 取显示文本。优先用注入的 GameData 实例（_data），
## 否则回退 Engine.get_singleton（本构建返回 null，仅作兜底）。
func _resolve_text(mid: int) -> String:
	var src : Object = _data if _data != null else Engine.get_singleton("GameData")
	if src == null:
		return ""
	return src.get_text(mid)
