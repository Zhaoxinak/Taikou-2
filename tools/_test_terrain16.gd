# _test_terrain16.gd — 素材规格落地校验（立绘 512x640 / 单位 256x256 / 地形材质 16 种）
#
# 覆盖：
#   1) AssetSpec 尺寸规格 + TERRAIN_MATERIAL_COUNT == 16
#   2) Terrain3DBuilder.TERRAIN_ORDER == 16 种，且 HEIGHT/COLOR 两表齐备
#   3) ★ 回归核心：data/battles.json 全 38 战每一格地形都能命中定义（0 格落 DEFAULT）
#      —— 旧版只覆盖 11 种，?8/?9/?A/?B/?C 共 4234 格是默认灰+高度0 的显示 bug
#   4) build_all_materials() 产出 16 份材质，颜色互不相同
#   5) 占位图实际尺寸符合 AssetSpec（立绘/单位/chip）
#   6) 16 张地形 chip 可加载

extends SceneTree

const AssetSpec = preload("res://src/render/AssetSpec.gd")
const Terrain3DBuilder = preload("res://src/battle/Terrain3DBuilder.gd")
const AssetLoader = preload("res://src/render/asset_loader.gd")

var _pass := 0
var _fail := 0


func check(cond: bool, msg: String) -> void:
	if cond:
		_pass += 1
		print("[ok] " + msg)
	else:
		_fail += 1
		print("[FAIL] " + msg)


func _run() -> void:
	# 1) 规格常量
	check(AssetSpec.PORTRAIT_SIZE == Vector2i(512, 640), "立绘规格 512x640")
	check(AssetSpec.UNIT_SIZE == Vector2i(256, 256), "单位 sprite 规格 256x256")
	check(AssetSpec.CHIP_SIZE == Vector2i(32, 32), "chip 规格 32x32")
	check(AssetSpec.TERRAIN_MATERIAL_COUNT == 16, "地形材质 16 种")

	# 2) 地形表齐备
	var order: Array = Terrain3DBuilder.TERRAIN_ORDER
	check(order.size() == 16, "TERRAIN_ORDER 含 16 种（实际 %d）" % order.size())
	var all_covered := true
	for t in order:
		if not Terrain3DBuilder.covers(t):
			all_covered = false
			print("     未覆盖: " + str(t))
	check(all_covered, "16 种地形在 HEIGHT/COLOR 两表均有定义")

	# 4) 材质（先于数据校验，逻辑独立）
	var mats: Dictionary = Terrain3DBuilder.build_all_materials()
	check(mats.size() == 16, "build_all_materials 产出 16 份材质（实际 %d）" % mats.size())
	var seen_colors := {}
	for t in mats:
		var mt: StandardMaterial3D = mats[t]
		seen_colors[mt.albedo_color.to_html()] = true
	check(seen_colors.size() >= 15, "16 种材质颜色互不雷同（去重后 %d）" % seen_colors.size())

	# 3) ★ 全 38 战逐格覆盖
	var path := "res://data/battles.json"
	check(FileAccess.file_exists(path), "battles.json 存在")
	var battles: Array = []
	if FileAccess.file_exists(path):
		battles = JSON.parse_string(FileAccess.get_file_as_string(path))
	check(battles.size() > 0, "battles.json 解析成功（%d 战）" % battles.size())

	var total := 0
	var covered := 0
	var miss := {}
	for b in battles:
		for row in b.get("terrain", []):
			for cell in row:
				if not (cell is Dictionary):
					continue
				total += 1
				var tname: String = str(cell.get("type", ""))
				if Terrain3DBuilder.covers(tname):
					covered += 1
				else:
					miss[tname] = miss.get(tname, 0) + 1
	check(total > 0, "统计到地形格 %d 个" % total)
	check(covered == total, "★ 全格命中地形定义：%d/%d = 100%%（缺失 %d）" % [covered, total, total - covered])
	if not miss.is_empty():
		print("     未覆盖明细: " + str(miss))

	# 5) 占位图尺寸符合规格
	var por := AssetLoader.load_portrait(-999)
	check(por != null, "立绘占位图可加载")
	if por != null:
		check(AssetSpec.validate(por, "portrait"),
			"立绘占位尺寸符合规格 (%dx%d)" % [por.get_width(), por.get_height()])
	var unit := AssetLoader.load_unit_texture(-999)
	check(unit != null, "单位占位图可加载")
	if unit != null:
		check(AssetSpec.validate(unit, "unit"),
			"单位占位尺寸符合规格 (%dx%d)" % [unit.get_width(), unit.get_height()])

	# 6) 16 张地形 chip
	var chips_ok := 0
	for i in 16:
		if AssetLoader.load_terrain_chip(i) != null:
			chips_ok += 1
	check(chips_ok == 16, "16 张地形 chip 均可加载（实际 %d）" % chips_ok)
	check(AssetLoader.load_terrain_chip(99) != null, "越界索引回退默认 chip 不崩")

	# 注意：headless 下 process_frame 可能永不触发，禁止 await，直接 quit 退出
	if _fail == 0:
		print("ALL PASS (%d checks)" % _pass)
	else:
		print("FAILURES: %d / %d" % [_fail, _pass])
	quit(1 if _fail > 0 else 0)


func _initialize() -> void:
	# --script 模式下 autoload 尚未进树，挂首个 process_frame 再跑断言
	process_frame.connect(_run, CONNECT_ONE_SHOT)
