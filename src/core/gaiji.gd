extends Node
## GAIJI（外字）渲染层 —— autoload: Gaiji
##
## 太阁立志传2 用 GBK 用户自定义区 0xA140..0xA14F 作为外字码，姓名/国名里出现
## 「長宗我部 / 香宗我部 / 垪」等罕见字。原版以 GAIJI.TR2 的 16×16 1bpp 位图字形绘制。
##
## 本层职责：
##  1. decode_bytes()  —— 把含 GAIJI 转义码的原始字节解码为正确 Unicode（运行期保险；
##                         data/*.json 已在导出期解码，此函数用于 MSGX 文本等原始数据）。
##  2. draw_string_fx() —— UiLabel / UiButton 的集中文本绘制助手（高级版）：
##        · 零回归快路径：无外字 / 无富文本标记 / 无 FX / 无字间距时，完全等价原生 draw_string；
##        · GAIJI 替换单元（宗我/垪…）按位图绘制，其余走系统字体；
##        · 增强能力：描边(8 向) / 投影 / 字间距 / 外字位图线性插值 / 内联多色标记 [c:#rrggbb]…[/c]。
##  3. draw_string_subst() —— 基础版（向后兼容），等价于 draw_string_fx 全默认。
##  4. glyph_image() / build_atlas() —— 提供 16×16 1bpp 字形资产。
##
## 设计铁律：長/香/部 为标准汉字，系统字体即可渲染，**不入替换集**；仅「宗我」组合切片与
## 罕见独立字（垪/堯/籠/頸/惣/揆/梟/瓊/絆/渚/戌）改用位图，保证忠实且不破坏普通文本。

const _DATA := "res://data/gaiji.json"

var _single: Dictionary = {}       # int(code) -> String(char)
var _glyphs: Dictionary = {}       # int(code) -> String(bitmap hex, 64 chars)
var _subst: Array = []             # [{text:String, slot:int}]
var _subst_first: Dictionary = {}  # first char -> Array[{text,slot}] (按长度降序，最长匹配优先)
var _tex_cache: Dictionary = {}    # int(slot*2 + smooth) -> Texture2D（白墨，绘制时 modulate 上色）
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
		_single[k.trim_prefix("0x").hex_to_int()] = data["single"][k]
	for g in data.get("glyphs", []):
		_glyphs[g["slot"].trim_prefix("0x").hex_to_int()] = g.get("bitmap", "")
	for s in data.get("substitutes", []):
		var entry := {"text": s["text"], "slot": s["slot"].trim_prefix("0x").hex_to_int()}
		_subst.append(entry)
		var fc: String = s["text"][0]
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
			var ch: String = _single.get(code, "")
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


# ───────────────────────── 渲染助手（基础） ─────────────────────────

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


# ───────────────────────── 富文本标记 ─────────────────────────

## 文本是否含富文本颜色标记（[c:...]…[/c]），需要走分段解析路径。
func has_rich(t: String) -> bool:
	return t.contains("[/c]") or t.contains("[c:")


## 解析富文本标记，返回 [{text:String, color:Color}] 段列表。
## 支持 [c:#rrggbb] / [c:0xrrggbb] / [c:rrggbb] 开启上色，[/c] 复位到默认色。
## 普通文本（无标记）返回单段 = 默认色。解析失败/空文本安全降级。
func _parse_rich(text: String, default_color: Color) -> Array:
	var out: Array = []
	var cur_color: Color = default_color
	var cur := ""
	var i := 0
	var n := text.length()
	while i < n:
		if text[i] == '[':
			var end := text.find(']', i)
			if end != -1:
				var tag := text.substr(i + 1, end - i - 1)
				if tag == "/c":
					if cur != "":
						out.append({"text": cur, "color": cur_color}); cur = ""
					cur_color = default_color
					i = end + 1
					continue
				elif tag.begins_with("c:") or tag.begins_with("c="):
					if cur != "":
						out.append({"text": cur, "color": cur_color}); cur = ""
					cur_color = _parse_color(tag.substr(2))
					i = end + 1
					continue
		cur += text[i]
		i += 1
	if cur != "":
		out.append({"text": cur, "color": cur_color})
	if out.is_empty():
		out.append({"text": "", "color": default_color})
	return out


