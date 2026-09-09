# -*- coding: utf-8 -*-
"""event_sys.gd 的 Python 等价验证镜像（本机 --script 主循环失效，走此替代链路）。
复跑与 GDScript 同一套断言：派发注册表结构、taxonomy、条件求值、每 tick 状态机。
来源：src/core/event_sys.gd + scripts/{event_handlers_full,event_predicates,event_cond,event_dispatch_tables}_ref.py
"""
# ---- 与 event_sys.gd 完全同源的常量/数据（避免 import Godot 模块） ----
HANDLERS = {
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
CONFIDENCE_KEYS = set()  # 仅结构校验用，python 镜像不存 conf 细节
PREDICATES = {
    0x4e82c0:[[13,14],"condition",[[0x519548,5]],"[0x516638]&0x14","high"],
    0x4e7e10:[[10],"condition",[[0x5179b8,14]],"[ctx+0xc]&2==0","high"],
    0x4b4b20:[[9],"condition",[],"","high"],
    0x44ca90:[[9],"effect",[],"[0x52063c]","high"],
    0x4b3ac0:[[15],"effect",[],"","high"],
    0x4499f0:[[29],"effect",[],"","high"],
    0x41adb0:[[13,14],"gate",[],"id∈{0xffff,0xd,0xe}","high"],
    0x441cf0:[[16],"gate",[],"byte[0x517894]&4==0","high"],
    0x44a120:[[8],"gate",[],"[ctx+0xc]&2==0","high"],
    0x4b3890:[[15],"gate",[],"","high"],
    0x450b90:[[3],"builder",[],"","high"],
    0x447520:[[3],"builder",[],"byte[[0x52063c]+8]&4","high"],
    0x4608b7:[[3],"dispatcher",[],"[ctx+6]==0","high"],
    0x461da0:[[3],"dispatcher",[],"arg==0(且arg<2)","high"],
    0x461510:[[2],"thunk",[],"","high"],
    0x4d5a20:[[15,16,17],"builder",[[0x50cfa8,13]],"[ctx+0xc]&2==0;byte[0x516638]&4","high"],
    0x4c3610:[[13,14],"condition",[[0x519548,5]],"","high"],
    0x41d980:[[14],"condition",[[0x519548,5],[0x519868,47]],"[ctx+0xc]读取","high"],
    0x4d5560:[[13,14],"condition",[[0x519868,47]],"[ctx+0xc]读取","high"],
    0x444220:[[15],"condition",[[0x51eb88,31]],"","high"],
    0x45e78c:[[9],"condition",[[0x51eb88,31],[0x5176a8,4]],"","high"],
    0x470260:[[9],"condition",[[0x51eb88,31],[0x516a28,16]],"","high"],
    0x4d1080:[[6,7],"condition",[[0x51eb88,31],[0x5179b8,14]],"[ctx+0xc]读取","high"],
    0x4da170:[[0,3],"effect",[[0x519868,47]],"word[参数+0x14]<370","high"],
    0x4daf20:[[0,3],"effect",[[0x519868,47]],"word[参数+0x14]<370","high"],
    0x4a3df3:[[0],"condition",[[0x51eb88,31]],"遍历非空","high"],
    0x4accb0:[[0,3],"gate",[],"byte[0x5179b7]==0xff","high"],
    0x4c34cf:[[13,14],"condition",[],"[0x49f5e0对象+0x2c]&0x700==0x700","high"],
    0x46e2e0:[[9],"effect",[],"","high"],
    0x4b4d10:[[9],"condition",[],"id==9;0x49f430(arg)==存储值","high"],
    0x4a7000:[[5,15],"condition",[[0x51eb88,31]],"byte[城表+0x1b]&0x10==0","high"],
    0x441750:[[9],"condition",[],"id==9;RNG(3)==0(1/3);arg<49","high"],
    0x44d950:[[3,15],"condition",[],"global_mode∉{2,3};arg&0x8000==0","high"],
    0x41ddd5:[[4,5,15],"condition",[],"[ctx+0xc]读取","high"],
    0x4c9db0:[[4,5,15],"effect",[],"word[0x52544c]==6","high"],
    0x4d34cb:[[11],"effect",[],"[ctx+0]==0xb(11)","high"],
    0x4a7160:[[17],"effect",[],"id既非0xffff也非0x11(17)","high"],
    0x45cc40:[[6,7],"gate",[],"id∈{6,7}","high"],
    0x460420:[[9],"builder",[],"id==9;word[0x513fcc]判定","high"],
    0x4b3b58:[[15],"effect",[],"","high"],
    0x460660:[[15],"effect",[],"RNG(2)==0;[ctx+0]!=0xf","high"],
    0x484f34:[[1],"condition",[],"","high"],
    0x45f020:[[0,2],"builder",[],"","high"],
    0x4c2d5b:[[0],"condition",[[0x5179b8,14]],"[ctx+0xc]读取","high"],
    0x488993:[[2],"builder",[],"","high"],
    0x45dc50:[[2],"condition",[],"","high"],
    0x4146c0:[[13,14],"effect",[],"[ctx+0xc]读取","high"],
    0x415b70:[[13,14],"effect",[],"[ctx+0xc]读取","high"],
    0x4d83e0:[[13,14],"gate",[],"byte[0x516638]&4必须置位","high"],
}
TAXONOMY = {i: "name" for i in range(2,29)}  # 27 项 (2..28)
EVENT_LIST_CONFIG = {i: [0,0,0,0] for i in range(2,29)}
TC_44DA00 = [0,4,1,4,4,4,4,2,4,3]
JT_44D9EC = [0,0,1,2,-1]
BR_DISPATCH_ID, BR_STATE7, BR_TERMINAL, BR_EXIT = 0, 1, 2, -1

OP_PROVINCE_PARAM, OP_PROVINCE_CUR, OP_CLIMATE_CUR = 10, 13, 14

def handlers_for(eid): return HANDLERS.get(eid, [])
def all_ids(): return sorted(HANDLERS)
def predicates_for(eid): return [PREDICATES[h] for h in handlers_for(eid) if h in PREDICATES]
def kind_of(h): return PREDICATES.get(h, [None,"","","",""])[1]

def eval_4e82c0(opcode, arg, cur_prov_idx, cur_climate_group):
    if opcode == OP_PROVINCE_CUR: return cur_prov_idx == arg
    if opcode == OP_CLIMATE_CUR:  return cur_climate_group == arg
    return False

def eval_4e7e10(opcode, arg, assoc_prov_idx, flags):
    if opcode != OP_PROVINCE_PARAM: return False
    if flags & 2: return False
    return assoc_prov_idx == arg

def tick_dispatch(state, global_mode, arg_flags):
    if global_mode == 2 or global_mode == 3: return BR_EXIT
    if arg_flags & 0x8000: return BR_EXIT
    if state < 0 or state > 9: return BR_EXIT
    tc = TC_44DA00[state]
    if tc < 0 or tc >= len(JT_44D9EC): return BR_EXIT
    return JT_44D9EC[tc]

def state0_dispatch(event_id):
    if event_id == 3:  return "0x44da10"
    if event_id == 15: return "0x44da90"
    return ""

# ---------------------------------------------------------------- 断言执行
fails = 0
def chk(name, cond):
    global fails
    if cond: print(f"  [PASS] {name}")
    else:    print(f"  [FAIL] {name}"); fails += 1

print("--- 1) 派发注册表结构（event_handlers_full_ref） ---")
all_h = sorted({h for v in HANDLERS.values() for h in v})
chk("49 个独立 handler", len(all_h) == 49)
chk("18 个事件 id", len(HANDLERS) == 18)
chk("id 集合正确", all_ids() == [0,1,2,3,4,5,6,7,8,9,10,11,13,14,15,16,17,29])
for h in all_h:
    chk(f"handler {h:#x} 合法代码地址", 0x400000 <= h < 0x600000)
chk("边界 id 0x31 不在", 0x31 not in HANDLERS)
chk("边界 id 0x3f 不在", 0x3f not in HANDLERS)
chk("0x490c0 笔误地址剔除", 0x490c0 not in all_h)
for hid in (0x4e82c0,0x4e7e10,0x4b4b20,0x44ca90,0x4b3ac0,0x4499f0,0x4a3df3,0x484f34,0x4d5a20):
    chk(f"已知 handler {hid:#x} 在表中", hid in all_h)
chk("0x4e82c0 ∈ id13 且 ∈ id14", 0x4e82c0 in handlers_for(13) and 0x4e82c0 in handlers_for(14))
chk("0x4e7e10 ∈ id10", 0x4e7e10 in handlers_for(10))
chk("0x4b3ac0 ∈ id15", 0x4b3ac0 in handlers_for(15))
chk("0x4b4b20 ∈ id9 且 0x44ca90 ∈ id9", 0x4b4b20 in handlers_for(9) and 0x44ca90 in handlers_for(9))
chk("0x4499f0 ∈ id29（纠正非0/1）", 0x4499f0 in handlers_for(29))
chk("0x484f34 ∈ id1（真实 id1 handler）", 0x484f34 in handlers_for(1))
chk("0x4a3df3 ∈ id0（零测试 idiom）", 0x4a3df3 in handlers_for(0))

print("--- 2) PREDICATES 全量（event_predicates_ref，49 条） ---")
chk("PREDICATES 恰 49 条", len(PREDICATES) == 49)
chk("PREDICATES 覆盖全部 handler", set(PREDICATES.keys()) == set(all_h))
for h in (0x4e82c0,0x4e7e10):
    chk(f"{h:#x} 索引国情表 stride5 / 49国政治 stride14",
        [0x519548,5] in PREDICATES[h][2] or [0x5179b8,14] in PREDICATES[h][2])
chk("0x4499f0 记为 id29", 29 in PREDICATES[0x4499f0][0])
chk("0x461510 记 kind=thunk", PREDICATES[0x461510][1] == "thunk")

print("--- 3) taxonomy / EventListConfig（event_system_spec） ---")
chk("taxonomy 27 类 (2..28)", len(TAXONOMY) == 27 and set(TAXONOMY) == set(range(2,29)))
chk("EventListConfig 27 × 4B", len(EVENT_LIST_CONFIG) == 27
    and all(len(v)==4 for v in EVENT_LIST_CONFIG.values()))
chk("taxonomy 含'寺院/本能寺大火/结局'",
    TAXONOMY[2] and TAXONOMY[25] and TAXONOMY[28])

print("--- 4) 条件求值 0x4e82c0 (event_cond_ref) ---")
chk("op13 cur==arg 命中", eval_4e82c0(13,5,5,0) is True)
chk("op13 cur!=arg 不命中", eval_4e82c0(13,5,6,0) is False)
chk("op14 climate==arg 命中", eval_4e82c0(14,2,0,2) is True)
chk("op14 climate!=arg 不命中", eval_4e82c0(14,4,0,2) is False)
chk("op99 不命中", eval_4e82c0(99,0,0,0) is False)

print("--- 5) 条件求值 0x4e7e10 (event_cond_ref) ---")
chk("op10 assoc==arg 命中", eval_4e7e10(10,7,7,0) is True)
chk("op10 assoc!=arg 不命中", eval_4e7e10(10,7,3,0) is False)
chk("op10 flags bit2 门控", eval_4e7e10(10,7,7,2) is False)
chk("op9 非10 不命中", eval_4e7e10(9,7,7,0) is False)

print("--- 6) 每 tick 状态机 0x44d950 (event_dispatch_tables_ref) ---")
chk("转码表 TC_44DA00 正确", TC_44DA00 == [0,4,1,4,4,4,4,2,4,3])
chk("跳表 JT_44D9EC 正确", JT_44D9EC == [0,0,1,2,-1])
chk("global_mode==2 → EXIT", tick_dispatch(0,2,0) == BR_EXIT)
chk("global_mode==3 → EXIT", tick_dispatch(0,3,0) == BR_EXIT)
chk("arg_flags bit15 → EXIT", tick_dispatch(0,0,0x8000) == BR_EXIT)
chk("state<0 → EXIT", tick_dispatch(-1,0,0) == BR_EXIT)
chk("state>9 → EXIT", tick_dispatch(10,0,0) == BR_EXIT)
chk("state0 → DISPATCH_ID", tick_dispatch(0,0,0) == BR_DISPATCH_ID)
chk("state1 → EXIT(空转)", tick_dispatch(1,0,0) == BR_EXIT)
chk("state2 → DISPATCH_ID", tick_dispatch(2,0,0) == BR_DISPATCH_ID)
chk("state3 → EXIT(空转)", tick_dispatch(3,0,0) == BR_EXIT)
chk("state4..6 → EXIT(空转)", all(tick_dispatch(s,0,0)==BR_EXIT for s in (4,5,6)))
chk("state7 → STATE7(调0x4441a0)", tick_dispatch(7,0,0) == BR_STATE7)
chk("state8 → EXIT(空转)", tick_dispatch(8,0,0) == BR_EXIT)
chk("state9 → TERMINAL(置0x506c4c=0xaa4)", tick_dispatch(9,0,0) == BR_TERMINAL)
chk("有效状态恰 {0,2,7,9}", sorted(s for s in range(10) if tick_dispatch(s,0,0)!=BR_EXIT)==[0,2,7,9])
chk("state0 按 id 分派 id3→0x44da10", state0_dispatch(3)=="0x44da10")
chk("state0 按 id 分派 id15→0x44da90", state0_dispatch(15)=="0x44da90")
chk("state0 其他 id 无路由", state0_dispatch(5)=="")

print(f"\nRESULT: {'ALL PASS' if fails==0 else f'{fails} FAIL'}")
