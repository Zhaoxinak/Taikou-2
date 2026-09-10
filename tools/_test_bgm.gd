extends SceneTree
## BGM（原版 CD 音轨 / 中文版 MP3/ 34 首）无头校验
##
## 覆盖：
##   1) 常量表完整性（34 轨 / 路径存在 / 轨号↔文件名）
##   2) 全部 34 轨可解码为 AudioStreamMP3 且时长 > 0
##   3) Python 时长表（scripts/bgm_tracks.json → Bgm.DUR）与 Godot 解码交叉校验（抽样）
##   4) CdPlay(0x401310) 语义：轨 0 / 越界 ⇒ 停止；同轨重播跳过；切轨生效
##   5) 槽位 → 轨号 = 槽位 + 2（0x498eb8）
##   6) 标题画面接线：进标题即起播轨 1

const Bgm = preload("res://src/audio/Bgm.gd")

var _fails: int = 0


func check(cond: bool, msg: String) -> void:
	if cond:
		print("[ok] ", msg)
	else:
		_fails += 1
		push_error("[FAIL] " + msg)


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)


func _run() -> void:
	var t0 := Time.get_ticks_msec()
	var audio := root.get_node_or_null("AudioManager")

	# —— 1) 常量表 ——
	check(Bgm.COUNT == 34, "BGM 轨数 = 34（原版 0x498f45 push 0x22，got %d）" % Bgm.COUNT)
	check(Bgm.TRACK_MIN == 1 and Bgm.TRACK_MAX == 34, "轨号范围 1..34")
	check(Bgm.PATHS.size() == 34, "PATHS 34 条 (got %d)" % Bgm.PATHS.size())
	check(Bgm.DUR.size() == 34, "DUR 34 条 (got %d)" % Bgm.DUR.size())
	check(Bgm.SLOT_OFFSET == 2, "槽位偏移 = 2（0x498eb8, got %d）" % Bgm.SLOT_OFFSET)
	check(Bgm.file_of(1) == "01.mp3" and Bgm.file_of(34) == "34.mp3", "轨号→文件名 01/34")
	check(Bgm.file_of(0) == "" and Bgm.file_of(35) == "", "非法轨号→空串")

	# 路径真实存在
	var exist := 0
	for p in Bgm.PATHS:
		if FileAccess.file_exists(ProjectSettings.globalize_path(p)):
			exist += 1
	check(exist == 34, "34 个 MP3 文件全部存在 (got %d)" % exist)

	# —— 2) 全部可解码 ——
	var decoded := 0
	var lens: Array = []
	for i in Bgm.COUNT:
		var fp := ProjectSettings.globalize_path(Bgm.PATHS[i])
		var f := FileAccess.open(fp, FileAccess.READ)
		if f == null:
			continue
		var s := AudioStreamMP3.new()
		s.data = f.get_buffer(f.get_length())
		f.close()
		var ln := s.get_length()
		lens.append(ln)
		if ln > 0.0:
			decoded += 1
	check(decoded == 34, "34 轨全部解码成功 (got %d)" % decoded)

	# —— 3) Python ↔ Godot 时长交叉校验（抽样 6 轨，容差 1%）——
	var sample_idx := [0, 1, 9, 20, 25, 33]
	var mism := 0
	for i in sample_idx:
		var gd_len: float = lens[i]
		var py_len: float = float(Bgm.DUR[i])
		if abs(gd_len - py_len) > maxf(0.5, py_len * 0.01):
			mism += 1
			print("   轨 %d: Godot %.2f vs Python %.2f" % [i + 1, gd_len, py_len])
	check(mism == 0, "Python 时长表与 Godot 解码一致（抽样 %d 轨，容差 1%%，偏差 %d）"
		% [sample_idx.size(), mism])

	# —— 4) CdPlay 语义（需 autoload）——
	if audio == null:
		check(false, "AudioManager autoload 缺失")
		_finish(t0)
		return

	audio.stop_bgm()
	check(audio.get_bgm_track() == 0, "stop_bgm 后当前轨 = 0")

	var ok1: bool = audio.play_bgm_track(5)
	check(ok1 and audio.get_bgm_track() == 5, "起播轨 5，当前轨记录 = 5 (got %d)" % audio.get_bgm_track())

	# 同轨重播跳过（原版 0x401322 比对 byte[0x501294]）
	var ok_same: bool = audio.play_bgm_track(5)
	check(not ok_same, "同轨重播被跳过（防重播，返回 false）")
	check(audio.get_bgm_track() == 5, "重播后当前轨仍 = 5")

	# 切轨
	var ok2: bool = audio.play_bgm_track(6)
	check(ok2 and audio.get_bgm_track() == 6, "切轨 5→6 生效")

	# 轨 0 = 停止（原版 bl==0 → CdStopClose）
	var ok0: bool = audio.play_bgm_track(0)
	check(not ok0 and audio.get_bgm_track() == 0, "轨 0 ⇒ 停止（当前轨归 0）")

	# 越界 = 停止（原版 cmp 轨数 < bl）
	audio.play_bgm_track(3)
	var ok_over: bool = audio.play_bgm_track(35)
	check(not ok_over and audio.get_bgm_track() == 0, "越界轨 35 ⇒ 停止")
	var ok_neg: bool = audio.play_bgm_track(-1)
	check(not ok_neg, "负轨号 ⇒ 停止")

	# —— 5) 槽位 → 轨号 ——
	check(Bgm.track_for_slot(0) == 2, "槽位 0 → 轨 2（got %d）" % Bgm.track_for_slot(0))
	check(Bgm.track_for_slot(3) == 5, "槽位 3 → 轨 5（got %d）" % Bgm.track_for_slot(3))
	audio.stop_bgm()
	var ok_slot: bool = audio.play_bgm_slot(1)
	check(ok_slot and audio.get_bgm_track() == 3, "play_bgm_slot(1) → 轨 3 (got %d)" % audio.get_bgm_track())

	# 音量接口
	audio.set_bgm_volume_db(-6.0)
	check(is_equal_approx(audio.get_bgm_volume_db(), -6.0), "BGM 音量可设 (-6 dB)")
	audio.set_bgm_volume_db(0.0)

	# —— 6) 标题画面接线 ——
	var title: Control = (load("res://scenes/main.tscn") as PackedScene).instantiate()
	root.add_child(title)
	await process_frame
	await process_frame
	check(audio.get_bgm_track() == 1, "进标题画面自动起播 BGM 轨 1 (got %d)" % audio.get_bgm_track())

	audio.stop_bgm()
	_finish(t0)


func _finish(t0: int) -> void:
	print("")
	if _fails > 0:
		push_error("[BGM FAIL] %d 项断言失败" % _fails)
		quit(1)
	print("[ok] BGM 校验通过（用时 %.0f ms）" % [float(Time.get_ticks_msec() - t0)])
	quit(0)
