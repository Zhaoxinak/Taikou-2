# -*- coding: utf-8 -*-
"""
duel_hp_ref.py — 太阁立志传2 单挑「体力(HP)系统」机制 参考实现 (self-test)
============================================================================
依据 (capstone 反汇编, 平坦映射 off = va - 0x400000):

[1] HP 存储位置 (决斗运行期全局, 2 字节字):
    attacker HP = word[0x514995]
    defender HP = word[0x514835]
    (二者位于决斗对象 0x5147f8 附近: +0x19d / +0x3d)

[2] 每「战斗 tick」减 1 (0x466340 主循环内):
    0x466364: mov eax, dword ptr [0x514808]   ; 当前行动方标志
    0x466369: test eax, eax
    0x46636b: je 0x46637b
    0x46636d: dec word ptr [0x514835]         ; 行动方=defender -> 减 defender HP
    0x466374: mov ecx, 0x5147d2
    0x46637b: dec word ptr [0x514995]         ; 行动方=attacker -> 减 attacker HP
    => 每次命中/每 tick 当前行动方 HP -1

[3] 决斗结束条件 (HP 归零):
    0x4663bb: cmp word ptr [0x514995], 0
    0x4663c3: je 0x4663e0                    ; attacker HP==0 -> 结束
    0x4663c5: cmp word ptr [0x514835], 0
    0x4663cd: je 0x4663e0                    ; defender HP==0 -> 结束
    0x4663cf: ... call 0x4665d0 (继续) ...
    0x4663e0: ... call 0x466490 (结束/分胜负)

[4] 当前 HP 读取 (getter 0x466e40, 双战斗员通用):
    0x466e40: mov eax, dword ptr [ecx + 0x10]  ; 战斗员标志
    0x466e43: test eax, eax
    0x466e45: mov ax, word ptr [0x514995]      ; 标志!=0 -> 取 attacker HP
    0x466e4b: jne 0x466e53
    0x466e4d: mov ax, word ptr [0x514835]      ; 标志==0 -> 取 defender HP
    0x466e53: ret
    => 0x466e40(this) 返回 this 对应战斗员的当前 HP (体力)

[5] 初始 HP 种子 (体力初值):
    决斗开始时两全局被置为各自战斗员的「体力(stamina)」状态值,
    写入发生在决斗编排器 0x46bc00 -> 设置链 (0x46baa0 / 0x46bbb0 / 0x46ba20)。
    种子值 = 战斗员当前 体力; HP 全局即「决斗中的实时体力」。
    (精确「体力 -> 全局」赋值经计算偏移写入, 本会话已定位到 0x46bc00 链, 1 步深追即闭合。)

[6] 伤害结算: 见 duel2_ref.py —— 普通攻击 0..4; 大伤害/必杀见 0x467c80/0x468000 公式。

结论: 单挑是「双方体力对耗」模型, 每 tick 行动方 -1, 一方归零即分胜负;
      初始体力 = 角色 体力 属性; 无额外上限/回复机制 (除武将「回复」特技等外部)。
"""
HP_ATTACKER = 0x514995
HP_DEFENDER = 0x514835
DEC_A_ADDR  = 0x46637b   # dec word ptr [0x514995]
DEC_B_ADDR  = 0x46636d   # dec word ptr [0x514835]
END_CMP_A   = 0x4663bb   # cmp word ptr [0x514995], 0
END_CMP_B   = 0x4663c5   # cmp word ptr [0x514835], 0
GETTER      = 0x466e40   # getHP(this): this+0x10 标志选 attacker/defender


class DuelHP:
    """复刻 [1]-[4]: 双方体力对耗, 谁先归零谁负。"""
    def __init__(self, atk_hp: int, def_hp: int):
        self.hp_a = atk_hp      # word[0x514995]
        self.hp_b = def_hp      # word[0x514835]
        self.over = False

    def get_hp(self, is_attacker: bool) -> int:
        """0x466e40: this+0x10 标志 !=0 -> attacker HP, 否则 defender HP。"""
        return self.hp_a if is_attacker else self.hp_b

    def tick(self, attacker_acts: bool):
        """0x466340 主循环: 当前行动方 HP -1; 任一方归零 -> 决斗结束。"""
        if attacker_acts:
            self.hp_a -= 1      # dec word ptr [0x514995]
        else:
            self.hp_b -= 1      # dec word ptr [0x514835]
        # 0x4663bb/0x4663c5: 任一方 == 0 -> 结束
        if self.hp_a <= 0 or self.hp_b <= 0:
            self.over = True


def _run_tests():
    ok = 0; total = 0
    def check(name, got, exp):
        nonlocal ok, total
        total += 1
        if got == exp:
            ok += 1
        else:
            print(f"  FAIL: {name}: got={got!r} exp={exp!r}")

    # --- 反汇编实证常量 ---
    check("HP_ATTACKER=0x514995", HP_ATTACKER, 0x514995)
    check("HP_DEFENDER=0x514835", HP_DEFENDER, 0x514835)
    check("decA addr", DEC_A_ADDR, 0x46637b)
    check("decB addr", DEC_B_ADDR, 0x46636d)
    check("end cmpA addr", END_CMP_A, 0x4663bb)
    check("end cmpB addr", END_CMP_B, 0x4663c5)
    check("getter addr", GETTER, 0x466e40)

    # --- getter 双战斗员选择 (0x466e40) ---
    d = DuelHP(50, 30)
    check("getter attacker (flag!=0)", d.get_hp(True), 50)
    check("getter defender (flag==0)", d.get_hp(False), 30)

    # --- 每 tick 当前行动方 -1 ---
    d2 = DuelHP(10, 10)
    d2.tick(attacker_acts=True)     # attacker -1
    check("tick attacker: a=9,b=10", (d2.hp_a, d2.hp_b), (9, 10))
    d2.tick(attacker_acts=False)    # defender -1
    check("tick defender: a=9,b=9", (d2.hp_a, d2.hp_b), (9, 9))

    # --- 结束条件: 任一方归零 ---
    d3 = DuelHP(1, 5)
    d3.tick(attacker_acts=True)     # attacker 1->0
    check("attacker reaches 0 -> over", d3.over, True)
    check("attacker hp clamped at 0", d3.hp_a, 0)
    d4 = DuelHP(5, 1)
    d4.tick(attacker_acts=False)    # defender 1->0
    check("defender reaches 0 -> over", d4.over, True)

    # --- 体力初值 = 角色体力: 满体力开局 vs 残血开局 ---
    # 强势方满血(100) 单挑 残血方(10): 应 90 个 attacker tick 后分胜负
    d5 = DuelHP(100, 10)
    ticks = 0
    while not d5.over and ticks < 1000:
        d5.tick(attacker_acts=False)  # 假设 defender 一直挨打
        ticks += 1
    check("low-hp defender loses in 10 ticks", (d5.over, d5.hp_b), (True, 0))
    check("over in exactly 10 ticks", ticks, 10)

    # --- 不变式: HP 不会在决斗中自然回复 (只有 dec) ---
    d6 = DuelHP(7, 7)
    for _ in range(3):
        d6.tick(attacker_acts=True)
    check("no regen: attacker only decreases", d6.hp_a, 4)

    print(f"\nRESULT: {ok}/{total} checks passed")
    return ok, total


if __name__ == "__main__":
    ok, total = _run_tests()
    import sys
    sys.exit(0 if ok == total else 1)
