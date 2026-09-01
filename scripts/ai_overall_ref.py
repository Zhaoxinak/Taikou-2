# -*- coding: utf-8 -*-
"""
ai_overall_ref.py — 整体 AI 决策系统（续105, 2026-08-29）

== 范围 ==
本文件文档化《太阁立志传2》EXE 中"整体 AI 决策系统"的调用链与 6 个非外交子决策，
闭合 MEMORY.md"仍待破"清单第 1 项（续104 新开的大模块）。外交子决策 0x4a84e0 已在
ai_diplomacy_ref.py（续104）闭合，此处仅列出其在 AI 循环中的位置。

== 顶层调用链（实锤）==
  0x4a0d50  ai_top_tick        —— 游戏时钟/日期驱动（114 直接调用方 = 主循环每帧调用）
      └─ 0x4a6ba0  ai_think     —— 思考入口(1 调用方:0x4a0e33)；按 [esp+0xc] 模式分流
            ├─ (模式1/6/11/21 分支: 0x4a7370/0x4a71e0/0x4a6d30/0x41a360/0x4a73e0 等)
            └─ 主 AI 每回合块 (0x4a6ce9 起):
                 call 0x4a6e50 / 0x4a6f60 / 0x4a7000
                 call 0x4a70b0  prov_dispatch   (1 调用方:0x4a6d06)
                 call 0x4a7160 / 0x4a6d30 / 0x41a360 / 0x4a73e0

== 每省派发循环 0x4a70b0（49 省遍历，步长 0xe = 14B = 国情表 stride）==
  门: call 0x4a0d10 (ai_active_guard) —— 返回非0则整省跳过
  门: al = province_status[prov] (byte[0x519640+prov])；bl = byte[0x5205f2] (=当前"日序号" 1..31)
       * 若 al==0x1f 且 bl==1  → 仅调 0x4a84e0(外交) 后返回
       * 若 al==bl 且 word[prov+4](城主武将号)<0x172  → 进入完整 7 段决策链
       * 否则 → 跳过
  ⇒ 这是"分日错峰"机制：byte[0x5205f2] 是日期计数器，每省有一个激活日 = province_status
     字段；AI 每天运行，但每天仅 ~1–2 个 province_status 匹配的省被激活，约 1~2 月轮完 49 省。

== 完整 7 段子决策链（活跃省每激活一次依次执行）==
  ① 0x4a84e0  ai_diplo      外交          (2 调用方, 全在 0x4a70b0)  —— 续104 已闭
  ② 0x4a8250  ai_assign_gov  城主/守将配置 (3 调用方: AI循环+玩家指令0x4881aa+事件0x4bd993)  —— 共享基元
  ③ 0x4a8870  ai_attack      出兵/宣戦     (7 调用方: AI循环+玩家0x4881b3+事件0x4abcf2/0x4b61b4/0x4bd9a5 等) —— 共享基元
  ④ 0x4a8e80  ai_develop     内政命令      (6 调用方: AI循环+玩家0x4881bc+事件0x4abcfb/0x4b61bd/0x4bd9a5 等) —— 共享基元
  ⑤ 0x4a97d0  ai_transfer    武将転任/配置  (1 调用方: 仅 AI循环)  —— AI 专属
  ⑥ 0x4a92c0  ai_reinforce   増援/兵力移動  (1 调用方: 仅 AI循环)  —— AI 专属；**返回非0 ⇒ 跳过 ⑦**
  ⑦ 0x4a94e0  ai_recruit     武将登用/引抜  (1 调用方: 仅 AI循环)  —— AI 专属；仅当 ⑥ 返回 0 才执行

  关键约束：⑥ ⑦ 互斥 —— 同一激活若已下达增援命令，则不再尝试登用（每激活至多一个"人事/补给"大动作）。

== 6 个非外交子决策的语义（依据反汇编 + 上下文推断，核心 helper 语义标注"推断"）==
  ② 0x4a8250 assign_gov:
        call 0x49b760(prov) → 若==3(交战?) call 0x4a8370 守卫(省首城匹配则跳过)
        call 0x4a8390(prov,1) 搜索候选武将(返回武将号或 0xffff)
        据 byte[主将实体+0x22](主将某项能力/忠诚) 阈值分支:
            <0x3c(60): 若本省为主家(eBP)则跳过, 否则 0x49b7f0(prov,候选) 配置
            <0x5a(90): 同上
            >=0x5a  : 0x49b7b0(prov,2); 0x49b7f0(prov,0xff) 解除配置
        ⇒ "为无主将的城配置/撤换守将"。helper 0x49b7f0 = (推断) 设置城主武将; 0x49b7b0 = (推断) 设置配置模式。
        注意：该函数同时是玩家"城主任命"指令(0x4881aa)与事件(0x4bd993)的同一入口 ⇒ 引擎级基元。

  ③ 0x4a8870 attack:
        先把所有"有合法城主(word[prov+4]<0x172)"的省指针填入全局候选表 0x517848(count in cx)
        若无候选 → 0x49b5a0(prov,0xff)(推断: 取消/无动作) 返回
        call 0x4a8910(prov) 在候选中按"参戦フラグ0x525a50 / 主從状態0x525980 /
            国关系値0x525a88(0x49fe70) / 国力0x5259e8(0x49faf0)"排序挑最优目标省
        0x49b5a0(prov, 目标省索引) (推断: 对目标省宣戦/出兵)
        ⇒ "进攻决策"：挑选最弱/最亲/国力最低且已参戦标记的目标省开战。

  ④ 0x4a8e80 develop:
        al = byte[prov+8] 所属国(0..48) → ebx = 省指针(0x5179b8+国*14)
        若 no 合法主将 → 返回 3
        0x49faf0(prov) → esi(本省国力); 0x49faf0(ebx) → ecx(主家国力)
        取 byte[主将实体+8] 的 bit0/bit2/bit5 (推断: 主将"政治/智略/魅力"适性位)
        依 省力 vs 主家力 + 适性位 + 0x4ebd60(rng) 概率 → 经跳表(0x4a90a0) 选 0/1/2/3:
            0: 0x49b790(prov,0); 0x49b7d0(prov,国)
            1: 0x49b790(prov,1); 0x49b7d0(prov,国)
            2: 0x49b790(prov,2); 0x49b7d0(prov,国)
            3: 0x49b790(prov,3); 0x49b7d0(prov,0xff)
        ⇒ "内政命令"：按相对国力与主将适性概率性下发 4 类内政令(0/1/2/3=農業/商業/治安/改修 待定)，
           目标国=本国。helper 0x49b790=(推断)设内政令类型; 0x49b7d0=(推断)设内政令目标国。
        注：同 0x4a7.../0x4881bc 玩家指令复用 ⇒ 引擎级基元。

  ⑤ 0x4a97d0 transfer:
        call 0x4a9810(prov) 守卫(本省==主家且旗4则否 / 城参戦标记0x1b&0x10则否 /
            已在 0x518588"転任中武将"表有同国记录则否 / 城数>=0xa(10)则否)
        call 0x4ac720(prov) → 待転任武将实体 esi
        call 0x4ac7f0(esi,prov) → 目标省 eax
        call 0x4a9920(eax,esi,prov) 执行転任(设 byte[武将+0x12]=0xff, +0x13=国,
            0x4a00a0/0x4a0540/0x4a05a0 移动, 0x49a880 设"転任中"令0x10, 0x4ebfe0 推送 MSGX 0x50c0e8/0x50c0e0)
        ⇒ "武将転任"：把多余的/不合适的武将调到更合适的城。

  ⑥ 0x4a92c0 reinforce (AI 专属, 门控 ⑦):
        if 省==主家(self=0x49f670) 且 byte[0x516638]&0x10 → 返回 0 (主家不在此路径增援)
        call 0x4a11c0 → ax; if ax>=0xa(10) → 返回 0 (已足够?)
        遍历省城链表([prov]) 找"需增援的支城"(byte[城+0x1b]&0x10 且国匹配) → 0x4a79d0/0x4a9470 校验
        若找到: edi=0x4a1110(实体); 0x4b8090(0,0,prov,edi) 派令; 0x4a1150(edi)
                byte[esi+0x16]=0xf(增援令); +0x13=bl; word[+0x18]=0; +0x1a=0; 0x4a04e0(...) 下发
                byte[edi+0x71]=0; 返回 1 (非0 ⇒ 跳过 ⑦)
        ⇒ "増援/兵力移動"：向缺兵支城调拨兵力。返回 1 时本激活不再登用。

  ⑦ 0x4a94e0 recruit (AI 专属, 仅当 ⑥==0):
        call 0x4a0d10 守卫; 省须有合法城主; 省首城链表非空
        0x49a610(主将)→若!=0xff(已占用)跳过; byte[主将+0x2c]&0x10 等旗检
        call 0x49b750(prov) → 状态 0/1/2:
            0: 0x4abd60(prov) 登用动作A; 0x49c5a0(prov) 收尾
            1: 0x4a9790(prov)→合格支城数; 若>0 call 0x4a9610(prov)(具体登用流程,
               内部 0x4ac470 取自由武将, 0x4a9230 查 0x518588 已存在同国転任记录,
               0x4b8090 派令, 0x4a90b0 设令0xe) 否则 0x49c5a0
            2: 0x4abef0(prov); 0x49c5a0
            3: 0x49c5a0
        ⇒ "武将登用/引抜"：为本省/本家招募自由武将。

== 全局 AI 表（供上述决策读取/写入）==
  0x5259e8  49 word  国力表 (0x49faf0 计算; 城军事 聚合上限 60000)        [续104/95]
  0x525980  49 word  主從状態表 (0x49fd60=get_master_vassal)            [本会话]
  0x525a88  49 word  国关系値表   (0x49fe70=get_diplomacy)              [本会话]
  0x525a50  49 byte  参戦フラグ   (0x4a8ae0 写入: 按省城链表 owner 标记)  [本会话]
  0x517848  指针表   候选省 scratch (0x4a8870 攻击决策时填入)            [本会话]
  0x518588  0x8b×20  転任中武将/増援中实体表 (byte[+0x25]=所属国, +0x16=令) [本会话]
  0x519640  49 byte  各省激活日 (=province_status, 与 0x5205f2 错峰匹配)  [本会话]
  0x5205f0  年偏移 / 0x5205f1 月 / 0x5205f2 日序号(1..31, 错峰键) / 0x5205f3 [续95/本会话]

== 证据/产物 ==
  scripts/_d_4a0d50.txt  _d_4a6ba0.txt  _d_4a70b0.txt
  scripts/_d_4a84e0.txt (续104) _d_4a8250.txt _d_4a8870.txt(+0x4a8910..0x4a8e10 helpers)
  scripts/_d_4a8e80.txt _d_4a97d0.txt(+0x4a9810/0x4a9920) _d_4a92c0.txt(+0x4a9470) _d_4a94e0.txt(+0x4a9610/0x4a91a0/0x4a9230/0x4a90b0)
  scripts/_ai_overall_callers.py  (E8 直接调用方扫描, 见 self_test)
"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

from capstone import *
from capstone.x86 import *

IMG = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000

# 函数地址常量
AI_TOP_TICK    = 0x4a0d50
AI_THINK       = 0x4a6ba0
PROV_DISPATCH  = 0x4a70b0
AI_DIPLO       = 0x4a84e0
AI_ASSIGN_GOV  = 0x4a8250
AI_ATTACK      = 0x4a8870
AI_DEVELOP     = 0x4a8e80
AI_TRANSFER    = 0x4a97d0
AI_REINFORCE   = 0x4a92c0
AI_RECRUIT     = 0x4a94e0

# 全局 AI 表
TBL_POWER      = 0x5259e8   # 49 word 国力
TBL_MV_STATUS  = 0x525980   # 49 word 主從状態
TBL_RELATION   = 0x525a88   # 49 word 国关系値
TBL_WAR_FLAG   = 0x525a50   # 49 byte 参戦フラグ
TBL_CANDIDATE  = 0x517848   # 候选省指针表
TBL_TRANSIT    = 0x518588   # 0x8b×20 転任/増援实体表
TBL_PROV_STATUS= 0x519640   # 49 byte 各省激活日

# 子决策中文名（按 0x4a70b0 调用序）
SUBDECISIONS = [
    (AI_DIPLO,      "外交",        "diplomacy",     2),
    (AI_ASSIGN_GOV, "城主配置",     "assign_governor", 3),
    (AI_ATTACK,     "出兵/宣戦",   "attack",         7),
    (AI_DEVELOP,    "内政命令",     "develop",        6),
    (AI_TRANSFER,   "武将転任",     "transfer",       1),
    (AI_REINFORCE,  "増援/兵力移動", "reinforce",     1),
    (AI_RECRUIT,    "武将登用",     "recruit",        1),
]


def count_direct_callers(target, data):
    """纯字节级 E8 rel32 直接调用方计数（0x4a70b0→0x4a84e0 这类零间接调用证据）。"""
    n = 0
    i = 0
    N = len(data)
    while i < N - 5:
        if data[i] == 0xE8:
            imm = int.from_bytes(data[i+1:i+5], 'little', signed=True)
            tgt = (BASE + i + 5 + imm) & 0xffffffff
            if tgt == target:
                n += 1
        i += 1
    return n


def self_test():
    with open(IMG, 'rb') as f:
        data = f.read()
    print("== ai_overall_ref self_test ==")
    ok = True
    def check(name, got, want, cmp=lambda a, b: a == b):
        nonlocal ok
        passed = cmp(got, want)
        ok = ok and passed
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: got {got} (want {want})")
        return passed

    check("ai_think_4a6ba0 caller count ==1", count_direct_callers(AI_THINK, data), 1)
    check("prov_dispatch_4a70b0 caller count ==1", count_direct_callers(PROV_DISPATCH, data), 1)
    check("ai_diplo_4a84e0 caller count ==2", count_direct_callers(AI_DIPLO, data), 2)
    check("ai_transfer_4a97d0 caller count ==1 (AI-only)", count_direct_callers(AI_TRANSFER, data), 1)
    check("ai_reinforce_4a92c0 caller count ==1 (AI-only)", count_direct_callers(AI_REINFORCE, data), 1)
    check("ai_recruit_4a94e0 caller count ==1 (AI-only)", count_direct_callers(AI_RECRUIT, data), 1)
    check("ai_assign_gov_4a8250 is SHARED (>=2 callers)", count_direct_callers(AI_ASSIGN_GOV, data), 2, cmp=lambda a, b: a >= b)
    check("ai_attack_4a8870 is SHARED (>=2 callers)", count_direct_callers(AI_ATTACK, data), 2, cmp=lambda a, b: a >= b)
    check("ai_develop_4a8e80 is SHARED (>=2 callers)", count_direct_callers(AI_DEVELOP, data), 2, cmp=lambda a, b: a >= b)
    check("ai_top_tick_4a0d50 has many callers (>=50)", count_direct_callers(AI_TOP_TICK, data), 50, cmp=lambda a, b: a >= b)
    print("SELF_TEST:", "ALL PASS" if ok else "FAILURES PRESENT")
    return ok


if __name__ == "__main__":
    self_test()
