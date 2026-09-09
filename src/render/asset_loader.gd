# asset_loader.gd — 美术资源加载（含「真实图缺失→回退占位图」）
#
# HD-4（695 张武将立绘 / 16 张单位 sprite 等）尚未批量生成（需 ImageGen 积分）。
# 本加载器让所有引用美术的位置都能先渲染占位图，等真实美术就位后按同名文件直接替换即可，
# 复刻进度不被美术阻塞。
#
# 用法：
#   var tex := AssetLoader.load_unit_texture(officer_id)   # 有 units/{id}.png 用真图，否则占位
#   var por := AssetLoader.load_portrait(officer_id)

class_name AssetLoader
extends RefCounted

# 素材规格（preload 而非依赖 class_name 全局缓存：新增文件在未重扫前不进缓存）
const AssetSpec = preload("res://src/render/AssetSpec.gd")

const UNIT_PLACEHOLDER := "res://assets/sprites/units/placeholder_unit.png"
const PORTRAIT_PLACEHOLDER := "res://assets/sprites/portraits/placeholder_portrait.png"
const CHIP_PLACEHOLDER := "res://assets/sprites/chips/placeholder_chip.png"


# 单位 sprite：真实 units/{id}.png 缺失时回退占位图
static func load_unit_texture(id: int) -> Texture2D:
	var p := "res://assets/sprites/units/%d.png" % id
	var t := _load_tex(p)
	if t != null:
		return t
	return _load_tex(UNIT_PLACEHOLDER)


# 武将立绘：按「带姓名文件名 → 旧式纯 id → 占位图」依次回退
#
# 命名规则（与 tools/finalize_portraits.py 对齐）：
#   单张  {id}_{姓名}.png        例：13_织田信长.png
#   多张  {id}_{姓名}-1.png …    例：13_织田信长-1.png（默认取 -1）
#
# ⚠️ 本类是 static，拿不到 GameData（非 autoload 解析不到全局名），
#    所以姓名由调用方传入；不传就退回旧式 {id}.png。
#    三级回退保证任何历史命名都不会突然读不到图。
static func load_portrait(id: int, name: String = "") -> Texture2D:
	var dir := "res://assets/sprites/portraits/"
	if name != "":
		for p in [dir + "%d_%s.png" % [id, name], dir + "%d_%s-1.png" % [id, name]]:
			var t := _load_tex(p)
			if t != null:
				return t
	var t2 := _load_tex(dir + "%d.png" % id)
	if t2 != null:
		return t2
	return _load_tex(PORTRAIT_PLACEHOLDER)


# 小图（地形/UI 碎片）
static func load_chip(name: String) -> Texture2D:
	var p := "res://assets/sprites/chips/%s.png" % name
	var t := _load_tex(p)
	if t != null:
		return t
	return _load_tex(CHIP_PLACEHOLDER)


# 地形材质 chip（16 种，terrain_00..15.png；索引→名见 chips/terrain_index.json）
# 序号对应 Terrain3DBuilder.TERRAIN_ORDER
static func load_terrain_chip(index: int) -> Texture2D:
	if index < 0 or index >= AssetSpec.TERRAIN_MATERIAL_COUNT:
		return _load_tex(CHIP_PLACEHOLDER)
	var t := _load_tex("res://assets/sprites/chips/terrain_%02d.png" % index)
	if t != null:
		return t
	return _load_tex(CHIP_PLACEHOLDER)


# 加载纹理：已导入（编辑器内，存在 .import）走 load() 最快；
# 未导入（占位图 / headless）直接 Image.load 读文件，避免 "No loader found" 噪声。
static func _load_tex(path: String) -> Texture2D:
	if not FileAccess.file_exists(path):
		return null
	if FileAccess.file_exists(path + ".import"):
		var t := load(path)
		if t is Texture2D:
			return t
	var img := Image.new()
	if img.load(path) == OK:
		return ImageTexture.create_from_image(img)
	return null
