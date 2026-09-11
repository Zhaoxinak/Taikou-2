extends Node3D
## world3d_map.gd — HD-2D 大地图 3D 层（八方旅人风格）
##
## 由 world_screen.gd 挂载在 SubViewport 内渲染：
##   · 3D 地形网格（史实高度图 height_winter.png + 季节颜色贴图 color_{season}.png）
##   · 200 城 3D 城标（Sprite3D billboard 分级：町城红/军事白/港蓝）+ 近处城名 Label3D
##   · 像素武士主角（Sprite3D，4 朝向 × 2 走路帧，脚下阴影）
##   · 相机近距离跟随玩家（聚焦玩家周围，站在地形上不穿地）
##   · 天空 / 太阳光 / 雾 / 辉光 / 暗角（八方旅人氛围）
##
## ⚠️ 不用 class_name（--script 无头模式不建全局类缓存），跨文件 preload。

const MAP_W := 48.0
const MAP_H := 36.0
const GW := 400                       # 地形网格分辨率（逻辑格 48 → 400 顶点）
const GH := 300
const Y_SCALE := 0.55                 # 高度夸张倍率（HD-2D 起伏感）
const CAM_OFFSET := Vector3(-0.7, 2.4, -1.0)  # 贴身近景：相机贴近玩家西北后上方（八方旅人式）
const CAM_HEIGHT_OFF := 0.5
const CAM_LERP := 0.32
const FOV := 38.0
const PIXEL_SIZE := 0.045             # 玩家贴图像素尺寸（16px → 1.24 单位高，占画面 ~1/6，八方旅人主角比例）
const LABEL_RANGE := 1.2              # 显示城名的距离（逻辑格）

const WorldMapRef = preload("res://src/core/world_map.gd")
const COLOR_FILES := ["color_winter", "color_spring", "color_summer", "color_autumn"]
const HEIGHT_FILE := "height_winter"

var _himg: Image = null
var _cimg: Image = null
var _hvals := PackedFloat32Array()
var _mat: StandardMaterial3D = null
var _season := -1
var _cam: Camera3D = null
var viewport: SubViewport = null   # 由 world_screen 注入，用于 camera_3d 绑定
var _player: Sprite3D = null
var _player_shadow: MeshInstance3D = null
var _ring: Sprite3D = null
var _arrow: Sprite3D = null
var _player_mat: StandardMaterial3D = null
var _frames: Array = []                # 8 帧像素武士贴图（R/L/D/U × 帧0/1）
var _castle_markers: Dictionary = {}   # id -> {spr, label}
var _need_season := true
var _frame := 0


func _log(msg: String) -> void:
	print("[world3d] " + msg)


func _gd() -> Node:
	return get_node("/root/GameData")


# ------------------------------------------------------------------
# 地形
# ------------------------------------------------------------------

func _load_heights() -> void:
	var f := FileAccess.open("res://assets/terrain3d/%s.png" % HEIGHT_FILE, FileAccess.READ)
	if f == null:
		_log("高度图缺失: %s" % HEIGHT_FILE)
		return
	_himg = Image.new()
	_himg.load_png_from_buffer(f.get_buffer(f.get_length()))
	_hvals.resize(GW * GH)
	for j in range(GH):
		for i in range(GW):
			var c: Color = _himg.get_pixel(int(float(i) / (GW - 1) * (_himg.get_width() - 1)), int(float(j) / (GH - 1) * (_himg.get_height() - 1)))
			_hvals[j * GW + i] = c.r * 6.5 - 0.5


func terrain_h_at(wx: float, wz: float) -> float:
	## 世界坐标 → 地形高度（与网格同式）
	var lx := wx + MAP_W / 2.0
	var ly := MAP_H / 2.0 - wz
	var i := int(clampf(lx / MAP_W * (GW - 1), 0, GW - 1))
	var j := int(clampf(ly / MAP_H * (GH - 1), 0, GH - 1))
	return _hvals[j * GW + i] * Y_SCALE


func world_of(lp: Vector2) -> Vector3:
	## 逻辑坐标 → 玩家站立位置（地形高度 + 站高）
	var h: float = terrain_h_at(lp.x - MAP_W / 2.0, -(lp.y - MAP_H / 2.0))
	return Vector3(lp.x - MAP_W / 2.0, h + 0.6, -(lp.y - MAP_H / 2.0))


