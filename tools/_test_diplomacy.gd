# _test_diplomacy.gd — M7 外交系统无头校验（extends SceneTree）
#
# 复刻结构：src/core/diplomacy.gd
# 比对参考实现：scripts/diplomacy2_ref.py (183/183) / scripts/diplomacy3_ref.py (2394/2394)
#              scripts/diplomacy_spec.json（续95）
#
# 覆盖：三角索引全 1176 覆盖唯一（并对 spec 的 asm 写法证伪）/ 位域隔离 /
#   主从 2<->3 有向镜像 / 目标国筛选 / 关系初始化与灭亡恶化 / 友好·高压成功变更 /
#   diff·min_trunc / mission_level·intel_merit·mission_merit / 名称表 / GameState 接线。
#
# 运行：Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_diplomacy.gd

extends SceneTree

const DiplomacyRef = preload("res://src/core/diplomacy.gd")

var _fails: int = 0


func check(cond: bool, msg: String) -> void:
	if cond:
		print("[ok] " + msg)
	else:
		push_error("[FAIL] " + msg)
		_fails += 1


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)


func _run() -> void:
	var d: RefCounted = DiplomacyRef.new()
	var gs = root.get_node("/root/GameState")

	# ---- [1] 三角索引：全 1176 覆盖且唯一（并对 spec 的 asm 写法证伪）----
	var seen := {}
	var dup := false
	for i in range(49):
		for j in range(i + 1, 49):
			var t : int = d.tri_index(i, j)
			if seen.has(t):
				dup = true
			seen[t] = true
	check(seen.size() == 1176 and not dup, "tri_index 49 国对 → 1176 个唯一索引")
	var mn : int = 999999
	var mx : int = -1
	for k in seen.keys():
		if k < mn:
			mn = k
		if k > mx:
			mx = k
	check(mn == 0 and mx == 1175, "tri_index 范围恰为 0..1175（=矩阵 1176B）")
	check(d.tri_index(0, 1) == 0, "tri_index(0,1) = 0")
	check(d.tri_index(0, 48) == 47, "tri_index(0,48) = 47")
	check(d.tri_index(47, 48) == 1175, "tri_index(47,48) = 1175")
	# 证伪：spec 的 asm 改写 (j + 48*i - i*(i-1)/2) - 1 会溢出到 1222
	check(((48 + 48 * 47 - 47 * 46 / 2) - 1) > 1175,
		"证伪：spec asm 改写 tri 会溢出 1176（故以 equivalent 为准）")

	# ---- [2] rel_offset 合法性与对称性 ----
	check(d.rel_offset(3, 3) == -1, "rel_offset(i==j) = -1（原版 NULL）")
	check(d.rel_offset(49, 0) == -1 and d.rel_offset(0, 49) == -1, "rel_offset 越界 = -1")
	check(d.rel_offset(-1, 0) == -1, "rel_offset 负 = -1")
	check(d.rel_offset(5, 3) == d.rel_offset(3, 5), "rel_offset 对称（i>j 自动交换）")

	# ---- [3] 外交関係 bit0-2 存取与位域隔离 ----
	check(d.get_diplomacy(1, 2) == 0, "初始外交関係 = 0(盟友)")
	d.set_diplomacy(1, 2, 5)
	check(d.get_diplomacy(1, 2) == 5, "set/get_diplomacy 往返")
	check(d.get_diplomacy(2, 1) == 5, "外交関係无向（反向读同值）")
	d.set_master_vassal(1, 2, 3)
	d.set_diplomacy(1, 2, 6)
	check(d.get_master_vassal(1, 2) == 3, "set_diplomacy 不破坏主从位域")
	d.set_master_vassal(1, 2, 1)
	check(d.get_diplomacy(1, 2) == 6, "set_master_vassal 不破坏外交位域")

	# ---- [4] 主从関係 bit3-4：有向 2<->3 镜像 ----
	var d2: RefCounted = DiplomacyRef.new()
	d2.set_master_vassal(5, 3, DiplomacyRef.MV_DOMINION)
	check(d2.get_master_vassal(5, 3) == 3, "(5,3) 读到 支配(3)")
	check(d2.get_master_vassal(3, 5) == 2, "(3,5) 读到 从属(2) —— 有向语义")
	check(d2.mv_name(3, 5) == "从属" and d2.mv_name(5, 3) == "支配", "mv_name 有向读取正确")
	d2.set_master_vassal(7, 2, DiplomacyRef.MV_ALLY)
	check(d2.get_master_vassal(7, 2) == 1 and d2.get_master_vassal(2, 7) == 1,
		"同盟(1) 不参与镜像（双向同值）")
	d2.set_master_vassal(9, 4, DiplomacyRef.MV_NONE)
	check(d2.get_master_vassal(9, 4) == 0 and d2.get_master_vassal(4, 9) == 0,
		"空白(0) 不参与镜像")

	# ---- [5] 目标国可派筛选 0x4c4270（按主从関係过滤，非外交）----
	check(d.can_dispatch(0, 0) and d.can_dispatch(0, 1), "高压外交：接受 空白/同盟")
	check(not d.can_dispatch(0, 2) and not d.can_dispatch(0, 3), "高压外交：拒绝 从属/支配")
	check(d.can_dispatch(1, 0), "友好外交：只接受 空白")
	check(not d.can_dispatch(1, 1) and not d.can_dispatch(1, 3), "友好外交：拒绝 同盟/支配")
	check(d.can_dispatch(2, 3) and d.can_dispatch(2, 2), "收集情报：无条件接受")
	check(not d.can_dispatch(3, 0), "未知 mode = false")

	# ---- [6] 关系初始化 0x4c2e4e ----
	var d3: RefCounted = DiplomacyRef.new()
	d3.init_relations(0, [0, 1, 2, 3, 4], 3)
	check(d3.get_diplomacy(0, 1) == 3 and d3.get_diplomacy(0, 2) == 3, "初始化 → 普通(3)")
	check(d3.get_diplomacy(0, 3) == 6, "与 foe → 绝交(6)")
	check(d3.get_diplomacy(0, 4) == 3, "其余 → 普通(3)")
	check(d3.get_master_vassal(0, 1) == 0 and d3.get_master_vassal(0, 3) == 0, "初始化 → 主从空白(0)")
	check(d3.dipl_name(0, 1) == "普通" and d3.dipl_name(0, 3) == "绝交", "dipl_name 正确")

	# ---- [7] 势力灭亡恶化一级 0x4c7734 ----
	var d4: RefCounted = DiplomacyRef.new()
	d4.init_relations(1, [0, 1, 2, 3, 24])
	var changed: Array = d4.worsen_on_conquest(1, [0, 2, 3, 24], [24])
	check(changed.size() == 3, "灭亡恶化：3 国受影响（跳过 #24）")
	check(d4.get_diplomacy(0, 1) == 4, "关系 普通(3) → 敌视(4) 恶化一级")
	check(d4.get_diplomacy(24, 1) == 3, "国 #24 被跳过，关系不变")
	# 主从非空白 → 跳过
	d4.set_master_vassal(2, 1, DiplomacyRef.MV_ALLY)
	d4.worsen_on_conquest(1, [0, 2], [24])
	var before : int = d4.get_diplomacy(2, 1)
	d4.worsen_on_conquest(1, [2], [24])
	check(d4.get_diplomacy(2, 1) == before, "主从非空白 → 不恶化")
	# 已交战(7) → 跳过
	d4.set_diplomacy(3, 1, 7)
	d4.worsen_on_conquest(1, [3], [24])
	check(d4.get_diplomacy(3, 1) == 7, "已交战(7) → 不再恶化（上限）")

	# ---- [8] 友好/高压外交成功变更 ----
	var d5: RefCounted = DiplomacyRef.new()
	check(d5.friendly_success(0, 6, 8) == 1, "友好 type0 → lv=diff(1,0)=1")
	check(d5.get_master_vassal(6, 8) == 1, "友好成功 → 主从=同盟(1)")
	check(d5.dipl_name(6, 8) == "亲密", "友好 type0 → 亲密")
	check(d5.friendly_success(2, 6, 9) == 0, "友好 type2 → lv=0")
	check(d5.friendly_success(3, 6, 9) == 2, "友好 type3 → lv=2")
	check(d5.pressure_success(0, 6, 10) == 1, "高压 type0 → lv=1")
	check(d5.get_master_vassal(6, 10) == 3, "高压成功 → 主从=支配(3)")
	check(d5.pressure_success(3, 6, 11) == 2, "高压 type3 → lv=2")
	check(DiplomacyRef.pressure_succeeds(), "高压外交恒成功（0x47b5f0 无随机失败）")

	# ---- [9] 通用数学 ----
	check(DiplomacyRef.diff(5, 2) == 3, "diff(5,2)=3")
	check(DiplomacyRef.diff(1, 2) == 0, "diff(1,2)=0（饱和减）")
	check(DiplomacyRef.diff(3, 3) == 0, "diff(3,3)=0")
	check(DiplomacyRef.min_trunc(10, 20, 100) == 30, "min_trunc(10,20,100)=30")
	check(DiplomacyRef.min_trunc(200, 100, 150) == 150, "min_trunc 截断后取小")

	# ---- [10] 使者功勋结算 ----
	check(DiplomacyRef.mission_level(0, 0) == 1, "mission_level(0,0) = 1")
	check(DiplomacyRef.mission_level(3, 100) == 7, "mission_level 封顶 7（3+5+1=9→7）")
	check(DiplomacyRef.mission_level(2, 40) == 5, "mission_level(2,40) = 2+2+1 = 5")
	check(DiplomacyRef.mission_level(7, 0) == 4, "mission_level(7,0)：7&3=3 → 4（除数20非10）")
	check(DiplomacyRef.intel_merit(0, 0, 5) == 130, "情报功勋 5城·lv1 = 5*6+100 = 130")
	check(DiplomacyRef.intel_merit(3, 100, 10) == 220, "情报功勋 10城·lv7 = 10*12+100 = 220")
	check(d.mission_merit(2, 100) == 250, "卖出军粮 val100 → 250")
	check(d.mission_merit(3, 100) == 250, "购入军粮 val100 → 250")
	check(d.mission_merit(4, 50) == 300, "购入军马 val50 → 300")
	check(d.mission_merit(9) == 600, "友好外交 → 600")
	check(d.mission_merit(10) == 1000, "高压外交 → 1000")
	check(d.mission_merit(11, 0, 0, 0, 0, false) == 800, "朝廷工作无官位 → 800")
	check(d.mission_merit(11, 0, 0, 0, 0, true) == 1000, "朝廷工作得官位 → 1000")
	check(d.mission_merit(12, 0, 5) == 130, "收集情报 5城 → 130")
	check(d.mission_merit(99) == 0, "未知工作码 → 0")

	# ---- [11] 名称表 ----
	check(DiplomacyRef.DIPL_NAMES.size() == 8 and DiplomacyRef.MV_NAMES.size() == 4, "名称表 8+4")
	check(DiplomacyRef.DIPL_NAMES == ["盟友", "亲密", "良好", "普通", "敌视", "险恶", "绝交", "交战"],
		"外交 8 级名称")
	check(DiplomacyRef.MV_NAMES == ["", "同盟", "从属", "支配"], "主从 4 级名称")
	check(d.work_name(9) == "友好外交" and d.work_name(12) == "收集情报", "工作名映射")
	check(d.work_name(99) == "", "未知工作码 → 空名")

	# ---- [12] GameState 接线 ----
	gs.diplomacy.reset()
	gs.diplomacy.set_diplomacy(10, 20, 7)
	check(gs.diplomacy.get_diplomacy(10, 20) == 7, "GameState.diplomacy 可用")
	check(gs.diplomacy.dipl_name(10, 20) == "交战", "GameState.diplomacy 名称可用")

	# ---- 收尾 ----
	print("")
	if _fails == 0:
		print("[DIPLOMACY PASS] 全部断言通过 ✅")
		quit(0)
	else:
		push_error("[DIPLOMACY FAIL] %d 项断言失败 ❌" % _fails)
		quit(1)
