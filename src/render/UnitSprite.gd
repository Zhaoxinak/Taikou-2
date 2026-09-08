# UnitSprite.gd — HD-2D 单位/角色 sprite（billboard 像素面片）
#
# HD-2D 的灵魂：角色是**高分辨率像素 art**，用 billboard 面片贴在 3D 场景里，
# 纹理过滤必须 NEAREST（保持硬边像素，不做平滑插值）。
#
# 用法
# ----
#   var s := UnitSprite.make(tex, Vector3(10, 0, 5))
#   units_root.add_child(s)

class_name UnitSprite
extends RefCounted

# 默认像素尺寸（世界单位/像素）——越小 sprite 越大
const DEFAULT_PIXEL_SIZE := 0.012

# 阵营色调（用于区分敌我，叠加在 sprite 上）
const TINT_ALLY  := Color(1.0, 1.0, 1.0, 1.0)
const TINT_ENEMY := Color(1.0, 0.82, 0.82, 1.0)
const TINT_SELF  := Color(0.85, 1.0, 0.85, 1.0)


# 创建一个 billboard 像素 sprite
static func make(tex: Texture2D, pos: Vector3,
		pixel_size: float = DEFAULT_PIXEL_SIZE,
		tint: Color = Color.WHITE) -> Sprite3D:
	var s := Sprite3D.new()
	s.texture = tex

	# ★ HD-2D 核心：NEAREST 过滤保住像素硬边
	s.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST

	# 永远面向相机
	s.billboard = BaseMaterial3D.BILLBOARD_ENABLED

	# 保持 Y 轴对齐（角色不会随相机俯仰而倒下）
	s.axis = Vector3.AXIS_Y

	s.pixel_size  = pixel_size
	s.position    = pos
	s.modulate    = tint

	# 投射阴影 → HD-2D 的体积感
	s.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON

	# 透明混合（默认 alpha_cut 关闭即可，保持像素 sprite 完整半透明）
	s.transparent    = true
	s.shaded         = true   # 受光照影响（HD-2D 角色会被场景光照亮）

	return s


# 单位高亮（选中/悬停）
static func set_highlight(s: Sprite3D, on: bool) -> void:
	if on:
		s.modulate = Color(1.25, 1.15, 0.85, 1.0)
	else:
		s.modulate = Color.WHITE


# 从图集创建帧动画 sprite（步行/攻击）
static func make_animated(frames: Array[Texture2D], pos: Vector3,
		fps: float = 8.0) -> AnimatedSprite3D:
	var a := AnimatedSprite3D.new()
	a.billboard      = BaseMaterial3D.BILLBOARD_ENABLED
	a.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	a.position       = pos

	var lib := SpriteFrames.new()
	lib.add_animation("default")
	lib.set_animation_speed("default", fps)
	lib.set_animation_loop("default", true)
	for f in frames:
		lib.add_frame("default", f)
	a.sprite_frames = lib
	a.play("default")
	return a


# 世界坐标换算：格 (gx,gz) → 3D 位置（地形高度 h）
static func grid_to_world(gx: int, gz: int, h: float = 0.0,
		tile_size: float = 1.0) -> Vector3:
	return Vector3(
		(gx + 0.5) * tile_size,
		h,
		(gz + 0.5) * tile_size
	)
