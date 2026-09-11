extends SceneTree
## HD-2D 大地图样板（八方旅人式）：
## 3D 立体地形（高度图生成网格）+ 透视相机俯视跟随 + 像素武士行走 + 辉光/暗角/雾氛围
## 用法：Godot --path . --script res://tools/_shot_hd2d.gd
## 输出：user://hd2d_{1,2,3}.png

const HEIGHT_PNG := "res://assets/terrain3d/height_winter.png"
const COLOR_PNG := "res://assets/terrain3d/color_spring.png"

# 地形网格分辨率（顶点数 = GW x GH）
const GW := 400
const GH := 300
const MAP_W := 48.0
const MAP_H := 36.0
const Y_SCALE := 0.55          # 高度放大（山高 ~7 单位，柔和丘陵）
const H_MIN := -0.5
const H_MAX := 6.0

var _player: Sprite3D
var _cam: Camera3D
var _cam_attrs: CameraAttributesPhysical
var _frames: Array = []       # 8 帧贴图 [朝向][帧] 扁平
var _frame := 0
var _walk := 0
var _face := Vector2.RIGHT
var _path: Array = []
var _step := 0

func _init() -> void:
	process_frame.connect(_tick)

func _log(msg: String) -> void:
	print("[hd2d] ", msg)

# ------------------------------------------------------------
# 1. 3D 地形生成：高度图 → ArrayMesh + 贴图
# ------------------------------------------------------------
func build_terrain(root_node: Node) -> void:
	var himg := Image.load_from_file(ProjectSettings.globalize_path(HEIGHT_PNG))
	if himg.is_empty():
		_log("高度图加载失败")
		quit(1)
		return
	himg.resize(GW, GH)   # 采样到网格分辨率
	var cimg := Image.load_from_file(ProjectSettings.globalize_path(COLOR_PNG))

	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	# 逻辑坐标 → 世界：北在 -Z，地图中心在原点
	# (lx, ly): lx 0..48 (西→东), ly 0..36 (南→北)
	for j in range(GH):
		for i in range(GW):
			var ly := j / float(GH - 1) * MAP_H            # j=0（图像顶=北）→ ly=0（proj 北）
			var lx := i / float(GW - 1) * MAP_W
			var h: float = himg.get_pixel(i, j).r * (H_MAX - H_MIN) + H_MIN
			var wy := h * Y_SCALE
			var pos := Vector3(lx - MAP_W / 2.0, wy, -(ly - MAP_H / 2.0))
			# 顶点索引 j*GW+i；面（每格 2 三角）
			if i < GW - 1 and j < GH - 1:
				var a := j * GW + i
				var b := a + 1
				var c := a + GW
				var d := c + 1
				# UV：u=东向、v=南向（贴图顶部=北）
				var u0 := i / float(GW - 1)
				var v0 := j / float(GH - 1)
				var u1 := (i + 1) / float(GW - 1)
				var v1 := (j + 1) / float(GH - 1)
				# 三角 1: a-b-c
				st.set_uv(Vector2(u0, v0)); st.add_vertex(vert(a))
				st.set_uv(Vector2(u1, v0)); st.add_vertex(vert(b))
				st.set_uv(Vector2(u0, v1)); st.add_vertex(vert(c))
				# 三角 2: b-d-c
				st.set_uv(Vector2(u1, v0)); st.add_vertex(vert(b))
				st.set_uv(Vector2(u1, v1)); st.add_vertex(vert(d))
				st.set_uv(Vector2(u0, v1)); st.add_vertex(vert(c))
	var mesh := st.commit()

	var mi := MeshInstance3D.new()
	mi.name = "Terrain3D"
	mi.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_texture = ImageTexture.create_from_image(cimg)
	mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mi.material_override = mat
	root_node.add_child(mi)
	var varr: Array = mesh.surface_get_arrays(0)
	_log("地形生成完成: %d 顶点" % (varr[Mesh.ARRAY_VERTEX] as PackedVector3Array).size())

