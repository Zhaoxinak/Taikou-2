# -*- coding: utf-8 -*-
# 太阁立志传2 — 单挑 5 动作码攻击分发 + 一击必杀/击中要害 大额伤害路径 参考实现
# 反汇编证据：
#   跳表 0x4684c0: [0]->0x468457(普通) [1]->0x468489(瞄准) [2]->0x468495(快刀)
#                   [3]->0x4684a0(击中要害->0x467c80) [4]->0x4684a9(一击必杀->0x468000)
#   大额公式(0x467c80/0x468000): dmg = rand%0x28 + ((0x514978>>2)&3)*10 + (0x514993//3)
#                              + (0x514995<20?+20) + ((0x514818&3)*10) + (0x51481a&0x38? //2)
#   击中要害收尾 0x467a70: 概率 ((0x514978>>2)&3)*3 % 触发暴击(置 0x51498d, MSGX 0x180e/0x1811/0x1815)
#   一击必杀收尾 0x468000: if dmg > (0x514833//3 + (0x514818&3)*10) -> 瞬杀([esi+0x18] 置位, MSGX 0x1823)
import sys, random

# ---- 跳表 ----
JUMP_TABLE = 0x4684c0
HANDLERS = {
    0: 0x468457,  # 普通攻击
    1: 0x468489,  # 瞄准
    2: 0x468495,  # 快刀
    3: 0x4684a0,  # 击中要害
    4: 0x4684a9,  # 一击必杀
}
ACTION_NAMES = {0:"普通攻击",1:"瞄准",2:"快刀",3:"击中要害",4:"一击必杀"}

# 战斗运行期全局（来源反汇编里的 0x514xxx 地址），建模为字段
class DuelGlobals:
    def __init__(self, g978=0, g993=0, g833=0, g818=0, g81a=0, g995=0):
        self.g514978 = g978   # >>2 &3 = 系数A / 暴击概率基数
        self.g514993 = g993   # //3 加伤
        self.g514833 = g833   # 一击必杀瞬杀阈值用 //3
        self.g514818 = g818   # &3 = 系数B (大额公式 & 瞬杀阈值)
        self.g51481a = g81a   # &0x38 -> 伤害减半
        self.g514995 = g995   # <20 -> +20

def large_damage(rng, G):
    """复刻 0x467c80/0x468000 大额公式。返回 (dmg, halved)"""
    dmg = rng.randint(0, 39)                       # rand() % 0x28 (40)
    A = (G.g514978 >> 2) & 3
    dmg += A * 10                                   # (514978>>2)&3 * 10
    dmg += G.g514993 // 3                          # 514993 / 3
    if G.g514995 < 0x14:                           # 514995 < 20
        dmg += 0x14                                # +20
    B = G.g514818 & 3
    dmg += B * 10                                   # (514818 & 3) * 10
    halved = bool(G.g51481a & 0x38)
    if halved:
        dmg //= 2
    return dmg, halved

def crit_roll(rng, G):
    """复刻 0x467a70: 概率门 0x4ebe40(((514978>>2)&3)*3) -> True 为暴击"""
    p = ((G.g514978 >> 2) & 3) * 3                  # 0..9 (%)
    return rng.randint(0, 99) < p

def attack_damage(action, rng, G):
    """单挑攻击伤害总管。返回 dict。"""
    if action not in HANDLERS:
        raise ValueError("bad action")
    if action == 0:
        # 普通攻击：旧三段式，伤害域 0..4（此处仅占位，详细见 duel_ref.py）
        dmg = rng.randint(0, 4)
        return {"action": action, "name": ACTION_NAMES[action], "damage": dmg,
                "large": False, "crit": False, "instakill": False}
    if action in (1, 2):
        # 瞄准/快刀：非直接大额伤害路径（特效 + 台词），伤害走普通域
        dmg = rng.randint(0, 4)
        return {"action": action, "name": ACTION_NAMES[action], "damage": dmg,
                "large": False, "crit": False, "instakill": False}
    # action 3 (击中要害) / 4 (一击必杀)
    dmg, halved = large_damage(rng, G)
    crit = False
    instakill = False
    if action == 3:
        crit = crit_roll(rng, G)                    # 0x467a70 概率暴击
    else:  # action == 4
        threshold = G.g514833 // 3 + (G.g514818 & 3) * 10
        if dmg > threshold:                        # 0x468111 cmp cx,dx; jbe skip
            instakill = True
    return {"action": action, "name": ACTION_NAMES[action], "damage": dmg,
            "large": True, "crit": crit, "instakill": instakill,
            "halved": halved}

def dispatch(action):
    """复刻跳表 0x4684c0 索引 -> handler 地址"""
    return HANDLERS[action]


