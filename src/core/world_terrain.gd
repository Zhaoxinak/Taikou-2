extends RefCounted
## world_terrain.gd — 大地图格子地形（原版风：海 / 沙滩 / 草地 / 森林 / 山 / 城镇）
##
## 全图 GRID_W×GRID_H 格（每格 CELL=0.5 逻辑单位），由海岸线环 + 山系 + 城下町数据
## 一次性生成并缓存（懒初始化）。镜头聚焦后逐格绘制可见区域，呈现原版那种
## 像素格地形质感（草地有草簇、森林有树冠、山有雪顶三角、城镇有町屋与城郭）。
##
## ⚠️ 不用 class_name（--script 无头模式不建全局类缓存），跨文件 preload。

const JapanMap = preload("res://src/ui/japan_map.gd")

const GRID_W := 96
const GRID_H := 72
const CELL := 0.5          # 每格 = 0.5 逻辑单位（原版大地图一格）

# 地形类型
const SEA := 0
const BEACH := 1
const GRASS := 2
const FOREST := 3
const MOUNT := 4
const TOWN := 5

static var _data := PackedByteArray()
static var _done := false


## 确定性散列（格坐标 → 伪随机）
static func _hash2(x: int, y: int, seedv: int) -> int:
	var h := x * 374761393 + y * 668265263 + seedv * 69069
	h = (h ^ (h >> 13)) * 1274126177
	return h & 0x7fffffff


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


## 生成地形（只跑一次）
static func ensure() -> void:
	if _done:
		return
	_done = true
	_data.resize(GRID_W * GRID_H)
	var polys: Array = JapanMap.polygons()
	# 1. 海陆判定
	var land := PackedByteArray()
	land.resize(GRID_W * GRID_H)
	for gy in range(GRID_H):
		for gx in range(GRID_W):
			var cx := (gx + 0.5) * CELL
			var cy := (gy + 0.5) * CELL
			var on := false
			for p in polys:
				if _in_poly(cx, cy, p):
					on = true
					break
			land[gy * GRID_W + gx] = 1 if on else 0
	# 2. 山系逻辑坐标
	var mpts := PackedVector2Array()
	for m in JapanMap.mountains():
		mpts.append(JapanMap.mountain_pos(m))
	# 3. 城下町（町城 + 港町）坐标
	var towns := PackedVector2Array()
	var pos: Dictionary = GameData.get_castle_positions()
	for id in pos.keys():
		var cid := int(id)
		if GameData.get_castle_has_town(cid) or GameData.is_port_city(cid):
			towns.append(pos[id])
	# 4. 逐格填充（优先级：城镇 > 沙滩 > 山 > 森林 > 草地）
	for gy in range(GRID_H):
		for gx in range(GRID_W):
			var idx := gy * GRID_W + gx
			if land[idx] == 0:
				_data[idx] = SEA
				continue
			var cx := (gx + 0.5) * CELL
			var cy := (gy + 0.5) * CELL
			var p := Vector2(cx, cy)
			# 城下町（町城/港町周边 1 格余量）
			var is_town := false
			for t in towns:
				if p.distance_to(t) < 0.62:
					is_town = true
					break
			if is_town:
				_data[idx] = TOWN
				continue
			# 沙滩：8 邻域有海
			var near_sea := false
			for dy in range(-1, 2):
				for dx in range(-1, 2):
					if dx == 0 and dy == 0:
						continue
					var nx := gx + dx
					var ny := gy + dy
					if nx < 0 or ny < 0 or nx >= GRID_W or ny >= GRID_H:
						continue
					if land[ny * GRID_W + nx] == 0:
						near_sea = true
						break
				if near_sea:
					break
			if near_sea:
				_data[idx] = BEACH
				continue
			# 山：名山系范围 + 内陆丘陵噪声
			var is_mount := false
			for m in mpts:
				if p.distance_to(m) < 1.35:
					is_mount = true
					break
			if is_mount or _hash2(gx, gy, 7) % 100 < 7:
				_data[idx] = MOUNT
				continue
			# 森林
			if _hash2(gx, gy, 11) % 100 < 22:
				_data[idx] = FOREST
				continue
			_data[idx] = GRASS


## 取格地形（越界=海）
static func at(gx: int, gy: int) -> int:
	ensure()
	if gx < 0 or gy < 0 or gx >= GRID_W or gy >= GRID_H:
		return SEA
	return _data[gy * GRID_W + gx]
