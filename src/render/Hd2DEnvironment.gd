# Hd2DEnvironment.gd — HD-2D 后处理环境配置
#
# HD-2D 的"电影感"来源：Bloom/Glow + 景深 + SSAO + ACES 色调映射。
# 参考：OCTOPATH TRAVELER / TRIANGLE STRATEGY 的视觉风格。
#
# 用法
# ----
#   var world_env := WorldEnvironment.new()
#   world_env.environment = Hd2DEnvironment.build_environment()
#   add_child(world_env)
#
# 性能分级（4K 下建议降级）
# ------------------------
#   见 build_environment(quality: int) 的 quality 参数

class_name Hd2DEnvironment
extends RefCounted

# 质量档位
enum Quality {
	LOW    = 0,   # 手机/低端：只保留 Glow
	MEDIUM = 1,   # 1080p 默认：Glow + Tonemap + 色彩
	HIGH   = 2,   # 2K/4K：全开（+ DOF + SSAO）
}

# 预设底色（不同场景/时段）
const BG_NIGHT   := Color(0.02, 0.03, 0.06)
const BG_DUSK    := Color(0.08, 0.05, 0.10)
const BG_DAY     := Color(0.04, 0.06, 0.10)
const BG_INDOOR  := Color(0.05, 0.04, 0.03)


# 构建 HD-2D 环境（默认 HIGH）
static func build_environment(quality: int = Quality.HIGH,
		bg_color: Color = BG_DAY) -> Environment:
	var env := Environment.new()

	env.background_mode  = Environment.BG_COLOR
	env.background_color = bg_color

	# 环境光（避免死黑，HD-2D 需要一定环境亮度）
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color  = Color(0.35, 0.38, 0.45)
	env.ambient_light_energy = 0.55

	# ── Glow / Bloom（HD-2D 招牌：柔光溢出）────────────────
	env.glow_enabled       = true
	env.glow_intensity     = 0.55
	env.glow_bloom         = 0.25
	env.glow_hdr_threshold = 0.85
	env.glow_hdr_scale     = 1.2
	env.glow_blend_mode    = Environment.GLOW_BLEND_MODE_SOFTLIGHT
	# ⚠️ glow_mipmap_bias 在 Godot 4.7 已从 Environment 移除（赋值会抛
	#    "Invalid assignment ... value of type float"，导致 build_environment 返回 null）。
	#    默认值本就是 0.0，直接不设即可。

	# ── 色调映射（ACES 电影级）────────────────────────────
	env.tonemap_mode     = Environment.TONE_MAPPER_ACES   # ⚠️ 4.x 属性名为 tonemap_mode（非 tonemapper）
	env.tonemap_exposure = 1.05
	env.tonemap_white    = 1.6

	# ── 色彩微调（HD-2D 偏浓郁）───────────────────────────
	env.adjustment_enabled    = true
	env.adjustment_saturation = 1.15
	env.adjustment_contrast   = 1.08
	env.adjustment_brightness = 1.02

	if quality >= Quality.HIGH:
		# ── 环境光遮蔽（接触阴影，增强体积感）─────────────
		# ⚠️ Godot 4.7.1 的 Environment 已移除 DOF（dof_* 全部不存在），
		#    故 HD-2D 仅用 Glow + SSAO + ACES + 色彩微调，景深效果暂略。
		env.ssao_enabled   = true
		env.ssao_intensity = 0.9
		env.ssao_radius    = 1.2
		env.ssao_detail    = 0.6

	return env


# 天气/时段预设（配合 GAME_DATA_SPEC §3.9 天气系统）
# 返回 {env_override: Callable, light_energy: float, light_color: Color}
static func weather_preset(kind: String) -> Dictionary:
	match kind:
		"晴":
			return {"bg": BG_DAY, "energy": 1.30, "color": Color(1.00, 0.96, 0.88),
					"fog": false, "fog_density": 0.0}
		"雨":
			return {"bg": Color(0.05, 0.07, 0.10), "energy": 0.70,
					"color": Color(0.72, 0.78, 0.90), "fog": true, "fog_density": 0.02}
		"雪":
			return {"bg": Color(0.10, 0.11, 0.14), "energy": 0.90,
					"color": Color(0.88, 0.92, 1.00), "fog": true, "fog_density": 0.015}
		"雾":
			return {"bg": Color(0.09, 0.10, 0.11), "energy": 0.85,
					"color": Color(0.85, 0.86, 0.85), "fog": true, "fog_density": 0.05}
		"夜":
			return {"bg": BG_NIGHT, "energy": 0.25, "color": Color(0.45, 0.55, 0.85),
					"fog": false, "fog_density": 0.0}
		_:
			return {"bg": BG_DAY, "energy": 1.0, "color": Color.WHITE,
					"fog": false, "fog_density": 0.0}


# 把天气预设应用到已存在的 Environment + DirectionalLight3D
static func apply_weather(env: Environment, sun: DirectionalLight3D, kind: String) -> void:
	var p := weather_preset(kind)
	env.background_color = p["bg"]
	if p["fog"]:
		env.fog_enabled        = true
		env.fog_light_color    = p["bg"]
		env.fog_density        = p["fog_density"]
	else:
		env.fog_enabled = false

	if sun:
		sun.light_energy = p["energy"]
		sun.light_color  = p["color"]


# 4K 性能降级：关闭最贵的后处理（DOF 在本版本不存在；降级 SSAO + Glow）
static func downgrade_for_4k(env: Environment) -> void:
	env.ssao_enabled   = false
	env.glow_intensity = 0.45
