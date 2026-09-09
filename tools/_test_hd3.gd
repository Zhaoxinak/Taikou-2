# _test_hd3.gd — HD-3 光照 + 天气联动 校验
#
# 覆盖：
#   1) Hd2DEnvironment.build_environment 三种质量档
#   2) weather_preset 全部天气（晴/雨/雪/雾/夜/未知）
#   3) apply_weather 改环境（雾开关）+ 太阳能量（夜降）
#   4) downgrade_for_4k 关 SSAO + DOF
#   5) WeatherFX 雨/雪 材质/网格参数（CPU 安全，不构造 GPUParticles3D）
#   6) WeatherFX.needs_particles 分支（晴/夜/雾=false）
#   7) 集成：WorldEnvironment + DirectionalLight3D 跑通 apply_weather
#
# 注：GPUParticles3D 需 GPU 渲染设备，不在 headless 里构造；其参数由 build_material 校验。

extends SceneTree

const Hd2DEnvironment = preload("res://src/render/Hd2DEnvironment.gd")
const WeatherFX = preload("res://src/render/WeatherFX.gd")

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
	# 1) build_environment 三档
	for q in [Hd2DEnvironment.Quality.LOW,
			Hd2DEnvironment.Quality.MEDIUM,
			Hd2DEnvironment.Quality.HIGH]:
		var e := Hd2DEnvironment.build_environment(q)
		check(e is Environment, "build_environment(%d) 返回 Environment" % q)
		check(e.glow_enabled, "build_environment 开启 Glow")
		check(e.tonemapper == Environment.TONE_MAPPER_ACES, "ACES 色调映射已设")
		check(e.adjustment_enabled, "色彩微调已开（HD-2D 浓郁）")

	# 2) weather_preset 全覆盖
	for kind in ["晴", "雨", "雪", "雾", "夜", "未知X"]:
		var p := Hd2DEnvironment.weather_preset(kind)
		check(p.has("bg") and p.has("energy") and p.has("color") and p.has("fog"),
			"weather_preset(%s) 含 bg/energy/color/fog" % kind)

	# 3) apply_weather：环境 + 太阳联动
	var env := Hd2DEnvironment.build_environment(Hd2DEnvironment.Quality.HIGH)
	var sun := DirectionalLight3D.new()
	var e0: float = sun.light_energy
	Hd2DEnvironment.apply_weather(env, sun, "夜")
	check(sun.light_energy < e0, "夜：太阳能量下降 (%f -> %f)" % [e0, sun.light_energy])
	check(env.fog_enabled == false, "夜：无雾")
	Hd2DEnvironment.apply_weather(env, sun, "雨")
	check(env.fog_enabled and env.fog_density > 0.0, "雨：开启雾 density=%f" % env.fog_density)
	Hd2DEnvironment.apply_weather(env, sun, "雪")
	check(env.fog_enabled and env.fog_density > 0.0, "雪：开启雾")
	Hd2DEnvironment.apply_weather(env, sun, "雾")
	check(env.fog_enabled and env.fog_density > 0.0, "雾：开启浓雾")
	Hd2DEnvironment.apply_weather(env, sun, "晴")
	check(env.fog_enabled == false, "晴：雾关闭")
	# sun=null 不崩
	Hd2DEnvironment.apply_weather(env, null, "雪")
	check(true, "apply_weather(sun=null) 不崩溃")

	# 4) downgrade_for_4k
	var env2 := Hd2DEnvironment.build_environment(Hd2DEnvironment.Quality.HIGH)
	Hd2DEnvironment.downgrade_for_4k(env2)
	check(not env2.ssao_enabled and not env2.dof_blur_far_enabled,
		"downgrade_for_4k 关 SSAO + DOF")

	# 5) WeatherFX 雨/雪 材质 + 网格参数（CPU 安全）
	var h := Vector3(22, 14, 26)
	var rm := WeatherFX.build_material("雨", h)
	check(rm is ParticleProcessMaterial, "雨 材质为 ParticleProcessMaterial")
	check(rm.emission_box_extents == h, "雨 发射盒=战场范围")
	check(rm.gravity.y < -10.0, "雨 重力向下（下落）")
	check(rm.initial_velocity_max > rm.initial_velocity_min, "雨 速度区间合理")
	check(abs(rm.color.a - 0.45) < 0.01, "雨 半透明")
	var sm := WeatherFX.build_material("雪", h)
	check(sm.gravity.y < 0.0 and sm.gravity.y > -10.0, "雪 缓降重力")
	check(sm.angular_velocity_max > 0.0, "雪 有旋转飘动")
	var rmesh := WeatherFX.build_draw_mesh("雨")
	check(rmesh is QuadMesh and rmesh.size.y > rmesh.size.x, "雨 面片细长（雨丝）")
	var smesh := WeatherFX.build_draw_mesh("雪")
	check(smesh is QuadMesh and abs(smesh.size.x - smesh.size.y) < 0.001, "雪 面片方形")

	# 6) needs_particles 分支
	for k in ["雨", "雪"]:
		check(WeatherFX.needs_particles(k), "needs_particles(%s)=true" % k)
	for k in ["晴", "夜", "雾"]:
		check(not WeatherFX.needs_particles(k), "needs_particles(%s)=false" % k)

	# 7) 集成：WorldEnvironment + 太阳 完整路径
	var root := Node3D.new()
	var dl := DirectionalLight3D.new()
	dl.name = "DirectionalLight3D"
	root.add_child(dl)
	var we := WorldEnvironment.new()
	we.environment = Hd2DEnvironment.build_environment(Hd2DEnvironment.Quality.MEDIUM)
	root.add_child(we)
	Hd2DEnvironment.apply_weather(we.environment, dl, "雨")
	check(we.environment.fog_enabled, "集成：WorldEnvironment 雨 雾生效")
	check(dl.light_energy < 1.2, "集成：雨 太阳能量降低")
	root.free()

	await process_frame
	if _fail == 0:
		print("ALL PASS (%d checks)" % _pass)
		quit(0)
	else:
		print("FAILURES: %d / %d" % [_fail, _pass])
		quit(1)


func _initialize() -> void:
	# --script 模式下 autoload 尚未进树，挂首个 process_frame 再跑断言
	process_frame.connect(_run, CONNECT_ONE_SHOT)
