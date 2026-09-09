extends Node
## GAIJI（外字）渲染层 —— autoload: Gaiji
##
## 太阁立志传2 用 GBK 用户自定义区 0xA140..0xA14F 作为外字码，姓名/国名里出现
## 「長宗我部 / 香宗我部 / 垪」等罕见字。原版以 GAIJI.TR2 的 16×16 1bpp 位图字形绘制。
##
## 本层职责：
##  1. decode_bytes()  —— 把含 GAIJI 转义码的原始字节解码为正确 Unicode（运行期保险；
##                         data/*.json 已在导出期解码，此函数用于 MSGX 文本等原始数据）。
##  2. draw_string_subst() —— UiLabel / UiButton 的集中文本绘制助手：
##        · 字符串**无**外字单元时，完全走原生 draw_string（行为与改造前 100% 一致 → 零回归）；
##        · 仅当含「宗我 / 垪」等外字单元时，才把该单元用 GAIJI.TR2 位图绘制，其余交系统字体。
##  3. glyph_image() / build_atlas() —— 提供 16×16 1bpp 字形资产。
##
## 设计铁律：長/香/部 为标准汉字，系统字体即可渲染，**不入替换集**；仅「宗我」组合切片与
## 罕见独立字（垪/堯/籠/頸/惣/揆/梟/瓊/絆/渚/戌）改用位图，保证忠实且不破坏普通文本。

const _DATA := "res://data/gaiji.json"

var _single: Dictionary = {}       # int(code) -> String(char)
var _glyphs: Dictionary = {}       # int(code) -> String(bitmap hex, 64 chars)
var _subst: Array = []             # [{text:String, slot:int}]
var _subst_first: Dictionary = {}  # first char -> Array[{text,slot}] (按长度降序，最长匹配优先)
var _tex_cache: Dictionary = {}    # int(slot) -> Texture2D（白墨，绘制时 modulate 上色）
var _loaded := false


func _ready() -> void:
	_ensure_loaded()


func _ensure_loaded() -> void:
	if _loaded:
		return
	_loaded = true
	var f := FileAccess.open(_DATA, FileAccess.READ)
	if f == null:
		push_error("Gaiji: 无法打开 %s" % _DATA)
		return
	var data: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if data == null or not (data is Dictionary):
		push_error("Gaiji: 数据解析失败")
		return
	for k in data.get("single", {}):
		_single[int(k, 16)] = data["single"][k]
	for g in data.get("glyphs", []):
		_glyphs[int(g["slot"], 16)] = g.get("bitmap", "")
	for s in data.get("substitutes", []):
		var entry := {"text": s["text"], "slot": int(s["slot"], 16)}
		_subst.append(entry)
		var fc := s["text"][0]
		if not _subst_first.has(fc):
			_subst_first[fc] = []
		_subst_first[fc].append(entry)
	for fc in _subst_first:
		_subst_first[fc].sort_custom(func(a, b): return a["text"].length() > b["text"].length())


# ───────────────────────── 解码（运行期保险） ─────────────────────────

## 把含 GAIJI 转义码（GBK 0xA1 4X 序列）的原始字节解码为正确 Unicode 文本。
## 例：0xA1,0x41 | 0xA1,0x43 | 0xA1,0x44 → "長宗我部"（single 映射已含 0xA143=宗我）。
func decode_bytes(b: PackedByteArray) -> String:
	_ensure_loaded()
	var out := ""
	var i := 0
	while i < b.size():
		var c := b[i]
		if c == 0xA1 and i + 1 < b.size() and b[i + 1] >= 0x40 and b[i + 1] <= 0x4F:
			var code := (c << 8) | b[i + 1]
			var ch := _single.get(code, "")
			if ch != "":
				out += ch
			else:
				out += _gbk_fallback(PackedByteArray([b[i], b[i + 1]]))
			i += 2
		else:
			out += String.chr(c)
			i += 1
	return out


func _gbk_fallback(b: PackedByteArray) -> String:
	# 极简兜底：非外字 GBK 字节无法在此解码时按 latin1 透传（避免崩溃；数据层已在导出期解好）。
	var s := ""
	for x in b:
		s += String.chr(x)
	return s


# ───────────────────────── 渲染助手 ─────────────────────────

## 字符串是否含任何外字替换单元。
func has_gaiji(text: String) -> bool:
	_ensure_loaded()
	for ch in text:
		if _subst_first.has(ch):
			return true
	return false


