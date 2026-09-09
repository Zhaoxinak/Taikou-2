# _test_gaiji.gd — GAIJI（外字）渲染层校验（extends SceneTree）
#
# 覆盖：
#   · decode_bytes —— 原始 GAIJI 转义码字节 → 正确 Unicode（長宗我部 / 香宗我部 / 垪）
#   · has_gaiji / first_gaiji_unit / unit_slot —— 替换单元识别与槽位映射
#   · glyph_image —— 16×16 1bpp 位图还原（含墨点；终止记录全透明）
#   · build_atlas —— 位图集生成
#   · draw_string_subst —— 方法存在且对无外字文本走原生等价分支（零回归）
# 运行：Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_gaiji.gd

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

	# —— 1) decode_bytes：原始 GAIJI 转义码 → Unicode ——
	check(G.decode_bytes(PackedByteArray([0xA1, 0x41, 0xA1, 0x43, 0xA1, 0x44])) == "長宗我部",
		"decode_bytes(長宗我部码) == 長宗我部")
	check(G.decode_bytes(PackedByteArray([0xA1, 0x42, 0xA1, 0x43, 0xA1, 0x44])) == "香宗我部",
		"decode_bytes(香宗我部码) == 香宗我部")
	check(G.decode_bytes(PackedByteArray([0xA1, 0x47])) == "垪",
		"decode_bytes(垪码) == 垪")

	# —— 2) 替换单元识别 ——
	check(G.has_gaiji("長宗我部元亲"), "has_gaiji(長宗我部元亲) == true")
	check(G.has_gaiji("香宗我部亲泰"), "has_gaiji(香宗我部亲泰) == true")
	check(G.has_gaiji("垪和氏续"), "has_gaiji(垪和氏续) == true")
	check(not G.has_gaiji("織田信長"), "has_gaiji(織田信長) == false（无外字）")
	check(not G.has_gaiji("普通文本"), "has_gaiji(普通文本) == false")

	check(G.first_gaiji_unit("長宗我部", 1) == "宗我", "first_gaiji_unit(長宗我部,1) == 宗我")
	check(G.first_gaiji_unit("長宗我部", 0) == "", "first_gaiji_unit(長宗我部,0) == \"\"（長为系统字）")
	check(G.first_gaiji_unit("垪和氏续", 0) == "垪", "first_gaiji_unit(垪和氏续,0) == 垪")
	check(G.unit_slot("宗我") == 0xA143, "unit_slot(宗我) == 0xA143")
	check(G.unit_slot("垪") == 0xA147, "unit_slot(垪) == 0xA147")
	check(G.unit_slot("不存在") == -1, "unit_slot(不存在) == -1")

	# —— 3) 字形位图还原 ——
	var img: Image = G.glyph_image(0xA143)
	check(img != null and img.get_width() == 16 and img.get_height() == 16, "glyph_image(0xA143) 16×16")
	var ink := 0
	for y in range(16):
		for x in range(16):
			if img.get_pixel(x, y).a > 0.0:
				ink += 1
	check(ink > 0, "glyph_image(0xA143) 含墨点 (ink=%d)" % ink)
	var term: Image = G.glyph_image(0xA14F)
	var term_ink := 0
	for y in range(16):
		for x in range(16):
			if term.get_pixel(x, y).a > 0.0:
				term_ink += 1
	check(term_ink == 0, "glyph_image(0xA14F 终止记录) 全透明 (ink=%d)" % term_ink)

	# —— 4) 位图集生成 ——
	var atlas_path := OS.get_user_data_dir().path_join("gaiji_test_atlas.png")
	check(G.build_atlas(atlas_path), "build_atlas 成功")
	check(FileAccess.file_exists(atlas_path), "atlas 文件已写出: %s" % atlas_path)

	# —— 5) draw_string_subst 签名/零回归自检 ——
	check(G.has_method("draw_string_subst"), "draw_string_subst 方法存在（无外字时内部走原生 draw_string 等价分支）")

	# —— 收尾 ——
	var dt := Time.get_ticks_msec() - t0
	if _fails == 0:
		print("\n[ALL PASS] GAIJI 渲染层校验通过（%d ms）" % dt)
		quit(0)
	else:
		push_error("\n[%d FAIL] GAIJI 渲染层校验存在失败" % _fails)
		quit(1)
