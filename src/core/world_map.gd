extends RefCounted
## world_map.gd — 大地图纯逻辑（投影 / 最近城 / 坐标夹紧 / 移动）
##
## 不依赖 Node/UI，可无头跑（tools/_test_world.gd）+ Python 等价镜像验证
## （scripts/_test_world_mirror.py）。坐标源 = data/castle_map.json（聚类近似，
## 非原版固定坐标 —— 见 gen_castle_map.py 标注）。
##
## ⚠️ 不用 class_name（--script 无头模式不建全局类缓存），跨文件一律 preload：
##    const WorldMapRef = preload("res://src/core/world_map.gd")

const STEP := 36.0          # 主角每次移动的步长（逻辑单位）
const ENTER_DIST := 90.0    # 进入城的距离阈值（逻辑单位）


## 逻辑坐标 → 屏幕坐标：在 view 矩形内等比 fit + 居中
static func project(pos: Vector2, map_w: float, map_h: float, view: Rect2) -> Vector2:
	var s: float = min(view.size.x / map_w, view.size.y / map_h)
	var draw_w: float = map_w * s
	var draw_h: float = map_h * s
	var off := view.position + Vector2((view.size.x - draw_w), (view.size.y - draw_h)) * 0.5
	return off + pos * s


## 屏幕坐标 → 逻辑坐标（project 的逆）
static func unproject(screen: Vector2, map_w: float, map_h: float, view: Rect2) -> Vector2:
	var s: float = min(view.size.x / map_w, view.size.y / map_h)
	var draw_w: float = map_w * s
	var draw_h: float = map_h * s
	var off := view.position + Vector2((view.size.x - draw_w), (view.size.y - draw_h)) * 0.5
	return (screen - off) / s


## 夹紧到地图范围 [0,map_w]×[0,map_h]
static func clamp_pos(pos: Vector2, map_w: float, map_h: float) -> Vector2:
	return Vector2(clamp(pos.x, 0.0, map_w), clamp(pos.y, 0.0, map_h))


## 最近城：positions = {id: Vector2}（来自 GameData.get_castle_positions）
## 返回最近城 id；positions 为空或越界时返回 -1
static func nearest(pos: Vector2, positions: Dictionary) -> int:
	var best := -1
	var best_d := INF
	for id in positions.keys():
		var d := pos.distance_to(positions[id] as Vector2)
		if d < best_d:
			best_d = d
			best = int(id)
	return best


## 移动并返回夹紧后的新位置（dx,dy ∈ {-1,0,1}）
static func step(pos: Vector2, dx: float, dy: float, map_w: float, map_h: float) -> Vector2:
	return clamp_pos(pos + Vector2(dx, dy) * STEP, map_w, map_h)


## 是否在进城阈值内（供 UI 高亮/提示）
static func within_enter(pos: Vector2, city_pos: Vector2) -> bool:
	return pos.distance_to(city_pos) <= ENTER_DIST
