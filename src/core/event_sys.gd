extends RefCounted
## EventSys — 事件解释器纯逻辑核心（MSGX 事件派发 / 条件判定 / 每 tick 状态机）
##
## 权威（按逆向证据层级）：
##   scripts/event_handlers_full_ref.py  18 事件 id → 49 handler 地址（含 id29 纠正、0x490c0 笔误剔除）
##   scripts/event_predicates_ref.py     49 handler → kind/ids/tables/gate/semantics/conf（续107/108）
##   scripts/event_cond_ref.py           0x4e82c0(op13/14) + 0x4e7e10(op10) 条件求值（可测纯函数）
##   scripts/event_dispatch_tables_ref.py 0x44d950(ids3/15) 每 tick 状态机 转码表+跳表（可测纯函数）
##   scripts/event_system_spec.json      EventCtx 显示结构(0x72 type_id + 0x74..0x84 params)、
##                                       27 类 taxonomy 名、EventListConfig(27×4)、EventHistoryScreen
##
## 复刻边界（诚实标注）：
##   ✅ 已 1:1 复刻：EventCtx 结构、taxonomy(27)、EventListConfig(27)、派发注册表(HANDLERS+PREDICATES)、
##      两个可测条件求值(0x4e82c0/0x4e7e10)、每 tick 状态机(0x44d950)。
##   🔴 未接项（非图像逆向缺口，与雪国气候字节/战斗 gun 惩罚/council NPC 名表同类）：
##      A. 效果 handler 主体（显示 MSG / 构造菜单 / 改游戏状态）需运行时对象 + UI 接线 → 仅结构事实入库，未执行。
##      B. 完整 C++ vtable 仅 18 id 经静态自断言反推（0..0x3f 其余槽位需 Unicorn 运行时 dump，ref 已证无静态表）。
##      C. NPC 名表(id 1000..1999/3000+) 同 council，待导出 → 显示名走占位。

## ============================================================ EventCtx（派发上下文）
## 运行时 handler 上下文（getCtx=0x49f6b0 → 0x516610；续81+ 契约）：
##   [ctx+0] word  event-type id     == handler 自断言的 opcode
##   [ctx+4] word  result A           handler 可写
##   [ctx+6] word  result B           handler 可写（applier 常设 0/1）
##   [ctx+8] word  arg                与运行时值比较
##   [ctx+0xc] word flags             额外门控（如 0x4e7e10 的 bit2）
class EventCtx:
	var event_id : int = 0      # [ctx+0]
	var result_a : int = 0      # [ctx+4]
	var result_b : int = 0      # [ctx+6]
	var arg      : int = 0      # [ctx+8]
	var flags    : int = 0      # [ctx+0xc]


## ============================================================ EventCtx 显示结构（原版 0x4eae50）
## 0x72 word  taxonomy type_id；0x74..0x84 dword param0..param4。本层仅存结构，渲染走 EventText。
class EventDisplayCtx:
	var type_id : int = 0
	var param : Array = [0,0,0,0,0]   # param0..param4


## ============================================================ taxonomy 名（27 类，taxonomy_index 2..28）
## 取自 event_system_spec.json event_taxonomy.entries；键 = taxonomy_index。
const TAXONOMY : Dictionary = {
	2:"          寺院      ",
	3:"        历史事件    ",
	4:"    木下藤吉郎的主题",
	5:"         大商人     ",
	6:"      新武将的主题  ",
	7:"     柴田胜家的主题 ",
	8:"     明智光秀的主题 ",
	9:"       普通的城镇   ",
	10:"          京都      ",
	11:"          界镇      ",
	12:"          城内      ",
	13:"          自宅      ",
	14:"          茶会      ",
	15:"          会议    ",
	16:"          酒馆      ",
	17:"         剑术道场     ",
	18:"     教堂-旅店-医生 ",
	19:"          行军      ",
	20:"          战斗      ",
	21:"        个人战斗    ",
	22:"        墨俣筑城    ",
	23:"       阿市的悲剧   ",
	24:"       金崎撤退战   ",
	25:"       本能寺大火   ",
	26:"        游戏开始    ",
	27:"          开始      ",
	28:"          结局      ",
}

