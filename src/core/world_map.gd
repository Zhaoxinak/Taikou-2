extends RefCounted
## world_map.gd — 大地图纯逻辑（投影 / 最近城 / 坐标夹紧 / 逐格移动 / 寻路）
##
## 不依赖 Node/UI，可无头跑（tools/_test_world.gd）+ Python 等价镜像验证。
## 坐标源 = data/castle_map.json（200 城史实经纬度投影，见 gen_castle_map.py）。
##
## ⚠️ 不用 class_name（--script 无头模式不建全局类缓存），跨文件一律 preload：
##    const WorldMapRef = preload("res://src/core/world_map.gd")

const STEP := 1.0           # 主角每次移动的步长（逻辑单位 = 1 地图格；复刻原版逐格移动）
const ENTER_DIST := 1.6     # 进入城的距离阈值（逻辑单位；原版：走到城格相邻即询问进入）
const MOVE_DAYS_PER_CELL := 1.0  # 移动 1 格消耗的天数（复刻原版：野外移动推进时间）


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


## 逐格移动一步（dx,dy ∈ {-1,0,1}），clamp 后返回新位置。
## 复刻原版：大地图按 1 格为基本移动单位（原版十字键/点击均按格推进）。
static func step(pos: Vector2, dx: float, dy: float, map_w: float, map_h: float) -> Vector2:
	return clamp_pos(pos + Vector2(dx, dy) * STEP, map_w, map_h)


## 朝目标位置走一步（步长 = STEP），返回新位置。
## 自动移动（原版「点击地图/指定城町」）由 UI 每帧调用直到到达。
static func move_towards(pos: Vector2, target: Vector2, map_w: float, map_h: float) -> Vector2:
	if pos.distance_to(target) <= STEP * 0.5:
		return clamp_pos(target, map_w, map_h)
	var dir := (target - pos).normalized()
	return clamp_pos(pos + dir * STEP, map_w, map_h)


## 是否在进城阈值内（供 UI 高亮/提示）
static func within_enter(pos: Vector2, city_pos: Vector2) -> bool:
	return pos.distance_to(city_pos) <= ENTER_DIST


## 从 from 到 to 的直线格点路径（含端点，步长 STEP）。
## 用于自动移动/行军距离估算；返回 PackedVector2Array。
static func path_cells(from: Vector2, to: Vector2, map_w: float, map_h: float) -> PackedVector2Array:
	var out := PackedVector2Array([from])
	var dist := from.distance_to(to)
	if dist < 0.001:
		return out
	var steps := maxi(1, int(ceil(dist / STEP)))
	for i in range(1, steps + 1):
		out.append(from.lerp(to, float(i) / float(steps)))
	out[out.size() - 1] = clamp_pos(to, map_w, map_h)
	return out


## 两点间的移动天数（复刻原版：野外移动按格计日，向上取整）
static func travel_days(from: Vector2, to: Vector2) -> int:
	return maxi(1, int(ceil(from.distance_to(to) / STEP * MOVE_DAYS_PER_CELL)))
