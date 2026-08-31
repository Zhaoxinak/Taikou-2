#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
duel3_ref.py — 单挑「AI 选牌逻辑 + 行动派发」参考实现 (self-test)
================================================================
依据 (均来自 capstone 反汇编, 平坦映射 off=va-0x400000):

[1] AI 一击必杀决策 0x469310 (TAIZOU2)
    0x469313: tier = 0x514818 & 3
    0x469319: ecx = [esi+4]            ; 攻击者角色结构体指针
    0x46931f: dl  = [ecx+0xf] >> 6     ; 角色字段 0xf 高2位 = 熟练/技巧档
    0x469325: di  = [ecx+0xb]          ; 角色字段 0xb = 武力(强度)
    0x46932a: eax = tier*10            ; (lea eax,[eax+eax*4]; shl eax,1)
    0x469333: eax += [0x514833]        ; + 敌方体力(本攻击者视角下=对手HP)
    0x46933d: edx = (char[0xf]>>6)*10  ; (lea edx,[edx+edx*4]; shl edx,1)
    0x469341: dl  = [ecx+8]; test dl,0x20  ; 角色字段 8 的 bit5
              je  .cap:
                cmp ax,0x46; jbe .keep; mov eax,0x46   ; bit5置位: 阈值封顶 0x46(70)
                jmp .keep
    .cap:    add eax,0xa               ; bit5清零: 阈值 +10
    .keep:   cmp [ecx+0x21],0x41; jb .no   ; 角色字段 0x21 < 0x41 → 无必杀技
              cmp di,ax; jbe .no           ; strength_metric <= threshold → 不发动
              ; 发动一击必杀: 置 [esi+0x18]=1, 经 0x4663f0 执行
    条件总结:
      strength_metric = char[0xb] + ((char[0xf]>>6)*10)
      threshold       = tier*10 + enemyHP + (char[8]&0x20 ? 0 : 10)   # bit5置位再封顶70
      IKILL_OK = (char[0x21] >= 0x41) and (strength_metric > threshold)

[2] 行动代码检查 0x466470: 返回 1 当且仅当 action ∈ {3,4,5}, 否则 0
    (3=击中要害, 4=一击必杀, 5=换人/拜托)

[3] 战斗行动派发表 0x4684c0 (5 个 dword 目标, 索引=行动代码 0..4):
      0 -> 0x468457  (普通攻击)
      1 -> 0x468489  (瞄准)
      2 -> 0x468495  (快刀)
      3 -> 0x4684a0  (击中要害 -> 0x467c80)
      4 -> 0x4684a9  (一击必杀 -> 0x468000)
    (玩家菜单 0x469070 经跳表 0x46916c 把选择 0..4 派发到对应 executor:
       0x468af0 / 0x46a680 / 0x468cd0 / 0x468f00 / 0x4663f0)