## EventListConfig：每类 4 字节属性（BGM/scene/params，列语义 TBD）。键 = taxonomy_index。
const EVENT_LIST_CONFIG : Dictionary = {
	2:[0,0,0,3],   3:[6,5,5,4],   4:[5,8,8,8],   5:[11,11,11,6], 6:[6,6,13,13],
	7:[13,15,15,15], 8:[5,9,7,11], 9:[7,7,3,10], 10:[7,2,11,9], 11:[10,7,9,10],
	12:[8,10,8,11], 13:[10,10,12,11], 14:[32,1,248,0], 15:[32,1,248,0], 16:[216,0,0,0],
	17:[0,0,0,0],  18:[112,0,208,0], 19:[208,0,176,0], 20:[176,0,0,0], 21:[0,0,0,0],
	22:[32,0,32,0], 23:[32,0,16,0], 24:[16,0,0,0],  25:[0,0,0,0],  26:[0,0,0,2],
	27:[0,4,0,6],  28:[0,7,0,0],
}


## ============================================================ 派发注册表：事件 id → handler 地址
## 取自 event_handlers_full_ref.py HANDLERS（18 id / 49 handler；id29 纠正、0x490c0 笔误剔除）。
## 注：同一 handler 可能自断言多个 id（派发把相关 id 归并到同一函数）。
const HANDLERS : Dictionary = {
	0:[0x4a3df3,0x4c2d5b,0x45f020,0x4accb0,0x4da170,0x4daf20],
	1:[0x484f34],
	2:[0x45f020,0x45dc50,0x461510,0x488993],
	3:[0x4accb0,0x4da170,0x4daf20,0x447520,0x450b90,0x4608b7,0x461da0,0x44d950],
	4:[0x41ddd5,0x4c9db0],
	5:[0x41ddd5,0x4c9db0,0x4a7000],
	6:[0x45cc40,0x4d1080],
	7:[0x45cc40,0x4d1080],
	8:[0x44a120],
	9:[0x441750,0x44ca90,0x45e78c,0x460420,0x46e2e0,0x470260,0x4b4b20,0x4b4d10],
	10:[0x4e7e10],
	11:[0x4d34cb],
	13:[0x4146c0,0x415b70,0x41adb0,0x4c34cf,0x4c3610,0x4d5560,0x4d83e0,0x4e82c0],
	14:[0x4146c0,0x415b70,0x41adb0,0x4c34cf,0x4c3610,0x4d5560,0x4d83e0,0x4e82c0,0x41d980],
	15:[0x44d950,0x41ddd5,0x4c9db0,0x4a7000,0x444220,0x460660,0x4b3890,0x4b3ac0,0x4b3b58,0x4d5a20],
	16:[0x4d5a20,0x441cf0],
	17:[0x4d5a20,0x4a7160],
	29:[0x4499f0],
}

## handler → 置信度 {strong: cmp-imm 自断言; medium: 零测试/递减 idiom(id0/1)}
## 取自 event_handlers_full_ref.py CONFIDENCE，压成地址 → conf 一级字典。
const CONFIDENCE : Dictionary = {
	0x4a3df3:"medium",0x4c2d5b:"medium",0x45f020:"medium",0x4accb0:"medium",0x4da170:"medium",0x4daf20:"medium",
	0x484f34:"medium",
	0x45dc50:"strong",0x461510:"strong",0x488993:"strong",
	0x447520:"strong",0x450b90:"strong",0x4608b7:"strong",0x461da0:"strong",0x44d950:"strong",
	0x41ddd5:"strong",0x4c9db0:"strong",
	0x4a7000:"strong",
	0x45cc40:"strong",0x4d1080:"strong",
	0x44a120:"strong",
	0x441750:"strong",0x44ca90:"strong",0x45e78c:"strong",0x460420:"strong",0x46e2e0:"strong",0x470260:"strong",0x4b4b20:"strong",0x4b4d10:"strong",
	0x4e7e10:"strong",
	0x4d34cb:"strong",
	0x4146c0:"strong",0x415b70:"strong",0x41adb0:"strong",0x4c34cf:"strong",0x4c3610:"strong",0x4d5560:"strong",0x4d83e0:"strong",0x4e82c0:"strong",0x41d980:"strong",
	0x444220:"strong",0x460660:"strong",0x4b3890:"strong",0x4b3ac0:"strong",0x4b3b58:"strong",0x4d5a20:"strong",0x441cf0:"strong",0x4a7160:"strong",
	0x4499f0:"strong",
}


