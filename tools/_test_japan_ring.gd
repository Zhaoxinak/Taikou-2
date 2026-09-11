extends SceneTree
## 检查 japan_map.gd 每个海岸线环能否三角剖分（定位 draw_colored_polygon 失败源）

const JapanMap = preload("res://src/ui/japan_map.gd")

func _init() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)

func _run() -> void:
	var polys: Array = JapanMap.polygons()
	for i in range(polys.size()):
		var pts := polys[i] as PackedVector2Array
		var tri := Geometry2D.triangulate_polygon(pts)
		if tri.is_empty():
			print("RING %d 剖分失败，点数=%d" % [i, pts.size()])
			# 检查是否自交：逐段找交点
			for a in range(pts.size()):
				var a1 := pts[a]
				var a2 := pts[(a + 1) % pts.size()]
				for b in range(a + 1, pts.size()):
					if b == (a + 1) % pts.size() or (a == 0 and b == pts.size() - 1):
						continue
					var b1 := pts[b]
					var b2 := pts[(b + 1) % pts.size()]
					var hit: Variant = Geometry2D.segment_intersects_segment(a1, a2, b1, b2)
					if hit != null:
						print("  自交: 边 %d(%s→%s) × 边 %d(%s→%s)" % [a, a1, a2, b, b1, b2])
		else:
			print("RING %d 剖分 OK，点数=%d，三角形=%d" % [i, pts.size(), tri.size() / 3])
	quit(0)
