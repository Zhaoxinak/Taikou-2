# AssetSpec.gd — 美术素材规格（★ 单一真源）
#
# 太阁2 复刻的美术规格。所有生成/加载/校验都以此为准，避免各处硬编码尺寸漂移。
#
#  立绘 portrait  512×640
#  单位 sprite    256×256
#  地形/UI chip    32×32   （原版尺寸）
#
# 真实美术就位前，占位图按本规格生成（scripts/gen_placeholders.py），
# 真图按同名替换即可，无需改代码。

class_name AssetSpec
extends RefCounted

# ── 尺寸规格 ─────────────────────────────────────────────
const PORTRAIT_SIZE := Vector2i(512, 640)
const UNIT_SIZE     := Vector2i(256, 256)
const CHIP_SIZE     := Vector2i(32, 32)

# 按用途返回规格尺寸
static func size_for(kind: String) -> Vector2i:
	match kind:
		"portrait":
			return PORTRAIT_SIZE
		"unit":
			return UNIT_SIZE
		"chip":
			return CHIP_SIZE
		_:
			return Vector2i.ZERO


# 校验纹理尺寸是否符合规格（真图接入时用来卡规格，尺寸不对会打警告但不阻断）
static func validate(tex: Texture2D, kind: String) -> bool:
	if tex == null:
		return false
	var want := size_for(kind)
	if want == Vector2i.ZERO:
		return false
	return tex.get_width() == want.x and tex.get_height() == want.y


# 规格描述（调试/日志用）
static func describe() -> String:
	return "素材规格：立绘 %dx%d / 单位 %dx%d / chip %dx%d" % [
		PORTRAIT_SIZE.x, PORTRAIT_SIZE.y,
		UNIT_SIZE.x, UNIT_SIZE.y,
		CHIP_SIZE.x, CHIP_SIZE.y,
	]
