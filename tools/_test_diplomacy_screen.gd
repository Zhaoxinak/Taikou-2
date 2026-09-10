# _test_diplomacy_screen.gd — 外交関係一览画面 单元测试（Godot 侧）
# 触发：Godot --headless --script res://tools/_test_diplomacy_screen.gd
# ⚠️ --script 模式下 autoload 不是全局标识符，必须 root.get_node("/root/GameState") 取。
extends SceneTree

const DiplomacyRef = preload("res://src/core/diplomacy.gd")
const UiButton = preload("res://src/ui/UiButton.gd")

var _pass := 0
var _fail := 0
var gs                                  # /root/GameState
var gd                                  # /root/GameData

func chk(name: String, cond: bool, detail: String = "") -> void:
	if cond:
		_pass += 1
	else:
		_fail += 1
		print("  FAIL  %s%s" % [name, ("  (%s)" % detail) if detail != "" else ""])

func _run() -> void:
	gs = root.get_node("/root/GameState")
	gd = root.get_node("/root/GameData")

	chk("start_new_game(13)", gs.start_new_game(13))

	print("=== 外交関係一览屏 ===")
	# 运行时 load（避免顶层 preload 在 autoload 注册前编译 command_screen/diplomacy_screen）
	var DiplomacyScreen = load("res://src/ui/diplomacy_screen.gd")
	var CommandScreen = load("res://src/ui/command_screen.gd")
	# 两个屏都挂到树（_ready 同步或下一帧触发），再统一用一次 process_frame 等 _ready 完成
	var scr = DiplomacyScreen.new()
	scr.callback_back = _nop
	root.add_child(scr)
	var cmd = CommandScreen.new()
	root.add_child(cmd)
	await process_frame

	var self_p: int = int(gs.protagonist_province())
	chk("自国有效 0..48", self_p >= 0 and self_p < 49, "self=%d" % self_p)
	chk("屏内 _self == protagonist_province", scr._self == self_p)
	chk("列出 49 行（每国一行）", scr._rows.size() == 49, "rows=%d" % scr._rows.size())

	# 关系值合法性（遍历除自国外的 48 国）
	var bad_d: int = 0
	var bad_m: int = 0
	for p in 49:
		if p == self_p:
			continue
		var d: int = int(gs.diplomacy.get_diplomacy(self_p, p))
		var m: int = int(gs.diplomacy.get_master_vassal(self_p, p))
		if d < 0 or d > 7:
			bad_d += 1
		if m < 0 or m > 3:
			bad_m += 1
	chk("外交関係 均在 0..7", bad_d == 0, "bad_d=%d" % bad_d)
	chk("主从関係 均在 0..3", bad_m == 0, "bad_m=%d" % bad_m)

	# 色板：DIPL_COLOR / MV_COLOR 索引 → 合法 Color（a>0）
	var other: int = (self_p + 1) % 49
	if other == self_p:
		other = (self_p + 2) % 49
	var sample_d: int = int(gs.diplomacy.get_diplomacy(self_p, other))
	var col = scr._tier_color(int(DiplomacyRef.DIPL_COLOR[sample_d]))
	chk("等级色板返回合法色（a>0）", col.a > 0.0)

	chk("图例已构建", scr._legend_ok)

	# callback_back 接线：调用 _on_back 应触发注入的回调
	# ⚠️ GDScript lambda 按值捕获 → 用 Array 持有可变计数
	var called: Array = [0]
	scr.callback_back = func(): called[0] += 1
	scr._on_back()
	chk("callback_back 被触发", called[0] == 1)

	print("=== command_screen 入口接线 ===")
	var dip_btn = null
	for c in cmd.get_children():
		if c is UiButton and str(c.text) == "外交関係一览":
			dip_btn = c
			break
	chk("command_screen 含「外交関係一览」钮", dip_btn != null)
	chk("未挂载时 _dip_screen 为空", cmd._dip_screen == null)

	# 打开/关闭为同步逻辑（无需额外帧）：验证接线
	cmd._on_open_diplomacy()
	chk("点击后挂载 DiplomacyScreen", cmd._dip_screen != null)
	var has_screen: bool = false
	for c in cmd.get_children():
		if c.get_script() == DiplomacyScreen:
			has_screen = true
			break
	chk("command_screen 子树含 DiplomacyScreen 实例", has_screen)
	cmd._close_diplomacy()
	chk("关闭后 _dip_screen 复位", cmd._dip_screen == null)

	scr.queue_free()
	cmd.queue_free()

	print("\n%d PASS / %d FAIL" % [_pass, _fail])
	quit(0 if _fail == 0 else 1)

func _nop() -> void:
	pass

func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)