## 把 6/8 位十六进制（可选 #/0x 前缀）解析为 Color（8 位含 alpha）。
func _parse_color(s: String) -> Color:
	var t := s.strip_edges().to_lower()
	if t.begins_with("#"):
		t = t.substr(1)
	elif t.begins_with("0x"):
		t = t.substr(2)
	if t.length() == 8:
		return Color8(t.substr(0, 2).hex_to_int(), t.substr(2, 2).hex_to_int(),
			t.substr(4, 2).hex_to_int(), t.substr(6, 2).hex_to_int())
	if t.length() == 6:
		return Color8(t.substr(0, 2).hex_to_int(), t.substr(2, 2).hex_to_int(),
			t.substr(4, 2).hex_to_int(), 255)
	if t.length() == 3:
		return Color8(t.substr(0, 1).repeat(2).hex_to_int(), t.substr(1, 1).repeat(2).hex_to_int(),
			t.substr(2, 1).repeat(2).hex_to_int(), 255)
	return Color(1, 1, 1, 1)


# ───────────────────────── 渲染助手（增强版） ─────────────────────────

## 描边偏移集合：以 outline_size 为半径的 8 向偏移（十字 + 对角）。
func _outline_offsets(s: int) -> Array:
	if s <= 0:
		return []
	return [
		Vector2(-s, 0), Vector2(s, 0), Vector2(0, -s), Vector2(0, s),
		Vector2(-s, -s), Vector2(s, -s), Vector2(-s, s), Vector2(s, s)
	]


## 集中文本绘制（基础版，向后兼容）：等价于 draw_string_fx 全默认（无描边/阴影/富文本）。
func draw_string_subst(c: CanvasItem, baseline_pos: Vector2, text: String,
		font: Font, font_size: int, color: Color,
		align: HorizontalAlignment, width: float) -> void:
	draw_string_fx(c, baseline_pos, text, font, font_size, color, align, width)


## 高级文本绘制：在基础版之上增加
##   · outline_size / outline_color      描边（8 向偏移副本，提升复杂背景可读性）
##   · shadow_offset / shadow_color      投影（整体偏移副本）
##   · letter_spacing                    字间距
##   · gaiji_smooth                      外字位图线性插值（放大更柔和）
##   · 内联富文本 [c:#rrggbb]…[/c]       单串内多色（高亮人名/物名/数值）
## 零开销快路径：无外字、无富文本、无 FX、无字间距时，完全等价于原生 draw_string（零回归）。
func draw_string_fx(c: CanvasItem, pos: Vector2, text: String,
		font: Font, font_size: int, color: Color,
		align: HorizontalAlignment = HORIZONTAL_ALIGNMENT_LEFT, width: float = 0.0,
		outline_size: int = 0, outline_color: Color = Color(0, 0, 0, 1),
		shadow_offset: Vector2 = Vector2.ZERO, shadow_color: Color = Color(0, 0, 0, 0),
		letter_spacing: float = 0.0, gaiji_smooth: bool = false) -> void:
	if text == "" or font == null:
		return
	var fx_on := outline_size > 0 \
		or (shadow_color.a > 0.0 and shadow_offset != Vector2.ZERO) \
		or letter_spacing != 0.0 or gaiji_smooth
	# —— 零回归快路径 ——
	if not has_gaiji(text) and not has_rich(text) and not fx_on:
		c.draw_string(font, pos, text, align, width, font_size, color)
		return
	# —— 分段解析（富文本）——
	var segs: Array = _parse_rich(text, color)
	var total := 0.0
	for s in segs:
		total += _advance_segment(s.text, font, font_size, letter_spacing)
	var start_x := pos.x
	if align == HORIZONTAL_ALIGNMENT_CENTER:
		start_x = pos.x + max(0.0, (width - total) * 0.5)
	elif align == HORIZONTAL_ALIGNMENT_RIGHT:
		start_x = pos.x + max(0.0, width - total)
	var x := start_x
	for s in segs:
		x = _draw_segment_fx(c, x, pos.y, s.text, font, font_size, s.color,
			outline_size, outline_color, shadow_offset, shadow_color, letter_spacing, gaiji_smooth)