# =================== 自校验 ===================
def self_test():
    import io
    buf = io.StringIO()
    ok = 0; total = 0
    def check(name, got, exp):
        nonlocal ok, total
        total += 1
        if got == exp:
            ok += 1
            buf.write("[OK  ] %s: got=%s\n" % (name, got))
        else:
            buf.write("[FAIL] %s: got=%s exp=%s\n" % (name, got, exp))

    # 1) 跳表映射
    check("dispatch-0", dispatch(0), 0x468457)
    check("dispatch-3", dispatch(3), 0x4684a0)
    check("dispatch-4", dispatch(4), 0x4684a9)

    # 2) 大额公式：确定性（固定 rng + 固定 G）
    class Fixed:
        def __init__(self, v): self.v = v
        def randint(self, a, b):
            # 返回 (a+b)//2 以稳定测试
            return (a + b) // 2
    G = DuelGlobals(g978=0x0c, g993=30, g833=60, g818=2, g81a=0, g995=10)
    # rand%40 mid = 19; A=(0x0c>>2)&3=3 ->30; g993//3=10; g995<20->+20; B=(2&3)=2->20; g81a&0x38=0 ->no half
    dmg, halved = large_damage(Fixed(0), G)
    check("large-dmg", dmg, 19 + 30 + 10 + 20 + 20)
    check("large-half-false", halved, False)

    # 3) 减半分支：g81a & 0x38 置位 -> 减半
    G2 = DuelGlobals(g978=0, g993=0, g833=0, g818=0, g81a=0x38, g995=0x20)
    dmg2, h2 = large_damage(Fixed(0), G2)
    # rand%40 mid=19; A=0; g993//3=0; g995>=20 no; B=0; half -> 19//2=9
    check("large-half-true", (dmg2, h2), (9, True))

    # 4) g995 边界：<20 加 20，>=20 不加
    G3a = DuelGlobals(g995=19); G3b = DuelGlobals(g995=20)
    dA,_ = large_damage(Fixed(0), G3a); dB,_ = large_damage(Fixed(0), G3b)
    check("g995-bound", dA - dB, 20)

    # 5) 暴击概率：p=((0x0c>>2)&3)*3 = 3*3 = 9% ; 用确定 rng 中值 49 -> 49<9 False
    check("crit-roll-true-fixed", crit_roll(Fixed(0), DuelGlobals(g978=0x0c)), False)
    # p=0 (g978=0) -> 永远不暴击
    check("crit-roll-p0", crit_roll(Fixed(0), DuelGlobals(g978=0)), False)

    # 6) 一击必杀瞬杀阈值：dmg > (g833//3 + (g818&3)*10)
    # 设 G 使 dmg=100, threshold= (60//3 + (2)*10)=20+20=40 -> 100>40 True
    Gk = DuelGlobals(g978=0, g993=0, g833=60, g818=2, g81a=0, g995=0x20)
    r = attack_damage(4, Fixed(100), Gk)   # 注意 Fixed.randint 被 attack_damage 内部调用，但我们已定 mid
    # Fixed.randint(0,39)=19 仍生效；dmg=19+0+0+0+20=39; threshold=40 -> 39>40 False
    check("instakill-false", r["instakill"], False)
    # 提高 dmg：用定 rng 返回高值
    class FixedHi:
        def randint(self,a,b): return b   # 39
    Gk2 = DuelGlobals(g978=0, g993=0, g833=60, g818=2, g81a=0, g995=0x20)
    r2 = attack_damage(4, FixedHi(), Gk2)
    # dmg=39+0+0+0+20=59; threshold=40 -> 59>40 True
    check("instakill-true", r2["instakill"], True)

    # 7) 普通/瞄准/快刀 非大额
    for a in (0,1,2):
        r = attack_damage(a, Fixed(0), G)
        check("non-large-%d"%a, r["large"], False)

    # 8) 动作码边界：非法值抛错
    try:
        dispatch(5); check("bad-action", "no-exc", "exc")
    except (KeyError, ValueError):
        check("bad-action", "exc", "exc")

    buf.write("\nself_test: %d/%d %s\n" % (ok, total, "ALL PASS" if ok==total else "FAILED"))
    out = buf.getvalue()
    with open(r"F:/Games/Taikou 2/scripts/_duel2_selftest.txt", "w", encoding="utf-8") as f:
        f.write(out)
    print(out)
    return ok == total

if __name__ == "__main__":
    if "--dump" in sys.argv:
        print("duel2_ref loaded; JUMP_TABLE=0x%X handlers=%d" % (JUMP_TABLE, len(HANDLERS)))
    else:
        sys.exit(0 if self_test() else 1)
