# -*- coding: utf-8 -*-
"""
太阁立志传2 · 合战「兵力消耗（attrition）」结算公式 —— 可执行参考实现

来源：TAIK2W95.exe（FuckALI 脱壳映像）静态反汇编，**非猜测**。
主函数 0x42d270（一回合结算，含兵力写回 slot.troops）。

对应原版函数：
  0x42d270  battle_round_resolve()      本文件 battle_round()
  0x42d5d0  army_strength(side)         army_strength()
  0x42d5a0  side1_strength()            side1_strength()
  0x42d730  side0_strength(pA,pB)       side0_strength()
  0x43e550  count_side0()               count_side(0)
  0x43e520  count_side1()               count_side(1)
  0x43a9c0  attack_divisor(c,a)         attack_divisor()
  0x43cd10  troop_scale(troops)         troop_scale()
  0x439050  getLo(c,a)                  sect_a_lo()
  0x4390c0  getHi(c,a)                  sect_a_hi()
  0x43e200  unit.stat_atk  (obj[0x0b])
  0x43e260  unit.stat_def  (obj[0x0a])
  0x43e220  unit.equip_tier(0..3)
  0x4ebcd0  satsub16(a,b) = max(0,a-b)
  0x4ebd10  satsub8(a,b)  = max(0,a-b)
  0x4ebc50  muldiv(a,b,c) = a*b//c   (c==0 -> 0xffff)

运行本文件会执行自检（曲线连续性 + 魔数除法一致性）。
"""
from dataclasses import dataclass, field

# ---------------------------------------------------------------- 常量表 (EXE)

# 攻击除数表。0x43a9c0 依 battle_type_flag(0x513548) 选窗口：
#   flag != 0 -> 基址 0x503770 ; flag == 0 -> 基址 0x503778
# 两窗口实为同一张 20 字节表的 +0 / +8 视图。
ATTACK_DIVISOR_TABLE = [10, 12, 15, 7, 7, 15, 100, 100,
                        10, 10, 12, 7, 7, 10, 10, 8,
                        100, 100, 12, 12]
ATTACK_DIV_WINDOW_FLAG_SET = 0    # 0x503770
ATTACK_DIV_WINDOW_FLAG_CLR = 8    # 0x503778

DEF_STAT_DIVISOR_BASE = 50        # 0x32
ATTACK_NUMERATOR = 7              # (x<<3)-x
STRENGTH_DIVISOR = 23             # 魔数 0xb21642c9 / sar 4  == //23（已数值验证）
MORALE_SCALE_DIV = 10             # m/10
EQUIP_W_CAT1, FLAT_CAT1 = 15, 20
EQUIP_W_CAT2, FLAT_CAT2 = 25, 10
MIN_UNIT_STRENGTH = 10


def satsub(a, b):
    """0x4ebcd0 / 0x4ebd10 —— 饱和减法，不会低于 0。"""
    return a - b if a > b else 0


def muldiv(a, b, c):
    """0x4ebc50"""
    return 0xffff if c == 0 else (a * b) // c


def troop_scale(troops):
    """0x43cd10 —— 兵力的边际收益递减曲线（分段线性、处处连续）。"""
    t = troops
    if t <= 100:
        return t
    if t <= 300:
        return t // 2 + 50
    if t <= 500:
        return t // 4 + 125
    if t <= 1000:
        return t // 5 + 150
    return (3 * t) // 20 + 200


# ---------------------------------------------------------------- 数据结构

@dataclass
class Unit:
    """合战单位槽。原版 = 0x513910 + i*24，共 15 槽。"""
    troops: int = 0            # +0x0c word  兵力（结算后回写）
    morale: int = 0            # +0x11 byte
    morale_loss: int = 0       # +0x12 byte
    state: int = 0             # +0x13 byte  低2位=兵种类别, 高4位!=0 表示已退场
    side_flag: int = 0         # +0x15 byte  bit2 = 阵营(0/1)
    stat_atk: int = 0          # 0x43e200  obj[0x0b]
    stat_def: int = 0          # 0x43e260  obj[0x0a]
    equip_tier: int = 0        # 0x43e220  0..3
    indirect: bool = False     # 由 [slot] 间接解析 -> stat 减半

    @property
    def active(self):
        return (self.state & 0xF0) == 0

    @property
    def category(self):
        return self.state & 3

    @property
    def side(self):
        return 1 if (self.side_flag & 4) else 0

    def atk(self):
        v = self.stat_atk
        return v >> 1 if self.indirect else v

    def dfn(self):
        v = self.stat_def
        return v >> 1 if self.indirect else v


