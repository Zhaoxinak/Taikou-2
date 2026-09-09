# WeatherFX.gd — HD-3 天气粒子特效（雨 / 雪）
#
# 晴 / 夜 / 雾 不需要粒子（雾用 Environment.fog 表现，见 Hd2DEnvironment）。
# 仅 雨 / 雪 用 GPUParticles3D 在战场上方撒粒子。
#
# 分成两层：
#   - build_material / build_draw_mesh：纯 CPU 对象（ParticleProcessMaterial / QuadMesh），
#     参数逻辑可在 headless 测试里校验，不依赖 GPU 渲染设备。
#   - make_particles：把上面两者组装成 GPUParticles3D 节点，运行时（有 GPU 窗口）调用。
#
# 用法
# ----
#   var fx := WeatherFX.make_particles("雨")      # 返回含粒子的 Node3D；无粒子时返回 null
#   if fx: add_child(fx)
#
# 实测战场范围约 40×19 格（tile_size=1）；粒子盒取 (22, 14, 26) 覆盖全场。

class_name WeatherFX
extends RefCounted

const RAIN_CHARS := ["雨"]
const SNOW_CHARS := ["雪"]

# 默认粒子盒半边长（覆盖战场中心向上发散）
const DEFAULT_HALF := Vector3(22.0, 14.0, 26.0)


# 该天气是否需要粒子（晴/夜/雾 不需要）
static func needs_particles(kind: String) -> bool:
	return kind in RAIN_CHARS or kind in SNOW_CHARS


# 根据天气创建粒子节点；晴/夜/雾 返回 null。
# 注：GPUParticles3D 需 GPU 渲染设备，仅在游戏窗口运行时调用，勿在 headless 测试里构造。
static func make_particles(kind: String,
		half_extents: Vector3 = DEFAULT_HALF) -> Node:
	if not needs_particles(kind):
		return null

	var root := Node3D.new()
	root.name = "WeatherFX"

	var p := GPUParticles3D.new()
	p.name = "Particles"
	p.amount = 900 if kind in RAIN_CHARS else 500
	p.lifetime = (2.0 * half_extents.y) / (21.0 if kind in RAIN_CHARS else 2.4)
	p.process_material = build_material(kind, half_extents)
	p.emitting = true
	p.draw_pass_1 = build_draw_mesh(kind)

	root.add_child(p)
	return root


# 雨/雪 粒子材质（CPU 对象，可在 headless 校验参数）
static func build_material(kind: String,
		half_extents: Vector3 = DEFAULT_HALF) -> ParticleProcessMaterial:
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = half_extents
	pm.direction = Vector3(0, -1, 0)

	if kind in RAIN_CHARS:
		pm.spread = 6.0
		pm.gravity = Vector3(0, -28.0, 0)
		pm.initial_velocity_min = 18.0
		pm.initial_velocity_max = 24.0
		pm.color = Color(0.62, 0.72, 0.92, 0.45)
		pm.angle_min = -4.0
		pm.angle_max = 4.0
	else:  # 雪
		pm.spread = 40.0
		pm.gravity = Vector3(0, -2.2, 0)
		pm.initial_velocity_min = 1.4
		pm.initial_velocity_max = 3.2
		pm.angular_velocity_min = -1.5
		pm.angular_velocity_max = 1.5
		pm.color = Color(1.0, 1.0, 1.0, 0.92)
	return pm


# 雨/雪 粒子面片（CPU 对象）
static func build_draw_mesh(kind: String) -> QuadMesh:
	var q := QuadMesh.new()
	if kind in RAIN_CHARS:
		q.size = Vector2(0.04, 0.55)   # 细长雨丝
	else:
		q.size = Vector2(0.16, 0.16)   # 方雪片
	return q