## ============================================================ PREDICATES：49 handler 元数据
## 键值 = handler 地址；值 = [ids, kind, tables, gate, semantics, conf]
##   ids      : 该 handler 自断言的事件 id 列表
##   kind     : gate|builder|thunk|condition|effect|dispatcher
##   tables   : [[global_base, stride], ...]（_evt_index_expr 反推的索引表）
##   gate     : 额外门控（全局/flags 位测试），空串=无
##   semantics: 短语义描述（续107/108）
##   conf     : high|medium
## 来源：event_predicates_ref.py PREDICATES（49 条全量）。
const PREDICATES : Dictionary = {
	0x4e82c0:[[13,14],"condition",[[0x519548,5]],"[0x516638]&0x14","id13 当前所在国==arg；id14 气候组==arg", "high"],
	0x4e7e10:[[10],"condition",[[0x5179b8,14]],"[ctx+0xc]&2==0","id10 事件关联国==arg", "high"],
	0x4b4b20:[[9],"condition",[],"","id9 调0x49f430(arg)返回值==存储值→FIRE", "high"],
	0x44ca90:[[9],"effect",[],"[0x52063c]","id9 显示msg 0x1224..0x1227+查全局门控", "high"],
	0x4b3ac0:[[15],"effect",[],"","id15 按byte[obj+0x1b]&7跳表派发7子例程", "high"],
	0x4499f0:[[29],"effect",[],"","id29(续106纠正非0/1) 自断言0x1d+FIRE+msg/概率", "high"],
	0x41adb0:[[13,14],"gate",[],"id∈{0xffff,0xd,0xe}","准入判定：id==0xffff/13/14 放行", "high"],
	0x441cf0:[[16],"gate",[],"byte[0x517894]&4==0","id16 全局bit2==0→放行", "high"],
	0x44a120:[[8],"gate",[],"[ctx+0xc]&2==0","id8 flags bit1==0→放行", "high"],
	0x4b3890:[[15],"gate",[],"","id15 arg==byte[0x520602]→放行", "high"],
	0x450b90:[[3],"builder",[],"","构造选项数组→0x513f08(菜单项0..3)", "high"],
	0x447520:[[3],"builder",[],"byte[[0x52063c]+8]&4","id3 构造选项表(1/2项)", "high"],
	0x4608b7:[[3],"dispatcher",[],"[ctx+6]==0","按id跳表派发(jmp[ecx*4+0x4608e8],4项)", "high"],
	0x461da0:[[3],"dispatcher",[],"arg==0(且arg<2)","按id跳表派发(jmp[ecx*4+0x461dd0],4项)", "high"],
	0x461510:[[2],"thunk",[],"","★TAIL-CALL跳板：取调用方函数指针尾跳(实现由调用方供给)", "high"],
	0x4d5a20:[[15,16,17],"builder",[[0x50cfa8,13]],"[ctx+0xc]&2==0;byte[0x516638]&4","★謁見菜单6选项(闲谈/礼品/任务/方针/传言/离开)", "high"],
	0x4c3610:[[13,14],"condition",[[0x519548,5]],"","国情表stride5：arg==当前国/气候组", "high"],
	0x41d980:[[14],"condition",[[0x519548,5],[0x519868,47]],"[ctx+0xc]读取","国情表+武将实体表stride47", "high"],
	0x4d5560:[[13,14],"condition",[[0x519868,47]],"[ctx+0xc]读取","武将实体表stride47", "high"],
	0x444220:[[15],"condition",[[0x51eb88,31]],"","城/町表stride31(取低字节)", "high"],
	0x45e78c:[[9],"condition",[[0x51eb88,31],[0x5176a8,4]],"","城/町表+ S10表stride4 + RNG + MSG", "high"],
	0x470260:[[9],"condition",[[0x51eb88,31],[0x516a28,16]],"","城/町表+ S7运行时表stride16；调0x49f430", "high"],
	0x4d1080:[[6,7],"condition",[[0x51eb88,31],[0x5179b8,14]],"[ctx+0xc]读取","城/町表+49国政治表stride14", "high"],
	0x4da170:[[0,3],"effect",[[0x519868,47]],"word[参数+0x14](武将实体号)<370","★赐物：武将实体表stride47第三条证据；msg0xc6", "high"],
	0x4daf20:[[0,3],"effect",[[0x519868,47]],"word[参数+0x14](武将实体号)<370","★与0x4da170同构；msg0xd9", "high"],
	0x4a3df3:[[0],"condition",[[0x51eb88,31]],"[ctx+0xc]读取;遍历非空","★按剩余量概率判定：ebp=50-x；RNG(ebp)", "high"],
	0x4accb0:[[0,3],"gate",[],"byte[0x5179b7]==0xff","读全局0x5179b7判==0xff；写0x525b1c=0", "high"],
	0x4c34cf:[[13,14],"condition",[],"[0x49f5e0对象+0x2c]&0x700==0x700时放行","与0x4e82c0同构并行id13/14", "high"],
	0x46e2e0:[[9],"effect",[],"","取0x5224f0对象；置0x520610=1；清零3全局；双输出查询", "high"],
	0x4b4d10:[[9],"condition",[],"id==9;0x49f430(arg)==存储值","★与0x4b4b20同族；clamp(ebp+edx+5,1,7)等级", "high"],
	0x4a7000:[[5,15],"condition",[[0x51eb88,31]],"byte[城表+0x1b]&0x10==0;byte[+0x1d]非0xff且>0且==1","城/町表首条；arg==0；id∈{5,15}", "high"],
	0x441750:[[9],"condition",[],"id==9;RNG(3)==0(1/3);arg<49","1/3概率；arg为合法省索引", "high"],
	0x44d950:[[3,15],"condition",[],"全局word[0x5205fe]∉{2,3};arg&0x8000==0","★每tick状态机：转码表0x44da00+跳表0x44d9ec", "high"],
	0x41ddd5:[[4,5,15],"condition",[],"[ctx+0xc]读取","按id三分支；全局0x51987e", "high"],
	0x4c9db0:[[4,5,15],"effect",[],"全局word[0x52544c]==6","多段消息：MSG 0x5ac/0x5ad/0x5ae", "high"],
	0x4d34cb:[[11],"effect",[],"[ctx+0]==0xb(11)","★事件到期/复位器：补足时间节点后清空ctx", "high"],
	0x4a7160:[[17],"effect",[],"id既非0xffff也非0x11(17)","★定时/延时触发器：[ctx+2]每tick递减，归零触发", "high"],
	0x45cc40:[[6,7],"gate",[],"id∈{6,7}","调0x45a700；id6/7放行", "high"],
	0x460420:[[9],"builder",[],"id==9;全局word[0x513fcc]判定","依word[0x513fcc]选路+0x460530取结果；清选项数组", "high"],
	0x4b3b58:[[15],"effect",[],"","★0x4b3ac0七路跳表公共尾；msg 0x2f/0x24/0x21/0x53/0x2b", "high"],
	0x460660:[[15],"effect",[],"RNG(2)==0; [ctx+0]!=0xf","1/2概率；id15时退出", "high"],
	0x484f34:[[1],"condition",[],"","★id1唯一handler：2×48B子记录(vptr对象)bit0置位判定", "high"],
	0x45f020:[[0,2],"builder",[],"","★随机化选项菜单：RNG(5/10)→0x513fd0/0x513fc8；填3槽", "high"],
	0x4c2d5b:[[0],"condition",[[0x5179b8,14]],"[ctx+0xc]读取","★指针→省索引反算(魔数÷14坐实stride14)；哨兵49", "high"],
	0x488993:[[2],"builder",[],"","★UI/面板构造器(像素坐标)；标题/标签字符串资源", "high"],
	0x45dc50:[[2],"condition",[],"","调0x44dc60取对象；word[+3] shr7&0x1f 抽bits7..11；id2判msg0x313", "high"],
	0x4146c0:[[13,14],"effect",[],"[ctx+0xc]读取","★id13/14主效果器(239insns)；取四槽对象输出缓冲", "high"],
	0x415b70:[[13,14],"effect",[],"[ctx+0xc]读取","多段效果：0x49f830(0/2/3)取槽位对象+子动作13/15/18", "high"],
	0x4d83e0:[[13,14],"gate",[],"byte[0x516638]&4必须置位","写word[0x506c4c]=0xffff；id13..14放行+0x4dcc80", "high"],
}