## 绘制单个着色分段（含描边/投影层），返回绘制后的 x 光标。
func _draw_segment_fx(c: CanvasItem, x: float, base_y: float, seg: String,
		font: Font, font_size: int, col: Color,
		outline_size: int, outline_color: Color,
		shadow_offset: Vector2, shadow_color: Color,
		letter_spacing: float, smooth: bool) -> float:
	if shadow_color.a > 0.0 and shadow_offset != Vector2.ZERO:
		_draw_segment_raw(c, x + shadow_offset.x, base_y, seg, font, font_size, shadow_color, letter_spacing, smooth)
	if outline_size > 0:
		for d in _outline_offsets(outline_size):
			_draw_segment_raw(c, x + d.x, base_y, seg, font, font_size, outline_color, letter_spacing, smooth)
	return _draw_segment_raw(c, x, base_y, seg, font, font_size, col, letter_spacing, smooth)


## 单色、含外字替换的单段绘制（GAIJI 感知）。返回结束 x。
func _draw_segment_raw(c: CanvasItem, x: float, base_y: float, seg: String,
		font: Font, font_size: int, col: Color, letter_spacing: float, smooth: bool) -> float:
	# 快路径：本段无外字且无字间距 → 整段单次原生绘制。
	# 避免逐字符 draw_string（CJK 大字体下每个字符一次调用，开销巨大，实测会「卡死」）。
	if letter_spacing == 0.0 and not has_gaiji(seg):
		c.draw_string(font, Vector2(x, base_y), seg, 0, -1, font_size, col)
		return x + font.get_string_size(seg, 0, -1, font_size).x
	var ascent := font.get_ascent(font_size)
	var cx := x
	var i := 0
	var n := seg.length()
	while i < n:
		var unit := first_gaiji_unit(seg, i)
		if unit != "":
			var slot := unit_slot(unit)
			var tex := _glyph_texture(slot, smooth)
			var gh := ascent
			if tex != null:
				c.draw_texture_rect(tex, Rect2(cx, base_y - gh, gh, gh), false, col)
			cx += gh + letter_spacing
			i += unit.length()
		else:
			var ch := seg[i]
			c.draw_string(font, Vector2(cx, base_y), ch, 0, -1, font_size, col)
			cx += font.get_string_size(ch, 0, -1, font_size).x + letter_spacing
			i += 1
	return cx


## 单段字形总前进宽度（GAIJI 感知 + 字间距）。
func _advance_segment(seg: String, font: Font, font_size: int, letter_spacing: float) -> float:
	if font == null:
		return 0.0
	# 快路径：无外字且无字间距 → 整段一次量宽
	if letter_spacing == 0.0 and not has_gaiji(seg):
		return font.get_string_size(seg, 0, -1, font_size).x
	var total := 0.0
	var ascent := font.get_ascent(font_size)
	var i := 0
	var n := seg.length()
	while i < n:
		var unit := first_gaiji_unit(seg, i)
		if unit != "":
			total += ascent + letter_spacing
			i += unit.length()
		else:
			total += font.get_string_size(seg[i], 0, -1, font_size).x + letter_spacing
			i += 1
	return total


# ───────────────────────── 字形资产 ─────────────────────────

## 取某槽位 16×16 1bpp 位图对应的白墨 RGBA Image（绘制时由 modulate 上色）。
func glyph_image(slot: int) -> Image:
	_ensure_loaded()
	var img := Image.create(16, 16, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	var bm: String = _glyphs.get(slot, "")
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


## 取槽位对应的白墨纹理；smooth=true 用线性插值（放大更柔和），否则最近邻（像素锐利）。
func _glyph_texture(slot: int, smooth: bool = false) -> Texture2D:
	var key := slot * 2 + (1 if smooth else 0)
	if _tex_cache.has(key):
		return _tex_cache[key]
	var tex := ImageTexture.create_from_image(glyph_image(slot))
	# Texture2D.Filter 枚举底层整数：FILTER_NEAREST=0, FILTER_LINEAR=1（跨版本稳定，不依赖枚举名）
	tex.set_filter(1 if smooth else 0)
	_tex_cache[key] = tex
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