func build_terrain() -> void:
	if _himg == null:
		_load_heights()
		if _himg == null:
			return
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for j in range(GH - 1):
		for i in range(GW - 1):
			var a := j * GW + i
			var b := j * GW + i + 1
			var c := (j + 1) * GW + i
			var d := (j + 1) * GW + i + 1
			var pa := _vert(a)
			var pb := _vert(b)
			var pc := _vert(c)
			var pd := _vert(d)
			var uva := Vector2(float(i) / (GW - 1), float(j) / (GH - 1))
			var uvb := Vector2(float(i + 1) / (GW - 1), float(j) / (GH - 1))
			var uvc := Vector2(float(i) / (GW - 1), float(j + 1) / (GH - 1))
			var uvd := Vector2(float(i + 1) / (GW - 1), float(j + 1) / (GH - 1))
			var n1 := (pb - pa).cross(pc - pa).normalized()
			var n2 := (pd - pb).cross(pc - pb).normalized()
			st.set_normal(n1)
			st.set_uv(uva); st.add_vertex(pa)
			st.set_uv(uvb); st.add_vertex(pb)
			st.set_uv(uvc); st.add_vertex(pc)
			st.set_normal(n2)
			st.set_uv(uvb); st.add_vertex(pb)
			st.set_uv(uvd); st.add_vertex(pd)
			st.set_uv(uvc); st.add_vertex(pc)
	_mat = StandardMaterial3D.new()
	_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_mat.roughness = 1.0
	_mat.metallic = 0.0
	_mat.cull_mode = BaseMaterial3D.CULL_DISABLED   # 双面渲染（与样板一致，避免背面剔除）
	_mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST   # HD-2D 像素感
	var mesh: ArrayMesh = st.commit()
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = _mat
	add_child(mi)
	_log("地形网格 %d 顶点" % mesh.get_faces().size())


func _vert(idx: int) -> Vector3:
	var j := idx / GW
	var i := idx % GW
	var ly := j / float(GH - 1) * MAP_H
	var lx := i / float(GW - 1) * MAP_W
	return Vector3(lx - MAP_W / 2.0, _hvals[j * GW + i] * Y_SCALE, -(ly - MAP_H / 2.0))


func _set_season(season: int) -> void:
	if _season == season and not _need_season:
		return
	_need_season = false
	_season = season
	var name: String = COLOR_FILES[season]
	var f := FileAccess.open("res://assets/terrain3d/%s.png" % name, FileAccess.READ)
	if f == null:
		_log("颜色贴图缺失: %s" % name)
		return
	_cimg = Image.new()
	_cimg.load_png_from_buffer(f.get_buffer(f.get_length()))
	if _cimg.get_format() != Image.FORMAT_RGBA8:
		_cimg.convert(Image.FORMAT_RGBA8)
	var tex := ImageTexture.create_from_image(_cimg)
	if _mat != null:
		_mat.albedo_texture = tex


# ------------------------------------------------------------------
# 环境：天空 / 太阳 / 雾 / 辉光
# ------------------------------------------------------------------

func build_environment() -> void:
	var env := Environment.new()
	# 简洁天际线背景（八方旅人式），避免程序化天空把画面洗白
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.73, 0.83, 0.90)
	env.fog_enabled = true
	env.fog_density = 0.0010
	env.fog_light_color = Color(0.76, 0.84, 0.90)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.62, 0.66, 0.62)
	env.ambient_light_energy = 2.0
	env.glow_enabled = true
	env.glow_intensity = 0.55
	env.glow_bloom = 0.08
	var world_env := WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)
	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-66, 28, 0)
	sun.light_energy = 3.0
	sun.shadow_enabled = false
	add_child(sun)
	_log("环境构建完成，子节点=%d" % get_child_count())


# ------------------------------------------------------------------
# 城标 / 城名
# ------------------------------------------------------------------