## ============================================================ 查询辅助
static func handlers_for(event_id: int) -> Array:
	return HANDLERS.get(event_id, [])

static func all_ids() -> Array:
	var ks : Array = HANDLERS.keys()
	ks.sort()
	return ks

static func confidence_of(event_id: int, handler: int) -> String:
	return CONFIDENCE.get(handler, "")

## 取某事件 id 的所有 handler 元数据（按 PREDICATES）
static func predicates_for(event_id: int) -> Array:
	var out : Array = []
	for h in handlers_for(event_id):
		if PREDICATES.has(h):
			out.append(PREDICATES[h])
	return out

static func kind_of(handler: int) -> String:
	return PREDICATES.get(handler, [null,"","","","",""])[1]

static func tables_of(handler: int) -> Array:
	return PREDICATES.get(handler, [null,"","","","",""])[2]

## taxonomy / EventListConfig 查询
static func taxonomy_name(taxonomy_index: int) -> String:
	return TAXONOMY.get(taxonomy_index, "")

static func event_list_config(taxonomy_index: int) -> Array:
	return EVENT_LIST_CONFIG.get(taxonomy_index, [])


## ============================================================ 条件判定（已解码、可测纯函数）
## 来源：event_cond_ref.py（0x4e82c0 / 0x4e7e10）。
## 天气/地域等运行时值由调用方注入（本层不读运行时全局），便于单测。