func vert(idx: int) -> Vector3:
	# 用矩阵重建顶点位置（与循环同式）
	var j := idx / GW
	var i := idx % GW
	var ly := j / float(GH - 1) * MAP_H
	var lx := i / float(GW - 1) * MAP_W
	var h: float = (_hvals[j * GW + i])
	return Vector3(lx - MAP_W / 2.0, h * Y_SCALE, -(ly - MAP_H / 2.0))


func terrain_h_at(wx: float, wz: float) -> float:
	var lx := wx + MAP_W / 2.0
	var ly := MAP_H / 2.0 - wz
	var i := int(clampf(lx / MAP_W * (GW - 1), 0, GW - 1))
	var j := int(clampf(ly / MAP_H * (GH - 1), 0, GH - 1))
	return _hvals[j * GW + i] * Y_SCALE

var _hvals: PackedFloat32Array

# ------------------------------------------------------------
# 2. 像素武士纹理（16x20 逻辑像素，4 朝向 + 2 走路帧）
#    复刻 world_screen._draw_pixel_samurai 的配色与造型
# ------------------------------------------------------------
func make_samurai_frames() -> void:
	var skin := Color(0.92, 0.78, 0.62)
	var hair := Color(0.16, 0.13, 0.11)
	var robe := Color(0.20, 0.26, 0.36)
	var belt := Color(0.90, 0.86, 0.78)
	var pant := Color(0.24, 0.22, 0.20)
	var accent := Color(0.78, 0.24, 0.18)
	var faces := [Vector2.RIGHT, Vector2.LEFT, Vector2.DOWN, Vector2.UP]
	for fi in range(4):
		var face: Vector2 = faces[fi]
		var flip: bool = face.x < -0.1
		var horiz: bool = abs(face.x) > abs(face.y)
		for fr in range(2):
			var img := Image.create(16, 20, false, Image.FORMAT_RGBA8)
			img.fill(Color(0, 0, 0, 0))
			var px := func(x: int, y: int, c: Color) -> void:
				for dx in range(1):
					for dy in range(1):
						if x >= 0 and x < 16 and y >= 0 and y < 20:
							img.set_pixel(x, y, c)
			if horiz:
				# 侧面
				for y in range(6): for x in range(8): px.call(3 + (5 if flip else 3), y, skin)
				# 头
				for y in range(6):
					for x in range(8):
						px.call((3 if flip else 5) + x, y, skin)
				# 髻
				for y in range(4):
					for x in range(4):
						px.call((2 if flip else 4) + x, y - 3, hair)
				# 胴
				for y in range(8):
					for x in range(10):
						px.call((2 if flip else 3) + x, y + 6, robe)
				# 腰带
				for y in range(2):
					for x in range(11):
						px.call((1 if flip else 2) + x, y + 7, belt)
				# 腿（2 帧交替）
				if fr == 0:
					for y in range(5): for x in range(3): px.call((3 if flip else 5) + x, y + 14, pant)
					for y in range(5): for x in range(3): px.call((7 if flip else 9) + x, y + 14, pant)
				else:
					for y in range(5): for x in range(3): px.call((1 if flip else 3) + x, y + 14, pant)
					for y in range(5): for x in range(3): px.call((9 if flip else 11) + x, y + 14, pant)
			else:
				var back: bool = face.y < -0.1
				# 头
				for y in range(7):
					for x in range(8):
						px.call(4 + x, y, hair if back else skin)
				# 髻
				for y in range(4):
					for x in range(6):
						px.call(5 + x, y - 3, hair)
				if not back:
					for y in range(3):
						for x in range(3):
							px.call(5 + x, y + 1, skin)
				# 胴
				for y in range(9):
					for x in range(12):
						px.call(2 + x, y + 7, robe)
				# 腰带
				for y in range(2):
					for x in range(14):
						px.call(1 + x, y + 8, belt)
				# 肩带
				for y in range(2):
					for x in range(6):
						px.call(5 + x, y + 12, accent)
				# 腿
				if fr == 0:
					for y in range(5): for x in range(4): px.call(3 + x, y + 16, pant)
					for y in range(5): for x in range(4): px.call(9 + x, y + 16, pant)
				else:
					for y in range(5): for x in range(4): px.call(1 + x, y + 16, pant)
					for y in range(5): for x in range(4): px.call(11 + x, y + 16, pant)
			_frames.append(ImageTexture.create_from_image(img))

