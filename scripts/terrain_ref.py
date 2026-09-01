
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
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
# -*- coding: utf-8 -*-
"""
太閤立志伝2 —— 地形系数系统 参考实现 (#36 / #38 CLOSED)
=====================================================

结论（2026-08-27 深夜 续7）：
游戏里**没有**独立的「地形攻防百分比矩阵」。地形对战斗的影响全部通过
**攻击除数 (attack divisor)** 实现，并与「移动消耗」共用同一套查表模板：

    f(x, y [, corps]) = TAB[ row*stride + terrainClass(x,y) ]  (+ 雪天加成)
    100 = 不可通行 / 无效

`dmg = E*7 // divisor // (def//4 + 50) + 1`  ⇒ divisor 越大伤害越低。

表全部在 EXE 静态段，可直接抄。逐字节自校验。
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = 0x400000
MEM = open(os.path.join(_HERE, _ROOT + '/scripts/_unpacked_mem.bin'), 'rb').read()


def tb(va, n):
    return list(MEM[va - BASE: va - BASE + n])


# ---------------------------------------------------------------- 静态表
# 合戦：攻击除数（伤害）
ATK_DIV_SIEGE = tb(0x503770, 8)    # battleType != 0
ATK_DIV_FIELD = tb(0x503778, 12)   # battleType == 0
# 合戦：移动消耗四张（雪天 +1 / +2）
MOVE_A = tb(0x5036a0, 8)                                        # 0x438a60, snow +1
MOVE_B = [tb(0x5036a8, 12), tb(0x5036a8 + 12, 12)]              # 0x438aa0, snow +1
MOVE_C = tb(0x5036c0, 8)                                        # 0x438af0, snow +2
MOVE_D = [tb(0x5036c8, 12), tb(0x5036c8 + 12, 12)]              # 0x438b30, snow +2
# 大地图（国内行军）移动消耗：row0=骑兵 row1=其他
MOVE_WORLD = [tb(0x503118, 9), tb(0x503118 + 9, 9)]             # 0x423070, snow +1

IMPASSABLE = 100
SNOW = 3            # word[0x513530] == 3


# ---------------------------------------------------------------- 合戦
def atk_divisor(terrain_cls, battle_type, *, facility_type=None, castle_def=0):
    """0x43a9c0 —— 防守方所在格的攻击除数。

    terrain_cls : getLo(x,y) = SECT_A[x*20+y] & 0x0F
    battle_type : byte[0x513548]
    facility_type / castle_def : 仅当 terrain_cls == 10 时使用
        facility_type = byte[facilityAt(x,y)]   0=本城 1=米仓 2=了望台 3=哨所 4=城门
        castle_def    = byte[ dword[0x513534] + 0x0d ]   （守方防御度）
    """
    if battle_type != 0:
        return ATK_DIV_SIEGE[terrain_cls]
    d = ATK_DIV_FIELD[terrain_cls]
    if terrain_cls == 0x0a:                       # 设施格
        if facility_type == 0:                    # 本城
            d += castle_def // 50
        else:
            d += castle_def // 100
    return d


def divisor_with_elevation(cls_def, elev_def, elev_atk, battle_type, **kw):
    """0x42d270 内联部分：除数取「防守方格子」，再按高度对冲 ±1（仅野战）。"""
    d = atk_divisor(cls_def, battle_type, **kw)
    if battle_type == 0:
        if elev_def > elev_atk:
            d += 1          # 守方在高处 → 除数大 → 减伤
        elif elev_def < elev_atk:
            d -= 1          # 守方在低处 → 增伤
    return d


def move_cost_battle(which, terrain_cls, weather, corps_field2c=0):
    """合戦移动消耗。which ∈ {'A','B','C','D'} 对应四个访问器。"""
    row = ((~corps_field2c) >> 2) & 1
    if which == 'A':
        c, snow = MOVE_A[terrain_cls], 1
    elif which == 'B':
        c, snow = MOVE_B[row][terrain_cls], 1
    elif which == 'C':
        c, snow = MOVE_C[terrain_cls], 2
    elif which == 'D':
        c, snow = MOVE_D[row][terrain_cls], 2
    else:
        raise ValueError(which)
    if weather == SNOW:
        c += snow
    return c


# ---------------------------------------------------------------- 大地图
def move_cost_world(terrain_cls, unit_cls, weather, elev_from, elev_to):
    """0x423070 —— 国内行军一步的消耗。

    terrain_cls : byte[0x511358 + cell]   （0..8）
    unit_cls    : byte[unit+0x13] & 3     （1 = 骑兵）
    elev_*      : byte[0x51142a + cell]
    """
    row = 0 if unit_cls == 1 else 1
    c = MOVE_WORLD[row][terrain_cls]
    if weather == SNOW:
        c += 1
    if elev_from < elev_to:
        c += 1          # 上坡
    elif elev_from > elev_to:
        c -= 1          # 下坡
    return c


# ---------------------------------------------------------------- 自校验
def _check():
    ok = True

    def eq(name, got, want):
        nonlocal ok
        if got != want:
            ok = False
            print(f'  [FAIL] {name}: {got} != {want}')
        else:
            print(f'  [OK]   {name} = {got}')

    print('-- 静态表逐字节 --')
    eq('ATK_DIV_SIEGE @0x503770', ATK_DIV_SIEGE, [10, 12, 15, 7, 7, 15, 100, 100])
    eq('ATK_DIV_FIELD @0x503778', ATK_DIV_FIELD,
       [10, 10, 12, 7, 7, 10, 10, 8, 100, 100, 12, 12])
    eq('MOVE_A @0x5036a0', MOVE_A, [3, 4, 4, 5, 5, 4, 100, 100])
    eq('MOVE_B row0', MOVE_B[0], [3, 3, 4, 12, 11, 4, 8, 9, 100, 100, 6, 20])
    eq('MOVE_B row1', MOVE_B[1], [1, 3, 4, 12, 11, 4, 8, 9, 100, 100, 6, 4])
    eq('MOVE_C @0x5036c0', MOVE_C, [1, 2, 3, 3, 3, 3, 100, 100])
    eq('MOVE_D row0', MOVE_D[0], [1, 1, 2, 12, 10, 1, 7, 9, 100, 100, 1, 100])
    eq('MOVE_D row1', MOVE_D[1], [1, 1, 2, 12, 10, 1, 7, 9, 100, 100, 1, 1])
    eq('MOVE_WORLD 骑兵', MOVE_WORLD[0], [1, 1, 1, 6, 3, 1, 100, 100, 2])
    eq('MOVE_WORLD 其他', MOVE_WORLD[1], [2, 2, 2, 6, 4, 1, 100, 100, 3])

    print('-- 攻击除数 --')
    eq('野战 平地(0)', atk_divisor(0, 0), 10)
    eq('攻城 平地(0)', atk_divisor(0, 1), 10)
    eq('野战 类2', atk_divisor(2, 0), 12)
    eq('攻城 类2', atk_divisor(2, 1), 15)
    eq('野战 不可通行类8', atk_divisor(8, 0), 100)
    eq('野战 设施格 本城 防御度80', atk_divisor(10, 0, facility_type=0, castle_def=80), 12 + 1)
    eq('野战 设施格 本城 防御度100', atk_divisor(10, 0, facility_type=0, castle_def=100), 12 + 2)
    eq('野战 设施格 城门 防御度80', atk_divisor(10, 0, facility_type=4, castle_def=80), 12 + 0)
    eq('野战 设施格 城门 防御度100', atk_divisor(10, 0, facility_type=4, castle_def=100), 12 + 1)

    print('-- 高度对冲 --')
    eq('守高攻低', divisor_with_elevation(0, 2, 1, 0), 11)
    eq('守低攻高', divisor_with_elevation(0, 1, 2, 0), 9)
    eq('同高', divisor_with_elevation(0, 1, 1, 0), 10)
    eq('攻城模式忽略高度', divisor_with_elevation(0, 2, 1, 1), 10)

    print('-- 移动消耗 --')
    eq("合戦 A 平地 晴", move_cost_battle('A', 0, 0), 3)
    eq("合戦 A 平地 雪", move_cost_battle('A', 0, SNOW), 4)
    eq("合戦 C 平地 雪", move_cost_battle('C', 0, SNOW), 3)
    eq("合戦 B row0 类11", move_cost_battle('B', 11, 0, corps_field2c=0b100), 20)
    eq("合戦 B row1 类11", move_cost_battle('B', 11, 0, corps_field2c=0b000), 4)
    eq("合戦 D row0 类11 不可通行", move_cost_battle('D', 11, 0, corps_field2c=0b100), 100)
    eq("大地图 骑兵 平地 晴 平路", move_cost_world(0, 1, 0, 5, 5), 1)
    eq("大地图 步兵 平地 晴 平路", move_cost_world(0, 0, 0, 5, 5), 2)
    eq("大地图 步兵 平地 雪 上坡", move_cost_world(0, 0, SNOW, 4, 6), 2 + 1 + 1)
    eq("大地图 步兵 平地 晴 下坡", move_cost_world(0, 0, 0, 6, 4), 1)
    eq("大地图 类6 不可通行", move_cost_world(6, 0, 0, 5, 5), 100)

    print('\n结果：' + ('全部通过' if ok else '有失败项'))
    return ok


if __name__ == '__main__':
    sys.exit(0 if _check() else 1)