func _arrow_tex() -> ImageTexture:
	var img := Image.create(10, 10, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for y in range(10):
		var half: float = 4.5 * (1.0 - float(y) / 9.0)
		for x in range(10):
			var cx := x - 4.5
			var cy := y - 4.5
			var dist: float = absf(cx) + absf(cy) * 0.7
			if dist <= half + 0.9 and cy <= half:
				img.set_pixel(x, y, Color(1.0, 0.85, 0.25, 1.0))
	return ImageTexture.create_from_image(img)


func _ring_tex() -> ImageTexture:
	var img := Image.create(32, 32, false, Image.FORMAT_RGBA8)
	for y in range(32):
		for x in range(32):
			var dx := (x - 15.5) / 15.5
			var dy := (y - 15.5) / 15.5
			var d := sqrt(dx * dx + dy * dy)
			var a: float = 0.0
			if d < 0.55:
				a = 0.42
			elif d < 1.0:
				a = 0.42 * (1.0 - (d - 0.55) / 0.45)
			img.set_pixel(x, y, Color(1.0, 0.95, 0.72, a))
	return ImageTexture.create_from_image(img)


func _marker_tex(col: Color) -> ImageTexture:
	var img := Image.create(16, 16, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for y in range(4, 12):
		for x in range(4, 12):
			var v := Color(col.r, col.g, col.b, 1)
			img.set_pixel(x, y, v)
	# 高光边
	for x in range(4, 12):
		img.set_pixel(x, 4, col.lightened(0.35))
		img.set_pixel(x, 11, col.darkened(0.3))
	for y in range(4, 12):
		img.set_pixel(4, y, col.lightened(0.35))
		img.set_pixel(11, y, col.darkened(0.3))
	return ImageTexture.create_from_image(img)


func build_castles() -> void:
	if not _gd().has_castle_map():
		return
	var positions: Dictionary = _gd().get_castle_positions()
	var texes := {
		0: _marker_tex(Color(0.78, 0.24, 0.18)),   # 町城红
		1: _marker_tex(Color(0.88, 0.90, 0.93)),   # 军事白
		2: _marker_tex(Color(0.55, 0.85, 1.0)),    # 港蓝
	}
	for id in positions.keys():
		var cid := int(id)
		var lp: Vector2 = positions[id]
		var wx := lp.x - MAP_W / 2.0
		var wz := -(lp.y - MAP_H / 2.0)
		var h: float = maxf(terrain_h_at(wx, wz), 0.0)
		var pos := Vector3(wx, h + 0.25, wz)
		var kind := 0
		if _gd().is_port_city(cid):
			kind = 2
		elif not _gd().get_castle_has_town(cid):
			kind = 1
		var spr := Sprite3D.new()
		spr.texture = texes[kind]
		spr.position = pos
		spr.pixel_size = 0.014
		spr.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		spr.no_depth_test = false
		add_child(spr)
		# 最近城高亮标记（黄色）
		var hl := Sprite3D.new()
		hl.texture = texes[kind]
		hl.position = pos
		hl.pixel_size = 0.022
		hl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		hl.modulate = Color(1.0, 0.92, 0.35, 0.9)
		hl.visible = false
		add_child(hl)
		var lab := Label3D.new()
		lab.text = str(_gd().get_castle(cid).get("name", ""))
		lab.position = pos + Vector3(0, 0.9, 0)
		lab.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		lab.pixel_size = 0.0060
		lab.font_size = 26
		lab.modulate = Color(0.95, 0.90, 0.75, 1.0) if kind == 2 else (Color(0.99, 0.92, 0.5, 1) if kind == 0 else Color(0.9, 0.92, 0.95, 1))
		lab.outline_size = 10
		lab.outline_modulate = Color(0.08, 0.07, 0.05, 0.9)
		lab.visible = false
		add_child(lab)
		_castle_markers[cid] = {"spr": spr, "hl": hl, "label": lab, "lp": lp}


# ------------------------------------------------------------------
# 玩家（像素武士 Sprite3D）
# ------------------------------------------------------------------

func _px(img: Image, x: int, y: int, c: Color) -> void:
	if x >= 0 and x < 16 and y >= 0 and y < 20:
		img.set_pixel(x, y, c)


func _outline(img: Image) -> void:
	## 给像素贴图加一圈黑色描边，人形轮廓更清晰
	var src := img.duplicate()
	for y in range(img.get_height()):
		for x in range(img.get_width()):
			if src.get_pixel(x, y).a < 0.1:
				var hit := false
				for dy in range(-1, 2):
					for dx in range(-1, 2):
						var nx := x + dx
						var ny := y + dy
						if nx >= 0 and nx < img.get_width() and ny >= 0 and ny < img.get_height() and src.get_pixel(nx, ny).a > 0.5:
							hit = true
							break
					if hit:
						break
				if hit:
					img.set_pixel(x, y, Color(0.05, 0.04, 0.03, 0.92))


func _samurai_tex(face: Vector2, frame: int) -> ImageTexture:
	var img := Image.create(16, 20, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	var skin := Color(0.92, 0.78, 0.62)
	var hair := Color(0.16, 0.13, 0.11)
	var robe := Color(0.42, 0.55, 0.78)
	var belt := Color(1.0, 0.97, 0.90)
	var pant := Color(0.24, 0.22, 0.20)
	var accent := Color(0.95, 0.45, 0.32)
	var flip := face.x < -0.1
	var horiz: bool = abs(face.x) > abs(face.y)
	if horiz:
		# 侧面
		for y in range(6):
			for x in range(8):
				_px(img, x + (3 if flip else 5), y, skin)
		for y in range(4):
			for x in range(4):
				_px(img, x + (2 if flip else 4), y - 3, hair)
		for y in range(8):
			for x in range(10):
				_px(img, x + (2 if flip else 3), y + 6, robe)
		for y in range(2):
			for x in range(11):
				_px(img, x + (1 if flip else 2), y + 7, belt)
		if frame == 0:
			for y in range(5):
				for x in range(3):
					_px(img, x + (3 if flip else 5), y + 14, pant)
				for x in range(3):
					_px(img, x + (7 if flip else 9), y + 14, pant)
		else:
			for y in range(5):
				for x in range(3):
					_px(img, x + (1 if flip else 3), y + 14, pant)
				for x in range(3):
					_px(img, x + (9 if flip else 11), y + 14, pant)
		_outline(img)
		return ImageTexture.create_from_image(img)
	var back: bool = face.y < -0.1
	for y in range(7):
		for x in range(8):
			_px(img, x + 4, y, hair if back else skin)
	for y in range(4):
		for x in range(6):
			_px(img, x + 5, y - 3, hair)
	if not back:
		for y in range(3):
			for x in range(3):
				_px(img, x + 5, y + 1, skin)
	for y in range(9):
		for x in range(12):
			_px(img, x + 2, y + 7, robe)
	for y in range(2):
		for x in range(14):
			_px(img, x + 1, y + 8, belt)
	for y in range(2):
		for x in range(6):
			_px(img, x + 5, y + 12, accent)
	# 面部细节：眼睛（正面）
	if not back:
		_px(img, 6, 2, Color(0.10, 0.08, 0.06, 1))
		_px(img, 9, 2, Color(0.10, 0.08, 0.06, 1))
	# 和服领口（白 V 形）
	_px(img, 6, 7, belt)
	_px(img, 7, 7, belt)
	_px(img, 8, 7, belt)
	_px(img, 9, 7, belt)
	# 左侧佩刀（深色细条 + 鞘尾）
	for y in range(3):
		_px(img, 1, 10 + y, Color(0.14, 0.12, 0.10, 1))
	if frame == 0:
		for y in range(5):
			for x in range(4):
				_px(img, x + 3, y + 16, pant)
			for x in range(4):
				_px(img, x + 9, y + 16, pant)
	else:
		for y in range(5):
			for x in range(4):
				_px(img, x + 1, y + 16, pant)
			for x in range(4):
				_px(img, x + 11, y + 16, pant)
	return ImageTexture.create_from_image(img)


func build_player() -> void:
	_frames = []
	var faces := [Vector2.RIGHT, Vector2.LEFT, Vector2.DOWN, Vector2.UP]
	for fi in range(4):
		for f in range(2):
			_frames.append(_samurai_tex(faces[fi], f))
	_player = Sprite3D.new()
	_player.texture = _frames[2]
	_player.pixel_size = PIXEL_SIZE
	_player.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_player.position = world_of(Vector2(24, 24))
	add_child(_player)
	# 脚下阴影
	var sh_mat := StandardMaterial3D.new()
	sh_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	sh_mat.albedo_color = Color(0, 0, 0, 0.32)
	sh_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	sh_mat.roughness = 1.0
	var sh_mesh := QuadMesh.new()
	sh_mesh.size = Vector2(0.9, 0.45)
	_player_shadow = MeshInstance3D.new()
	_player_shadow.mesh = sh_mesh
	_player_shadow.material_override = sh_mat
	add_child(_player_shadow)


# ------------------------------------------------------------------
# 相机
# ------------------------------------------------------------------

func build_camera() -> void:
	_cam = Camera3D.new()
	_cam.current = true
	_cam.fov = FOV
	_cam.near = 0.1
	_cam.far = 300.0
	_cam.position = Vector3(0, 8, -8)
	add_child(_cam)


# ------------------------------------------------------------------
# 暗角（2D 叠加在 3D 视口内）
# ------------------------------------------------------------------

func build_vignette() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var tex := Image.create(320, 200, false, Image.FORMAT_RGBA8)
	for y in range(200):
		for x in range(320):
			var nx := (x - 160) / 160.0
			var ny := (y - 100) / 100.0
			var d := sqrt(nx * nx + ny * ny)
			var a := clampf((d - 0.82) * 0.6, 0.0, 0.30)
			tex.set_pixel(x, y, Color(0.02, 0.03, 0.05, a))
	var tex_rect := TextureRect.new()
	tex_rect.texture = ImageTexture.create_from_image(tex)
	tex_rect.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	tex_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(tex_rect)


# ------------------------------------------------------------------
# 2D 叠加接口（world_screen 在 _draw 里画玩家，保证可见）
# ------------------------------------------------------------------

func player_screen_pos() -> Vector2:
	if viewport == null or viewport.get_camera_3d() == null or _player == null:
		return Vector2(-9999, -9999)
	return viewport.get_camera_3d().unproject_position(_player.global_position)


func player_tex() -> Texture2D:
	return _player.texture if _player != null else null


# ------------------------------------------------------------------
# 每帧同步（由 world_screen 调用）
# ------------------------------------------------------------------

func sync(player_lp: Vector2, face: Vector2, walk_frame: int, season: int) -> void:
	_frame += 1
	if _frame == 2 or _frame == 50 or _frame == 70:
		print("[world3d] sync frame=%d player_lp=%s cam=%s cam_visible=%s" % [_frame, player_lp, _cam.position, is_instance_valid(_cam)])
	_set_season(season)
	# 玩家位置（平滑插值由 world_screen 的 _draw_pos 提供）
	var wp := world_of(player_lp)
	_player.position = wp
	_player_shadow.position = wp + Vector3(0, 0.02, 0)
	if _ring != null:
		_ring.position = wp + Vector3(0, 0.05, 0)
	if _arrow != null:
		_arrow.position = wp + Vector3(0, 1.15, 0)
	var fi := 0
	if abs(face.x) > abs(face.y):
		fi = 0 if face.x > 0 else 1
	else:
		fi = 2 if face.y > 0 else 3
	var ptex: Texture2D = _frames[fi * 2 + (walk_frame if walk_frame > 0 else 0)]
	_player.texture = ptex
	# 玩家面朝东南（内陆），相机从西北后上方贴身跟随，看向玩家前方地面
	_player.rotation.y = -PI / 4.0
	var cam_target := wp + CAM_OFFSET
	cam_target.y = maxf(terrain_h_at(cam_target.x, cam_target.z) + CAM_HEIGHT_OFF, wp.y + 2.4)
	if _frame <= 3:
		_cam.position = cam_target   # 开局/初始直接到位，避免长距离拖影
	else:
		_cam.position = _cam.position.lerp(cam_target, CAM_LERP)
	_cam.look_at(wp + Vector3(0.35, 0.65, 0.35), Vector3.UP)
	# 近处城名显示 + 最近城高亮
	var nearest_id: int = WorldMapRef.nearest(player_lp, _gd().get_castle_positions()) if _gd().has_castle_map() else -1
	for cid in _castle_markers.keys():
		var m: Dictionary = _castle_markers[cid]
		var l: Label3D = m["label"]
		var d: float = player_lp.distance_to(m["lp"] as Vector2)
		l.visible = d < LABEL_RANGE
		var s3: Sprite3D = m["hl"]
		s3.visible = (cid == nearest_id)


func setup() -> void:
	_load_heights()
	build_terrain()
	build_environment()
	build_castles()
	build_player()
	build_camera()
	build_vignette()
	_log("setup 完成，总子节点=%d" % get_child_count())