const OP_PROVINCE_PARAM = 10   # 事件关联国 == arg   (0x4e7e10)
const OP_PROVINCE_CUR   = 13   # 当前所在国 == arg   (0x4e82c0)
const OP_CLIMATE_CUR    = 14   # 当前气候组 == arg   (0x4e82c0)

## 气候组 → 是否雪国（GAME_DATA_SPEC 3.9.7: +1 ∈ {0,2,4}）
const SNOW_GROUPS : Array = [0, 2, 4]

## 0x4e82c0：opcode 13/14 条件。命中返回 true（将触发事件）。
##   cur_prov_idx        : 玩家当前所在国 idx
##   cur_climate_group   : 当前气候组
##   gate                : 外部 gating；原版 [0x516638]&0x14 由调用方判（此处不入参，保持纯）
static func eval_4e82c0(opcode: int, arg: int, cur_prov_idx: int, cur_climate_group: int) -> bool:
	if opcode == OP_PROVINCE_CUR:       # 13
		return cur_prov_idx == arg
	if opcode == OP_CLIMATE_CUR:        # 14
		return cur_climate_group == arg
	return false

## 0x4e7e10：opcode 10 条件。flags bit2 必须=0 才放行（门控）。
static func eval_4e7e10(opcode: int, arg: int, assoc_prov_idx: int, flags: int) -> bool:
	if opcode != OP_PROVINCE_PARAM:
		return false
	if flags & 2:                       # test byte[ctx+0xc],2
		return false
	return assoc_prov_idx == arg

## 高层封装：给定派发 ctx + 运行时状态对象(rt)，该事件是否触发（仅覆盖已解码 opcode 10/13/14）。
## rt 须提供：current_province()->int, current_climate()->int, assoc_province()->int
static func would_fire(ctx: EventCtx, rt: Object) -> bool:
	match ctx.event_id:
		OP_PROVINCE_CUR:
			return eval_4e82c0(ctx.event_id, ctx.arg, rt.current_province(), rt.current_climate())
		OP_CLIMATE_CUR:
			return eval_4e82c0(ctx.event_id, ctx.arg, rt.current_province(), rt.current_climate())
		OP_PROVINCE_PARAM:
			return eval_4e7e10(ctx.event_id, ctx.arg, rt.assoc_province(), ctx.flags)
	return false


## ============================================================ 每 tick 状态机（0x44d950，ids 3/15）
## 来源：event_dispatch_tables_ref.py。转码表 0x44da00(10B) + 跳表 0x44d9ec(5项)。
## 状态 state(0..9) → 转码 idx → 跳表分支。
## 分支枚举：0=按id分派(0x44d9b3), 1=state7调0x4441a0(0x44d9ab), 2=终态置0x506c4c=0xaa4(0x44d9a0), -1=EXIT(0x44d9e4)
const TC_44DA00 : Array = [0,4,1,4,4,4,4,2,4,3]
const JT_44D9EC : Array = [0,0,1,2,-1]            # 跳表 5 项 → 分支枚举（[4]=EXIT）
const BR_DISPATCH_ID  : int = 0
const BR_STATE7       : int = 1
const BR_TERMINAL     : int = 2
const BR_EXIT         : int = -1

## 主入口：返回分支枚举。门控：global_mode∈{2,3}→EXIT；arg_flags&0x8000→EXIT；state>9→EXIT。
static func tick_dispatch(state: int, global_mode: int, arg_flags: int) -> int:
	if global_mode == 2 or global_mode == 3:
		return BR_EXIT
	if arg_flags & 0x8000:
		return BR_EXIT
	if state < 0 or state > 9:
		return BR_EXIT
	var tc : int = TC_44DA00[state]
	if tc < 0 or tc >= JT_44D9EC.size():
		return BR_EXIT
	return JT_44D9EC[tc]

## 0x44d9b3 分支体内的按 id 二级分派（state 0/2 进入）：id3→0x44da10，id15→0x44da90。
## 返回目标 handler VA 字符串（MSG 显示主体，UI 待接线 → 仅路由）。
static func state0_dispatch(event_id: int) -> String:
	if event_id == 3:
		return "0x44da10"     # id3: MSG 0x11b9 / 0x11ba
	if event_id == 15:
		return "0x44da90"     # id15: MSG 0xde5 / 0xde6
	return ""