@dataclass
class Commander:
    """大将/部队指挥对象（0x42d270 的两个指针参数）。"""
    col: int = 0        # +0x00  -> section A 列 c (0..19)
    row: int = 0        # +0x02  -> section A 行 a (0..8)
    kind: int = 0       # +0x04  两将相同 -> 额外 80% 衰减
    flags: int = 0      # +0x2c  bit4 -> 对方战力减半


@dataclass
class BattleCtx:
    units: list = field(default_factory=list)     # 15 槽
    sect_a: bytes = b''                           # HJMAPDAT section A：9x20 字节
    battle_type: int = 0        # 0x513548  选攻击除数窗口
    mode_m1: int = 0            # 0x511bf8  != 0 -> side1 免伤 & side1 战力 ÷8(配合 parity)
    mode_m2: int = 0            # 0x51352c  != 0 -> cat2 走 2/3 分支
    parity_flag: int = 0        # 0x513540 & 1
    handle_stat: int = 0        # 0x43cb50 -> [0x513534] 的 +0x0d 字节
    aux_zero: bool = True       # 0x43e870(c,a) 指向字节是否为 0


# ---------------------------------------------------------------- section A

def sect_a_lo(ctx, c, a):
    """0x439050 —— sectA[a*20 + c] & 0x0F"""
    return ctx.sect_a[a * 20 + c] & 0x0F


def sect_a_hi(ctx, c, a):
    """0x4390c0 —— sectA[a*20 + c] >> 4"""
    return ctx.sect_a[a * 20 + c] >> 4


def attack_divisor(ctx, c, a):
    """0x43a9c0 —— 依单位类型码取攻击除数，v==10 时叠加 handle_stat 修正。"""
    v = sect_a_lo(ctx, c, a)
    if ctx.battle_type != 0:
        return ATTACK_DIVISOR_TABLE[ATTACK_DIV_WINDOW_FLAG_SET + v]
    d = ATTACK_DIVISOR_TABLE[ATTACK_DIV_WINDOW_FLAG_CLR + v]
    if v == 10:
        d += ctx.handle_stat // (50 if ctx.aux_zero else 100)
    return d


# ---------------------------------------------------------------- 战力汇总

