# _test_textfx.gd — 高级文本渲染层校验（extends SceneTree）
#
# 覆盖：
#   · draw_string_fx —— 方法存在且签名兼容（向后兼容 draw_string_subst 调用）
#   · has_rich / _parse_rich —— 富文本 [c:#rrggbb]…[/c] 分段解析
#   · _parse_color —— 6/8 位十六进制（含 # / 0x 前缀）解析
#   · _advance_segment —— GAIJI 感知的单段前进宽度（含字间距）
#   · _outline_offsets —— 描边 8 向偏移
# 运行：Godot --headless --path <project> --script res://tools/_test_textfx.gd

extends SceneTree

var _fails: int = 0

func check(cond: bool, msg: String) -> void:
	if cond:
		print("[ok] " + msg)
	else:
		push_error("[FAIL] " + msg)
		_fails += 1

func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)

func _run() -> void:
	var t0 := Time.get_ticks_msec()
	var G: Node = root.get_node("/root/Gaiji")
	check(G != null, "Gaiji autoload 已加载")
	check(G.has_method("draw_string_fx"), "draw_string_fx 方法存在")
	check(G.has_method("draw_string_subst"), "draw_string_subst 方法存在（向后兼容）")

	# —— 1) 富文本标记识别 ——
	check(G.has_rich("普通文本") == false, "has_rich(普通文本) == false")
	check(G.has_rich("击败[c:#ff5555]織田信長[/c]！") == true, "has_rich(含[c:]标记) == true")

	# —— 2) 富文本分段解析 ——
	var segs: Array = G._parse_rich("击败[c:#ff5555]信長[/c]结束", Color(1, 1, 1, 1))
	check(segs.size() == 3, "_parse_rich 拆出 3 段（前/中/后），实际=%d" % segs.size())
	check(segs[0].text == "击败", "段0 文本 == 击败")
	check(segs[0].color == Color(1, 1, 1, 1), "段0 用默认色（白）")
	check(segs[1].text == "信長", "段1 文本 == 信長")
	check(segs[1].color == Color8(255, 85, 85, 255), "段1 颜色 == #ff5555（红）")
	check(segs[2].text == "结束", "段2 文本 == 结束")
	check(segs[2].color == Color(1, 1, 1, 1), "段2 复位为默认色（白）")

	# —— 3) 颜色解析（多种前缀）——
	check(G._parse_color("#00ff00") == Color(0, 1, 0, 1), "_parse_color(#00ff00) == 绿")
	check(G._parse_color("0xff0000") == Color(1, 0, 0, 1), "_parse_color(0xff0000) == 红")
	check(G._parse_color("0000ff") == Color(0, 0, 1, 1), "_parse_color(0000ff) == 蓝（无前缀）")
	check(G._parse_color("#ff880080") == Color8(255, 136, 0, 128), "_parse_color(#rrggbbaa) == 含 alpha")
	var ca: Color = G._parse_color("#ffffffff")
	check(abs(ca.a - 1.0) < 0.01, "_parse_color 8 位 alpha 解析 == 1.0")

	# —— 4) 单段前进宽度（GAIJI 感知 + 字间距）——
	var fnt := load("res://assets/fonts/NotoSansSC-Regular.ttf")
	var real_font: Font = null
	if fnt != null and fnt is FontFile:
		real_font = fnt
	var adv0: float = G._advance_segment("織田信長", real_font, 30, 0.0)
	var adv1: float = G._advance_segment("織田信長", real_font, 30, 4.0)
	check(adv1 > adv0, "_advance_segment 字间距使宽度单调增大 (%f -> %f)" % [adv0, adv1])
	# 含外字单元也应正常计算（長宗我部：長走系统字，宗我走位图）
	var adv_g: float = G._advance_segment("長宗我部", real_font, 30, 0.0)
	check(adv_g > 0.0, "_advance_segment(長宗我部) 含外字仍得正宽度 (%f)" % adv_g)

	# —— 5) 描边偏移 ——
	var offs0: Array = G._outline_offsets(0)
	check(offs0.size() == 0, "_outline_offsets(0) 空")
	var offs2: Array = G._outline_offsets(2)
	check(offs2.size() == 8, "_outline_offsets(2) 返回 8 向")
	check(offs2.has(Vector2(-2, 0)) and offs2.has(Vector2(2, 2)), "_outline_offsets(2) 含十字与对角")

	# —— 6) 零回归快路径检查：无外字/无标记/无 FX 时走原生等价分支 ——
	# （draw_string_fx 内部快路径不可直接观测；这里传 null CanvasItem + null 字体命中早返回，验证不崩溃）
	G.draw_string_fx(null, Vector2.ZERO, "テスト", null, 30, Color.WHITE, 0, 0.0)
	check(true, "draw_string_fx 纯文本调用不崩溃（无 CanvasItem 下静默跳过绘制）")

	# —— 收尾 ——
	var dt := Time.get_ticks_msec() - t0
	if _fails == 0:
		print("\n[ALL PASS] 高级文本渲染层校验通过（%d ms）" % dt)
		quit(0)
	else:
		push_error("\n[%d FAIL] 高级文本渲染层校验存在失败" % _fails)
		quit(1)
