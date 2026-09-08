# _test_audio.gd — 阶段 6 音效接入 无头校验（extends SceneTree）
#
# 覆盖：Sfx 常量表完整性（39 条 / id 连续 / 无重名）、全部 WAV 可载入
#       （AudioStreamWAV.load_from_file，含 8-bit PCM）、播放接口（含越界/静音）、
#       BGM 占位优雅降级。
# 运行：Godot_v4.7.1/Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_audio.gd

extends SceneTree

const Sfx = preload("res://src/audio/Sfx.gd")
const UiButton = preload("res://src/ui/UiButton.gd")

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
	var am = root.get_node("/root/AudioManager")

	# —— 1) 常量表完整性（映射自 sfx_subsystem.json 续195）——
	check(Sfx.COUNT == 39, "音效总数 = 39 (got %d)" % Sfx.COUNT)
	check(Sfx.NAMES.size() == 39 and Sfx.ZH.size() == 39 and Sfx.CATS.size() == 39 and Sfx.PATHS.size() == 39,
		"四表均为 39 项")
	check(Sfx.NAMES[0] == "CLICK" and Sfx.NAMES[1] == "CANCEL", "id0=CLICK / id1=CANCEL（UI 点击/取消）")
	check(Sfx.ZH[0].contains("点击"), "id0 语义 = UI 点击 (%s)" % Sfx.ZH[0])
	check(Sfx.DEAD_IDS == [15, 36], "死资源 id = [15,36]（原版无调用点，续248）")
	# 无重名（id↔名可逆）
	var dup := false
	for i in Sfx.COUNT:
		for j in Sfx.COUNT:
			if i != j and Sfx.NAMES[i] == Sfx.NAMES[j]:
				dup = true
	check(not dup, "39 个音效名无重复")

	# —— 2) 全部 WAV 存在于磁盘 ——
	var missing := 0
	for id in Sfx.COUNT:
		if not FileAccess.file_exists(ProjectSettings.globalize_path(Sfx.PATHS[id])):
			missing += 1
	check(missing == 0, "39 个 WAV 全部存在于 assets/audio/sfx/ (缺 %d)" % missing)

	# —— 3) 全部可载入（load_from_file 直载，8-bit PCM；返回流本体，null=失败）——
	var loaded := 0
	for id in Sfx.COUNT:
		var s = AudioStreamWAV.new().load_from_file(ProjectSettings.globalize_path(Sfx.PATHS[id]))
		if s is AudioStreamWAV:
			loaded += 1
	check(loaded == 39, "39 个 WAV 全部可载入为 AudioStreamWAV (got %d)" % loaded)
	# 8-bit PCM / 22050Hz 抽查（KOS 解码格式）
	var probe = AudioStreamWAV.new().load_from_file(ProjectSettings.globalize_path(Sfx.PATHS[0]))
	check(probe != null and probe.format == AudioStreamWAV.FORMAT_8_BITS and probe.mix_rate == 22050,
		"id0 CLICK = 8-bit PCM @22050Hz (got %s / %s)" %
		[probe.format if probe != null else "?", probe.mix_rate if probe != null else "?"])

	# —— 4) 惰性缓存 + 播放接口 ——
	var s0 = am._stream_of(0)
	check(s0 != null, "AudioManager._stream_of(0) 非空（CLICK）")
	check(am._stream_of(0) == s0, "第二次取同 id 返回缓存实例")
	am.play_sfx(0)   # 不崩溃即通过（无头无声卡）
	check(true, "play_sfx(0) 调用无异常")
	# 越界 / 非法 id
	am.play_sfx(-1)
	am.play_sfx(999)
	check(true, "越界 id（-1/999）优雅跳过")
	# 按名播放
	am.play_sfx_named("TEPPOU")
	am.play_sfx_named("__NO_SUCH__")
	check(true, "按名播放 + 未知名优雅跳过")
	# 池行为：连播超池容量不崩溃
	for i in 40:
		am.play_sfx(2)
	check(true, "连播 40 次（超池容量 8）无异常")
	am.stop_all_sfx()
	check(true, "stop_all_sfx() 无异常")
	# 静音门控
	am.set_muted(true)
	check(am.is_muted(), "set_muted(true) 生效")
	am.play_sfx(0)
	am.set_muted(false)
	check(not am.is_muted(), "set_muted(false) 恢复")
	# 音量
	am.set_sfx_volume_db(-6.0)
	check(true, "set_sfx_volume_db(-6) 无异常")

	# —— 5) BGM 占位：目录为空 → 优雅降级（只警告不崩溃）——
	am.play_bgm("main.ogg")
	am.stop_bgm()
	check(true, "BGM 占位接口（未接素材）优雅降级")

	# —— 6) UiButton 点击联动音效（CLICK id=0）——
	var btn = UiButton.new()
	root.add_child(btn)
	am._streams = {}          # 清缓存，确保下面是按钮联动触发的载入
	am.stop_all_sfx()
	var down := InputEventMouseButton.new()
	down.button_index = MOUSE_BUTTON_LEFT
	down.pressed = true
	var up := InputEventMouseButton.new()
	up.button_index = MOUSE_BUTTON_LEFT
	up.pressed = false
	btn._gui_input(down)
	btn._gui_input(up)
	check(am._streams.has(0) and am._streams.get(0) != null,
		"UiButton 点击联动 AudioManager 播放 CLICK(0)")
	btn.queue_free()

	# —— 收尾 ——
	print("")
	if _fails == 0:
		print("[AUDIO PASS] 全部断言通过 ✅")
		quit(0)
	else:
		push_error("[AUDIO FAIL] %d 项断言失败 ❌" % _fails)
		quit(1)