def army_strength(ctx, side):
    """0x42d5d0(side) —— 阵营战力汇总。"""
    total = [0, 0]
    for u in ctx.units:
        if not u.active:
            continue
        cat = u.category
        if cat == 1:
            v = u.atk() + EQUIP_W_CAT1 * u.equip_tier + FLAT_CAT1
        elif cat == 2:
            v = (u.atk() * 2) // 3 if ctx.mode_m2 else \
                u.atk() + EQUIP_W_CAT2 * u.equip_tier + FLAT_CAT2
        else:
            v = u.atk()
        m = satsub(u.morale, u.morale_loss)             # 0x4ebd10
        v = v * (100 + m // MORALE_SCALE_DIV) // 100
        v = max(v, MIN_UNIT_STRENGTH)
        v = v * troop_scale(u.troops) // STRENGTH_DIVISOR
        total[u.side] += v
    return total[side]


def count_side(ctx, side):
    """0x43e550 / 0x43e520 —— 该阵营存活单位数。"""
    return sum(1 for u in ctx.units if u.active and u.side == side)


def side1_strength(ctx):
    """0x42d5a0"""
    v = army_strength(ctx, 1)
    if ctx.mode_m1 and ctx.parity_flag:
        v >>= 3
    return v


def side0_strength(ctx, pA, pB):
    """0x42d730(pA,pB) —— side0 总战力，用于打 side1 的 base1。

    反汇编实证：仅 S0*4/5，若两将同类(pA.kind==pB.kind)再 *4/5。
    注意：本函数**不读取任何 flags 位**（位 0x10 / 0x40 均无关）；
    0x42b8c0 的「battle_type==0 且 parity&1 且 flags&0x40」额外减半出现在
    另一条 battle 路径，不在 0x42d270 这一回合结算里。
    """
    v = army_strength(ctx, 0)
    v = (4 * v) // 5                       # 恒定 80%
    if pA.kind == pB.kind:
        v = (4 * v) // 5                   # 同类再 80%
    return v


# ---------------------------------------------------------------- 一回合结算

def battle_round(ctx, pA, pB, extra_halve=False):
    """
    0x42d270 —— 合战一回合兵力消耗结算。就地修改 ctx.units[*].troops。

    返回 dict：各阵营伤亡数与伤亡百分比。
    """
    n0, n1 = count_side(ctx, 0), count_side(ctx, 1)
    S1 = side1_strength(ctx)
    S0 = side0_strength(ctx, pA, pB)

    # 注意：除以「对方」单位数 —— 攻击力摊薄到防守方每个单位上
    E1 = (S1 // n0) * 2 if n0 else 0
    E0 = (S0 // n1) * 2 if n1 else 0

    hiB = sect_a_hi(ctx, pB.col, pB.row)
    hiA = sect_a_hi(ctx, pA.col, pA.row)

    modB = attack_divisor(ctx, pB.col, pB.row)
    if ctx.battle_type == 0:
        if hiB > hiA:
            modB += 1
        elif hiB < hiA:
            modB -= 1
    base_vs_side0 = (E1 * ATTACK_NUMERATOR) // modB if modB else 0

    modA = attack_divisor(ctx, pA.col, pA.row)
    if ctx.battle_type == 0:
        if hiA > hiB:
            modA += 1
        elif hiA < hiB:
            modA -= 1
    base_vs_side1 = (E0 * ATTACK_NUMERATOR) // modA if modA else 0

    casualties = [0, 0]
    totals = [0, 0]
    for u in ctx.units:
        if not u.active:
            continue
        side = u.side
        totals[side] += u.troops
        base = base_vs_side0 if side == 0 else base_vs_side1
        dmg = base // (u.dfn() // 4 + DEF_STAT_DIVISOR_BASE) + 1
        if side == 1 and ctx.mode_m1:
            dmg = 0                                  # 0x42d446: side1 免伤
        remain = satsub(u.troops, dmg)
        casualties[side] += u.troops - remain
        u.troops = remain                            # 0x42d468 写回

    return {
        'casualties_side0': casualties[0],
        'casualties_side1': casualties[1],
        'loss_pct_side0': muldiv(casualties[0], 100, totals[0]),
        'loss_pct_side1': muldiv(casualties[1], 100, totals[1]),
    }


# ---------------------------------------------------------------- 自检

def _selftest():
    # 1) troop_scale 分段处处连续
    for b in (100, 300, 500, 1000):
        assert troop_scale(b) == troop_scale(b + 1), (b, troop_scale(b), troop_scale(b + 1))
    # 2) 魔数 0xb21642c9 / sar4 == //23
    def magic(x):
        hi = ((x * (0xb21642c9 - (1 << 32))) >> 32) + x
        return hi >> 4
    assert all(magic(x) == x // 23 for x in range(0, 300000, 331))
    # 3) 饱和减法
    assert satsub(5, 9) == 0 and satsub(9, 5) == 4
    # 4) 端到端跑一回合
    ctx = BattleCtx(sect_a=bytes([3] * 180))
    for i in range(4):
        ctx.units.append(Unit(troops=500, morale=80, morale_loss=10, state=1,
                              side_flag=0, stat_atk=70, stat_def=60, equip_tier=2))
    for i in range(4):
        ctx.units.append(Unit(troops=400, morale=60, morale_loss=20, state=1,
                              side_flag=4, stat_atk=55, stat_def=50, equip_tier=1))
    pA, pB = Commander(col=0, row=0, kind=1), Commander(col=1, row=0, kind=2)
    r = battle_round(ctx, pA, pB)
    assert all(u.troops >= 0 for u in ctx.units)
    assert r['casualties_side0'] > 0 and r['casualties_side1'] > 0
    print('[ok] 全部自检通过')
    print('     一回合示例：', r)
    print('     side0 剩余兵力:', [u.troops for u in ctx.units if u.side == 0])
    print('     side1 剩余兵力:', [u.troops for u in ctx.units if u.side == 1])
    print('     troop_scale 采样:', [(t, troop_scale(t)) for t in (50, 100, 300, 500, 1000, 3000)])


if __name__ == '__main__':
    _selftest()