## 从 text 的第 i 个字符起，匹配最长的外字替换单元（如 "宗我"）。无匹配返回 ""。
func first_gaiji_unit(text: String, i: int) -> String:
	_ensure_loaded()
	if i >= text.length():
		return ""
	var fc := text[i]
	if not _subst_first.has(fc):
		return ""
	for e in _subst_first[fc]:
		if text.substr(i, e["text"].length()) == e["text"]:
			return e["text"]
	return ""


## 外字单元文本 → GAIJI 槽位码（无则 -1）。
func unit_slot(unit: String) -> int:
	_ensure_loaded()
	for e in _subst:
		if e["text"] == unit:
			return e["slot"]
	return -1


## 集中文本绘制：无外字单元时走原生 draw_string（零回归）；有外字单元时按位图替换。
## 参数语义对齐 CanvasItem.draw_string：baseline_pos = 基线坐标，width/align 仅用于对齐布局。
func draw_string_subst(c: CanvasItem, baseline_pos: Vector2, text: String,
		font: Font, font_size: int, color: Color,
		align: HorizontalAlignment, width: float) -> void:
	if text == "" or font == null:
		return
	if not has_gaiji(text):
		c.draw_string(font, baseline_pos, text, align, width, font_size, color)
		return
	var ascent := font.get_ascent(font_size)
	var total := _advance(text, font, font_size)
	var start_x := baseline_pos.x
	if align == HORIZONTAL_ALIGNMENT_CENTER:
		start_x = baseline_pos.x + max(0.0, (width - total) * 0.5)
	elif align == HORIZONTAL_ALIGNMENT_RIGHT:
		start_x = baseline_pos.x + max(0.0, width - total)
	var x := start_x
	var i := 0
	var n := text.length()
	while i < n:
		var unit := first_gaiji_unit(text, i)
		if unit != "":
			var slot := unit_slot(unit)
			var tex := _glyph_texture(slot)
			var gh := ascent
			if tex != null:
				c.draw_texture_rect(tex, Rect2(x, baseline_pos.y - gh, gh, gh), false, color)
			x += gh
			i += unit.length()
		else:
			var ch := text[i]
			c.draw_string(font, Vector2(x, baseline_pos.y), ch, 0, -1, font_size, color)
			x += font.get_string_size(ch, 0, -1, font_size).x
			i += 1


func _advance(text: String, font: Font, font_size: int) -> float:
	var total := 0.0
	var i := 0
	var n := text.length()
	while i < n:
		var unit := first_gaiji_unit(text, i)
		if unit != "":
			total += font.get_ascent(font_size)  # 位图按 ascent 方形绘制
			i += unit.length()
		else:
			total += font.get_string_size(text[i], 0, -1, font_size).x
			i += 1
	return total


# ───────────────────────── 字形资产 ─────────────────────────

## 取某槽位 16×16 1bpp 位图对应的白墨 RGBA Image（绘制时由 modulate 上色）。
func glyph_image(slot: int) -> Image:
	_ensure_loaded()
	var img := Image.create(16, 16, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	var bm := _glyphs.get(slot, "")
	if bm == "" or bm.length() < 64:
		return img
	var bytes := _hex_to_bytes(bm)
	for r in range(16):
		var b0 := bytes[r * 2]
		var b1 := bytes[r * 2 + 1]
		for k in range(8):
			if (b0 >> (7 - k)) & 1:
				img.set_pixel(k, r, Color(1, 1, 1, 1))
			if (b1 >> (7 - k)) & 1:
				img.set_pixel(8 + k, r, Color(1, 1, 1, 1))
	return img


func _glyph_texture(slot: int) -> Texture2D:
	if _tex_cache.has(slot):
		return _tex_cache[slot]
	var tex := ImageTexture.create_from_image(glyph_image(slot))
	_tex_cache[slot] = tex
	return tex


## 把所有外字字形拼成一张位图集 PNG（与 assets/fonts/gaiji_atlas.png 同源）。
func build_atlas(path: String) -> bool:
	_ensure_loaded()
	var slots := _glyphs.keys()
	slots.sort()
	var img := Image.create(slots.size() * 16, 16, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for idx in range(slots.size()):
		var g := glyph_image(slots[idx])
		img.blit_rect(g, Rect2(0, 0, 16, 16), Vector2(idx * 16, 0))
	return img.save_png(path) == OK


func _hex_to_bytes(hex: String) -> PackedByteArray:
	var out := PackedByteArray()
	for i in range(0, hex.length(), 2):
		out.append(hex.substr(i, 2).hex_to_int())
	return out
