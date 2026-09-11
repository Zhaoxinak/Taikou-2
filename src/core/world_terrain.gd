extends RefCounted
## world_terrain.gd — 大地图地形（太阁5 手绘风数据源）
##
## 低分辨率 256×192 高度图 + 类型图（海/沙滩/草地/森林/山/城下町），
## 由海岸线环射线法判定海陆、value-noise 生成地形起伏（山/丘陵/平原），
## 城下町（町城/港町）周边为城镇。world_screen 据此渲染**平滑渐变**底图
## （双线性放大，无格子感，呈现太阁5 那种黄绿过渡的手绘战略图）。
##
## ⚠️ 不用 class_name（--script 无头模式不建全局类缓存），跨文件 preload。

const JapanMap = preload("res://src/ui/japan_map.gd")

const RES_W := 256
const RES_H := 192
const MAP_W := 48.0
const MAP_H := 36.0
const CELL := MAP_W / RES_W      # 每单元 0.1875 逻辑单位

const SEA := 0
const BEACH := 1
const GRASS := 2
const FOREST := 3
const MOUNT := 4
const TOWN := 5

static var _type := PackedByteArray()
static var _height := PackedFloat32Array()
static var _done := false


static func _hash01(ix: int, iy: int, seedv: int) -> float:
	var h := ix * 374761393 + iy * 668265263 + seedv * 69069
	h = (h ^ (h >> 13)) * 1274126177
	return float(h & 0xffff) / 65535.0


## value noise（双线性平滑）
static func _vnoise(x: float, y: float, seedv: int) -> float:
	var ix := int(floor(x))
	var iy := int(floor(y))
	var fx: float = x - floor(x)
	var fy: float = y - floor(y)
	var a: float = _hash01(ix, iy, seedv)
	var b: float = _hash01(ix + 1, iy, seedv)
	var c: float = _hash01(ix, iy + 1, seedv)
	var d: float = _hash01(ix + 1, iy + 1, seedv)
	var ux: float = fx * fx * (3.0 - 2.0 * fx)
	var uy: float = fy * fy * (3.0 - 2.0 * fy)
	return a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy


## 分形噪声（多 octave）
static func _fbm(x: float, y: float, seedv: int, oct: int) -> float:
	var v := 0.0
	var amp := 0.55
	var f := 1.0
	var tot := 0.0
	for i in range(oct):
		v += _vnoise(x * f, y * f, seedv + i * 101) * amp
		tot += amp
		amp *= 0.5
		f *= 2.0
	return v / tot


## 射线法点在多边形内
static func _in_poly(px: float, py: float, pts: PackedVector2Array) -> bool:
	var inside := false
	var n := pts.size()
	var j := n - 1
	for i in range(n):
		var xi := pts[i].x
		var yi := pts[i].y
		var xj := pts[j].x
		var yj := pts[j].y
		if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
			inside = not inside
		j = i
	return inside


## 生成（只跑一次）
static func ensure() -> void:
	if _done:
		return
	_done = true
	_type.resize(RES_W * RES_H)
	_height.resize(RES_W * RES_H)
	var polys: Array = JapanMap.polygons()
	# 1. 海陆
	var land := PackedByteArray()
	land.resize(RES_W * RES_H)
	for y in range(RES_H):
		for x in range(RES_W):
			var lx := (x + 0.5) * CELL
			var ly := (y + 0.5) * CELL
			var on := false
			for p in polys:
				if _in_poly(lx, ly, p):
					on = true
					break
			land[y * RES_W + x] = 1 if on else 0
	# 2. 名山系 + 城下町
	var mpts := PackedVector2Array()
	for m in JapanMap.mountains():
		mpts.append(JapanMap.mountain_pos(m))
	var towns := PackedVector2Array()
	var pos: Dictionary = GameData.get_castle_positions()
	for id in pos.keys():
		var cid := int(id)
		if GameData.get_castle_has_town(cid) or GameData.is_port_city(cid):
			towns.append(pos[id])
	# 3. 高度 + 类型
	for y in range(RES_H):
		for x in range(RES_W):
			var idx := y * RES_W + x
			if land[idx] == 0:
				_type[idx] = SEA
				_height[idx] = 0.0
				continue
			var lx := (x + 0.5) * CELL
			var ly := (y + 0.5) * CELL
			var p := Vector2(lx, ly)
			# 高度：fbm 起伏 + 名山隆起
			var hgt := _fbm(lx * 0.35, ly * 0.35, 31, 3)
			for m in mpts:
				var d: float = p.distance_to(m)
				if d < 1.8:
					hgt = maxf(hgt, 0.70 - d * 0.16)
			_height[idx] = hgt
			# 城下町
			var is_town := false
			for t in towns:
				if p.distance_to(t) < 0.55:
					is_town = true
					break
			if is_town:
				_type[idx] = TOWN
				continue
			# 沙滩（8 邻域有海）
			var near_sea := false
			for dy in range(-1, 2):
				for dx in range(-1, 2):
					if dx == 0 and dy == 0:
						continue
					var nx := x + dx
					var ny := y + dy
					if nx < 0 or ny < 0 or nx >= RES_W or ny >= RES_H:
						continue
					if land[ny * RES_W + nx] == 0:
						near_sea = true
						break
				if near_sea:
					break
			if near_sea:
				_type[idx] = BEACH
				continue
			# 山（高地形 + 名山区）
			if hgt > 0.62:
				_type[idx] = MOUNT
				continue
			# 森林（湿润中海拔）
			if _fbm(lx * 0.5 + 40.0, ly * 0.5 + 17.0, 7, 2) > 0.53 and hgt < 0.50:
				_type[idx] = FOREST
				continue
			_type[idx] = GRASS


static func type_at(x: int, y: int) -> int:
	ensure()
	if x < 0 or y < 0 or x >= RES_W or y >= RES_H:
		return SEA
	return _type[y * RES_W + x]


static func height_at(x: int, y: int) -> float:
	ensure()
	if x < 0 or y < 0 or x >= RES_W or y >= RES_H:
		return 0.0
	return _height[y * RES_W + x]