[4] 通用"执行当前行动"例程 0x4663f0 (全部 5 个 executor 与 0x469310 都调用它,
    参数 push 2; push 1; push 0x5147f8）。玩家菜单回调 0x469180 负责把菜单选择
    写进 this+0xc; AI 侧 this+0xc 不显式写入 -> 默认 0 (普通攻击), 仅在一击必杀
    条件满足时由 0x469310 置 this+0x18=1 升级为必杀。
    [5] 续93: AI 行动谱 = {普通攻击(0), 一击必杀(4)} — 瞄准/快刀/击中要害/换人/威吓/挑衅/逃走
        均仅由玩家菜单经特殊子菜单 writer(0x4694a0/0x4694e0/0x469530) 触发; AI orchestrator
        0x469840 永不写 this+0xc 为非 0/4 值 (0x468860 只读不改)。

自校验: 用一组覆盖 (强弱/满血/残血/各档位/有无必杀技) 的样例验证 IKILL_OK 边界,
并校验派发表与检查表常量。
"""

# ---------- 常量 ----------
ACTION_DISPATCH = {0: 0x468457, 1: 0x468489, 2: 0x468495, 3: 0x4684a0, 4: 0x4684a9}
IKILL_ACTIONS = {3, 4, 5}          # 0x466470 返回 1 的行动
THRESH_CAP = 0x46                  # 70

# --- 续93: AI 行动谱 / 玩家特殊行动 writer 映射 (capstone + e8 全映像字节扫描) ---
# AI 在单挑中只可能选 0(普通攻击) 或 4(一击必杀); 其余特殊行动(1/2/3/5) 仅由玩家菜单触发。
AI_ACTION_REPERTOIRE = {0, 4}
# 玩家特殊行动 writer: 设 this+0xc = <param>(0x4694a0/0x4694e0) 或固定 5(0x469530);
# 调用方全部是玩家侧 (0x446dba/0x4918b8/0x4d1bba/0x448508/0x448a2c/0x447c37, 均 ecx=0x5147f8)。
PLAYER_SPECIAL_WRITERS = {
    0x4694a0: "action = <param>  (1=瞄准, 2=快刀)",
    0x4694e0: "action = <param>  (3=击中要害, 4=一击必杀); 置 0x5149b0=4",
    0x469530: "action = 5        (换人/拜托)",
    0x469480: "action = 0        (普通攻击; 零调用方 — 默认档无需 setter)",
}
# 特殊子菜单 0x468220 唯一 e8 调用方 = 0x468468 (∈ 玩家攻击 handler 0x468340 的 0x4684c0 派发内)
SPECIAL_SUBMENU_CALLER = 0x468468


def check_action_code(action: int) -> int:
    """0x466470: 行动代码 ∈ {3,4,5} -> 1 else 0."""
    return 1 if action in IKILL_ACTIONS else 0


def compute_threshold(tier: int, enemy_hp: int, char8_bit5: bool) -> int:
    """0x469310 阈值计算 (不含 0x21 / strength 比较)。"""
    t = tier * 10 + enemy_hp
    if char8_bit5:
        return min(t, THRESH_CAP)
    return t + 0xa


def ai_decide_ikill(char: dict, enemy_hp: int, tier: int) -> bool:
    """
    AI 是否发动一击必杀 (0x469310)。
    char 字段 (角色结构体偏移):
       0xb  : 武力/强度
       0xf  : 高2位 (>>6) 为熟练/技巧档
       0x8  : bit5 决定阈值是否封顶 70
       0x21 : >= 0x41 才有必杀技
    """
    strength = char[0xb] + ((char[0xf] >> 6) * 10)
    char8_bit5 = bool(char[0x8] & 0x20)
    threshold = compute_threshold(tier, enemy_hp, char8_bit5)
    return (char[0x21] >= 0x41) and (strength > threshold)


def dispatch_handler(action: int) -> int:
    """0x4684c0 派发: 返回对应 handler 地址; 非法代码抛错。"""
    if action not in ACTION_DISPATCH:
        raise ValueError(f"bad action code {action}")
    return ACTION_DISPATCH[action]


def ai_select_action(char: dict, enemy_hp: int, tier: int) -> dict:
    """
    综合 AI 选牌: 默认普通攻击(0); 满足 0x469310 条件则升级为一击必杀(置 flag)。
    返回 {action, ikill_flag}。
    (续93 已实锤: AI 单挑行动谱严格 = {普通攻击(0), 一击必杀(4)};
     瞄准/快刀/击中要害/换人/威吓/挑衅/逃走 等仅由玩家菜单经特殊子菜单 writer 触发,
     AI orchestrator 0x469840 永不写 this+0xc 为非 0/4 值。)
    """
    if ai_decide_ikill(char, enemy_hp, tier):
        return {"action": 4, "ikill_flag": 1}
    return {"action": 0, "ikill_flag": 0}


def _run_tests():
    ok = 0
    total = 0

    def check(name, cond):
        nonlocal ok, total
        total += 1
        if cond:
            ok += 1
        else:
            print(f"  FAIL: {name}")

    # --- check_action_code (0x466470) ---
    check("chk 0->0", check_action_code(0) == 0)
    check("chk 1->0", check_action_code(1) == 0)
    check("chk 2->0", check_action_code(2) == 0)
    check("chk 3->1", check_action_code(3) == 1)
    check("chk 4->1", check_action_code(4) == 1)
    check("chk 5->1", check_action_code(5) == 1)

    # --- compute_threshold ---
    # tier=0, hp=50, bit5=0 -> 0*10+50+10 = 60
    check("thr t0 hp50 nobit5 =60", compute_threshold(0, 50, False) == 60)
    # tier=2, hp=30, bit5=1 -> 2*10+30=50, 不封顶
    check("thr t2 hp30 bit5 =50", compute_threshold(2, 30, True) == 50)
    # tier=5, hp=80, bit5=1 -> 5*10+80=130 封顶 70
    check("thr cap t5 hp80 bit5 =70", compute_threshold(5, 80, True) == 70)
    # tier=3, hp=100, bit5=0 -> 30+100+10=140
    check("thr t3 hp100 nobit5=140", compute_threshold(3, 100, False) == 140)

    # --- ai_decide_ikill: 必杀技缺失 ---
    weak = {0xb: 30, 0xf: 0x00, 0x8: 0x00, 0x21: 0x30}  # 0x21<0x41
    check("no-skill never ikill (even if strong)",
          ai_decide_ikill(weak, 10, 0) is False)

    # --- ai_decide_ikill: 强势且残血 -> 必杀 ---
    strong = {0xb: 95, 0xf: 0xC0, 0x8: 0x00, 0x21: 0x50}  # 0xf>>6=3 -> +30; str=125
    # threshold = 0*10 + 5 + 10 = 15 ; 125>15 -> ikill
    check("strong+lowhp ikill", ai_decide_ikill(strong, 5, 0) is True)

    # --- ai_decide_ikill: 强势但满血 -> 不发动 ---
    # threshold = 0 + 100 + 10 = 110 ; str=125 -> 125>110 -> 仍发动? 边界
    # 用更极端样例: 满血且 threshold 很高
    strong_full = {0xb: 95, 0xf: 0xC0, 0x8: 0x20, 0x21: 0x50}
    # bit5置位: threshold = 0+200 封顶70 -> 70 ; str=125>70 -> 发动
    check("strong fullhp bit5 ikill", ai_decide_ikill(strong_full, 200, 0) is True)
    # 无bit5 满血: threshold=0+200+10=210 ; str=125 -> 125>210 False -> 不发动
    strong_full2 = {0xb: 95, 0xf: 0xC0, 0x8: 0x00, 0x21: 0x50}
    check("strong fullhp no-bit5 no-ikill", ai_decide_ikill(strong_full2, 200, 0) is False)

    # --- ai_decide_ikill: 边界 strength == threshold -> 不发动 (jbe) ---
    # 构造 strength == threshold 的情形: char[0xb]=50, 0xf>>6=0 -> str=50
    # threshold: tier=0,hp=40,bit5=0 -> 0+40+10=50 ; 50>50 False
    edge = {0xb: 50, 0xf: 0x00, 0x8: 0x00, 0x21: 0x41}
    check("edge strength==thr no-ikill", ai_decide_ikill(edge, 40, 0) is False)
    # strength = 51 > 50 -> 发动
    edge2 = {0xb: 51, 0xf: 0x00, 0x8: 0x00, 0x21: 0x41}
    check("edge strength>thr ikill", ai_decide_ikill(edge2, 40, 0) is True)

    # --- dispatch_handler ---
    check("disp 0", dispatch_handler(0) == 0x468457)
    check("disp 4", dispatch_handler(4) == 0x4684a9)
    try:
        dispatch_handler(9); check("disp bad raises", False)
    except ValueError:
        check("disp bad raises", True)

    # --- ai_select_action ---
    sel = ai_select_action(strong, 5, 0)
    check("select ikill action=4 flag=1", sel == {"action": 4, "ikill_flag": 1})
    sel2 = ai_select_action(strong_full2, 200, 0)
    check("select normal action=0 flag=0", sel2 == {"action": 0, "ikill_flag": 0})

    # --- 续93: AI 行动谱穷举 — 永远只返回 0 或 4, 且 flag 与 action 一致 ---
    import itertools
    sweep_b = [0, 40, 95]
    sweep_f = [0x00, 0x20, 0xC0]
    sweep_21 = [0x30, 0x41, 0x80]
    sweep_hp = [0, 30, 100, 200]
    sweep_tier = [0, 2, 4]
    combos = 0
    for b, f, f21, hp, tier in itertools.product(sweep_b, sweep_f, sweep_21, sweep_hp, sweep_tier):
        char = {0xb: b, 0xf: f, 0x8: (f & 0x20), 0x21: f21}
        sel = ai_select_action(char, hp, tier)
        combos += 1
        check("ai repertoire 0/4", sel["action"] in AI_ACTION_REPERTOIRE)
        check("ai flag consistent", (sel["action"] == 4) == bool(sel["ikill_flag"]))
    check("sweep nonzero combos", combos > 0)

    print(f"\nRESULT: {ok}/{total} checks passed")
    return ok, total


if __name__ == "__main__":
    ok, total = _run_tests()
    import sys
    sys.exit(0 if ok == total else 1)