# ------------------------------------------------------------
# 3. 相机 + 氛围
# ------------------------------------------------------------
func build_camera(root_node: Node) -> void:
	_cam = Camera3D.new()
	_cam.name = "HD2DCam"
	_cam.fov = 55.0
	_cam.near = 0.1
	_cam.far = 300.0
	root_node.add_child(_cam)
	_cam.current = true
	# 景深（4.x CameraAttributes DOF，存在则启用）
	_cam_attrs = CameraAttributesPhysical.new()
	if "dof_blur_far_enabled" in _cam_attrs:
		_cam_attrs.set("dof_blur_far_enabled", true)
		_cam_attrs.set("dof_blur_far_distance", 18.0)
		_cam_attrs.set("dof_blur_far_transition", 8.0)
		_cam_attrs.set("dof_blur_far_amount", 0.6)
		_cam.attributes = _cam_attrs
	else:
		_log("本版本无 DOF，跳过景深")

	# 氛围：辉光 + 雾 + 天空 + 环境光
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.72, 0.82, 0.92)
	sky_mat.sky_horizon_color = Color(0.93, 0.95, 0.95)
	sky_mat.ground_bottom_color = Color(0.75, 0.83, 0.88)
	sky_mat.ground_horizon_color = Color(0.92, 0.94, 0.93)
	sky.sky_material = sky_mat
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 1.2
	env.glow_enabled = true
	env.glow_intensity = 0.55
	env.glow_bloom = 0.08
	env.glow_hdr_threshold = 0.85
	env.fog_enabled = true
	env.fog_light_color = Color(0.88, 0.91, 0.93)
	env.fog_density = 0.0008
	var we := WorldEnvironment.new()
	we.environment = env
	root_node.add_child(we)
	# 左上太阳光（Blender v6 同款方向：立体感来源）
	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-58, -42, 0)
	sun.light_energy = 1.6
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 200.0
	root_node.add_child(sun)
	_log("相机+氛围就绪")

# 暗角（CanvasLayer 径向渐变）
func build_vignette(root_node: Node) -> void:
	var cl := CanvasLayer.new()
	cl.layer = 100
	root_node.add_child(cl)
	var tr := TextureRect.new()
	tr.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	tr.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var grad := Gradient.new()
	grad.offsets = PackedFloat32Array([0.0, 0.55, 1.0])
	grad.colors = PackedColorArray([Color(0, 0, 0, 0), Color(0, 0, 0, 0.16), Color(0, 0, 0, 0.55)])
	var gtex := GradientTexture2D.new()
	gtex.gradient = grad
	gtex.fill = GradientTexture2D.FILL_RADIAL
	gtex.fill_from = Vector2(0.5, 0.5)
	gtex.fill_to = Vector2(1.0, 1.0)
	tr.texture = gtex
	cl.add_child(tr)
	_log("暗角就绪")

# ------------------------------------------------------------
# 4. 玩家 + 移动
# ------------------------------------------------------------
func build_player(root_node: Node) -> void:
	_player = Sprite3D.new()
	_player.name = "Player"
	_player.texture = _frames[0]
	_player.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_player.pixel_size = 0.10
	_player.position = world_of(Vector2(21.8, 21.4))
	root_node.add_child(_player)
	# 脚下阴影（HD-2D 角色贴地感）
	var shadow := MeshInstance3D.new()
	shadow.name = "Shadow"
	var sm := QuadMesh.new()
	sm.size = Vector2(0.9, 0.5)
	var smat := StandardMaterial3D.new()
	smat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	smat.albedo_color = Color(0, 0, 0, 0.30)
	smat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	smat.cull_mode = BaseMaterial3D.CULL_DISABLED
	shadow.mesh = sm
	shadow.material_override = smat
	_player.add_child(shadow)
	shadow.position = Vector3(0, -0.05, 0)
	shadow.rotation_degrees = Vector3(-90, 0, 0)
	_log("玩家就绪")

