extends RefCounted
## EventFlags — S15「劇本/築城イベント旗幟塊」Godot 复刻（原版 25B @ 0x5203c0）
##
## 权威结构：docs/specs/GAME_DATA_SPEC.md §3.9.9（续149/150/151）
##           参考实现：scripts/s15_event_flags_ref.py（63/63 自校验）
##                     scripts/s15_event_bits_named.py（23/23 bit 语义定名）
##
## 布局（共 25B）：
##   +0x00 event_id   1B  イベント進行 ID（= bit 号 1..38；0xff = 無/終了）
##   +0x01 progress   1B  低 5 bit = 進行段階(0..30)，高 3 bit = フェーズ(0..7)
##   +0x02..+0x09 segA 8B bitset = 已発生/已完了（bit 0..63）
##   +0x0a..+0x11 segB 8B bitset = 已失敗/已喪失（bit 0..63）
##   +0x12 done_marker 1B 実行済みマーカー（0 = 未実行；非 0 = 実行済み）
##   +0x13..+0x18 segC 6B byte[] = イベント作業変数（**非 bitset**）
##
## 访问器族（原版 0x49c390..0x49c580）：get_a/get_b/get_c/set_a/set_b/set_c/
##   set_prog/set_hi3/get_a24_26/get_a27_28/set_a24_26/set_a27_28/set_a29。
##
## ⚠️ 不声明 class_name（--script 无头模式不建全局类缓存，统一用 preload 引用）。

const SIZE : int = 25

# 段偏移（相对 0x5203c0）
const OFF_EVENT_ID  : int = 0x00
const OFF_PROGRESS  : int = 0x01
const OFF_SEG_A     : int = 0x02
const OFF_SEG_B     : int = 0x0A
const OFF_DONE_MARK : int = 0x12
const OFF_SEG_C     : int = 0x13

# 14 个已定名历史事件 bit（续150，23/23 自校验；铁证级走 MSGX 文本）
# 键 = bit 号，值 = 事件中文名
const NAMED_BITS : Dictionary = {
	1:  "桶狭间之战 (1560)",
	2:  "将军暗杀/追放 (1573)",
	3:  "石山本愿寺之战/一向一揆",
	4:  "岐阜筑城 (1567)",
	5:  "义昭上洛/将军奉戴 (1568)",
	6:  "二条城筑城/足利义昭 征夷大将军宣下 (1568)",
	7:  "金崎撤退 (1570)",
	8:  "安土城筑城 (1576)",
	9:  "本能寺之变→山崎合战 (1582)",
	10: "光秀讨伐/山崎 (1582)",
	11: "长篠合战 (1575)",
	14: "将军家(足利)断交",
	15: "今滨→长滨 改名 (1573)",
	38: "大阪(石山本愿寺)落城 (1580)",
}

# 两条一次性事件派发链（原版 0x41a400 / 0x41a660）
# 轮询序：if (get_a(bit) || get_b(bit)) continue; 否则调 handler，
# handler 返回非 0 → 整链终止。
const DISPATCH_A : Array[int] = [6, 1, 2, 3, 5, 9, 10]
const DISPATCH_B : Array[int] = [4, 7, 11]

var buf : PackedByteArray = PackedByteArray()


func _init() -> void:
	reset()


## 清零并置 event_id = 0xff（無/終了）
func reset() -> void:
	buf = PackedByteArray()
	buf.resize(SIZE)
	buf[OFF_EVENT_ID] = 0xFF


# ---------------------------------------------------------------- 段 A / B bitset
func _get_bit(seg_off: int, idx: int) -> int:
	if idx < 0 or idx > 63:
		return 0
	return (buf[seg_off + (idx >> 3)] >> (idx & 7)) & 1


func _set_bit(seg_off: int, idx: int, val: int) -> void:
	if idx < 0 or idx > 63:
		return
	var p: int = seg_off + (idx >> 3)
	if val:
		buf[p] |= (1 << (idx & 7))
	else:
		buf[p] &= ~(1 << (idx & 7)) & 0xFF


func get_a(i: int) -> int: return _get_bit(OFF_SEG_A, i)
func get_b(i: int) -> int: return _get_bit(OFF_SEG_B, i)
func set_a(i: int, v: int) -> void: _set_bit(OFF_SEG_A, i, v)
func set_b(i: int, v: int) -> void: _set_bit(OFF_SEG_B, i, v)


# ---------------------------------------------------------------- 段 C（byte 数组，非 bitset）
func get_c(i: int) -> int:
	if i < 0 or i > 5:
		return 0
	return buf[OFF_SEG_C + i]


func set_c(i: int, v: int) -> void:
	if i < 0 or i > 5:
		return
	buf[OFF_SEG_C + i] = v & 0xFF


# ---------------------------------------------------------------- 标量
func get_event_id() -> int: return buf[OFF_EVENT_ID]
func set_event_id(v: int) -> void: buf[OFF_EVENT_ID] = v & 0xFF

func get_progress() -> int: return buf[OFF_PROGRESS] & 0x1F
func set_progress(v: int) -> void: buf[OFF_PROGRESS] = (buf[OFF_PROGRESS] & 0xE0) | (v & 0x1F)

func get_phase() -> int: return (buf[OFF_PROGRESS] >> 5) & 7
func set_phase(v: int) -> void: buf[OFF_PROGRESS] = ((v & 7) << 5) | (buf[OFF_PROGRESS] & 0x1F)

func is_done() -> bool: return buf[OFF_DONE_MARK] != 0
func set_done_marker(v: int) -> void: buf[OFF_DONE_MARK] = v & 0xFF


# ---------------------------------------------------------------- segA 高位 byte[+5] 多用途字节（A24..A31）
# A24..A26 (bit0-2)：3-bit 计数器(0..7)
# A27,A28 (bit3-4)：2-bit 计数器(0..3)
# A29 (bit5)：1-bit 标志
# A30,A31 (bit6-7)：个体事件标志（与 A0..A23 同性质）
func get_a24_26() -> int: return buf[5] & 7
func get_a27_28() -> int: return (buf[5] >> 3) & 3
func set_a24_26(v: int) -> void: buf[5] = (buf[5] & ~7) | (v & 7)
func set_a27_28(v: int) -> void: buf[5] = (buf[5] & ~0x18) | ((v & 3) << 3)
func set_a29() -> void: buf[5] |= 0x20


# ---------------------------------------------------------------- 主人公依存歴史フラグ初期化（原版 0x488030）
# 开局调用一次（原版 0x487f9a）；复刻层用主角武将 id（= 原版 ÷47 魔数解出的实体 idx）。
func init_for_protagonist(protagonist_id: int) -> void:
	if protagonist_id == 8:
		# 武将 8 分支
		for b in range(1, 4):        # B1=B2=B3=1
			set_b(b, 1)
		set_b(7, 1); set_b(9, 1)
		set_a(4, 1); set_a(5, 1)
	else:
		set_b(5, 1); set_b(6, 1); set_b(7, 1)
		set_a(10, 1); set_b(10, 1)
		if protagonist_id != 0:
			set_b(3, 1)


# ---------------------------------------------------------------- 事件解决 / 派发
## 事件是否已終（段A 或 段B 置位）
func is_event_resolved(bit: int) -> bool:
	return get_a(bit) != 0 or get_b(bit) != 0


## 轮询一条派发链：返回首个「未解决」的 bit（其 handler 应被触发），全解决返回 -1。
## 原版语义：handler 返回非 0 则整链终止；复刻层把「是否触发」交还事件解释器决策。
func poll_chain(chain: Array[int]) -> int:
	for bit in chain:
		if is_event_resolved(bit):
			continue
		return bit
	return -1


# ---------------------------------------------------------------- 序列化（SAVE/LOAD 对称，原版 0x47f0a0 / 0x47f110）
func to_bytes() -> PackedByteArray:
	return buf.duplicate()


func from_bytes(b: PackedByteArray) -> void:
	if b.size() == SIZE:
		buf = b.duplicate()