func world_of(lp: Vector2) -> Vector3:
	# 逻辑坐标 → 世界（含地形高度）
	var lx := clampf(lp.x, 0, MAP_W)
	var ly := clampf(lp.y, 0, MAP_H)
	# 采样高度（近邻）
	var i := int(lx / MAP_W * (GW - 1))
	var j := int(ly / MAP_H * (GH - 1))
	var h: float = _hvals[j * GW + i]
	return Vector3(lx - MAP_W / 2.0, h * Y_SCALE + 0.6, -(ly - MAP_H / 2.0))

func _tick() -> void:
	_frame += 1
	if _frame == 1:
		root.size = Vector2i(1920, 1080)
		# 预采样高度
		var himg := Image.load_from_file(ProjectSettings.globalize_path(HEIGHT_PNG))
		himg.resize(GW, GH)
		_hvals = PackedFloat32Array()
		_hvals.resize(GW * GH)
		for j in range(GH):
			for i in range(GW):
				_hvals[j * GW + i] = himg.get_pixel(i, j).r * (H_MAX - H_MIN) + H_MIN
		make_samurai_frames()
		build_terrain(root)
		build_camera(root)
		build_vignette(root)
		build_player(root)
		# 演示路径：清洲(22.4,23.5) → 西北穿越近江山地 → 琵琶湖东南(20.5,19.5)
		_path = [
			Vector2(22.0, 20.8), Vector2(22.2, 20.2), Vector2(22.0, 20.7),
			Vector2(21.8, 21.3),
		]
		_log("启动")
		return
	if _frame < 8:
		return
	# 自动移动
	if _step < _path.size():
		var target: Vector2 = _path[_step]
		var cur := Vector2(_player.position.x + MAP_W / 2.0, -( _player.position.z - 0.0) + MAP_H / 2.0 - 0.0)
		# 从世界反推逻辑（简化：不取高度）
		cur = Vector2(_player.position.x + MAP_W / 2.0, -_player.position.z + MAP_H / 2.0)
		var d: Vector2 = target - cur
		var speed := 0.06
		if d.length() > speed:
			var np: Vector2 = cur + d.normalized() * speed
			_face = d.normalized()
			_player.position = world_of(np)
			_walk += 1
			_player.texture = _frames[face_index() * 2 + (_walk / 6) % 2]
		else:
			_step += 1
			_player.texture = _frames[face_index() * 2]
	# 相机跟随（平滑）
	var cam_target: Vector3 = _player.position + Vector3(0, 0, -1.2)
	cam_target.y = terrain_h_at(cam_target.x, cam_target.z) + 1.8
	var target_pos: Vector3 = _cam.position.lerp(cam_target, 0.18)
	_cam.position = target_pos
	_cam.look_at(_player.position + Vector3(0, 0.1, 0), Vector3.UP)
	# 诊断
	if _frame == 40:
		_log("cam=%s player=%s" % [_cam.position, _player.position])
	# 截图
	if _frame == 20 or _frame == 45 or _frame == 70:
		var img := root.get_viewport().get_texture().get_image()
		var idx := 1
		if _frame == 45: idx = 2
		elif _frame == 70: idx = 3
		var p := "user://hd2d_%d.png" % idx
		img.save_png(p)
		_log("截图 %d 保存: %s" % [idx, ProjectSettings.globalize_path(p)])
	if _frame >= 80:
		_log("完成")
		quit(0)

func face_index() -> int:
	if abs(_face.x) > abs(_face.y):
		return 0 if _face.x > 0 else 1
	return 2 if _face.y > 0 else 3
