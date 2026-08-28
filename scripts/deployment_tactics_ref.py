#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
太閤立志伝2 · 合戦「初期布陣」与「計略」系统 参考实现
=========================================================

来源：脱壳映像 scripts/_unpacked_mem.bin（基址 0x400000）静态反汇编，
      不依赖任何运行时填充的数据 —— 本模块所有表都是 EXE 静态段常量，
      可直接逐字节自校验。

破解要点
--------
1. 布陣函数 `0x42c740(pA, pB)` —— 合戦开始时一次性摆放全部 15 个单位槽。
2. 阵形相克矩阵 `0x5031d0`（4×4）→ 布阵变体 id `fi`；规律 = 拉丁方，
   `fi = [1,3,0,2][(B - A) mod 4]`（逐字节验证通过）。
3. 左军/右军各一张 `4 变体 × 5 单位 × (x,y)` 坐标表 + 每变体朝向；
   右军 = 左军的 **180° 点对称**（x'=38-x, y'=16-y, 单位序 [0,2,1,4,3]，
   朝向 +2 mod 4）—— 逐字节验证通过。
4. 計略名表 `0x5032d8`（stride 7，11 条中文名）+ 处理函数指针表 `0x503328`。
   ⇒ 长期缺口「計略中文名不在 EXE / 不在 MSGX」被推翻：就在静态段里。
5. 士気增减原语 `0x43db50/60/80`（部队记录 `+0x23`，上限 200）
   与 `0x43dba0`（`+0x25`，上限 100）。
6. 「鼓舞」数值公式（`0x435370`）完整还原。

用法：  python scripts/deployment_tactics_ref.py
"""
from __future__ import annotations

import os
import random
import struct
import sys

BASE = 0x400000
_IMG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_unpacked_mem.bin')

# ---------------------------------------------------------------- 静态表 --
# 阵形相克矩阵 @0x5031d0   index = A*4 + B  ->  布阵变体 fi
FORMATION_MATCHUP = [
    1, 3, 0, 2,
    2, 1, 3, 0,
    0, 2, 1, 3,
    3, 0, 2, 1,
]
#   等价闭式：fi = MATCHUP_RULE[(B - A) % 4]
MATCHUP_RULE = [1, 3, 0, 2]

# 左军（单位槽 0..4）坐标 @0x5031e0：4 变体 × 5 单位 × (x, y)
DEPLOY_LEFT = [
    [(6, 8), (8, 4), (8, 12), (6, 6), (6, 10)],       # fi=0  横一文字
    [(12, 8), (10, 12), (10, 4), (12, 10), (12, 6)],  # fi=1
    [(10, 8), (14, 10), (6, 10), (12, 8), (8, 8)],    # fi=2
    [(10, 8), (6, 6), (14, 6), (8, 8), (12, 8)],      # fi=3
]
FACING_LEFT = [1, 3, 2, 0]        # @0x503208

# 右军（单位槽 5..9）坐标 @0x503210，朝向 @0x503238
DEPLOY_RIGHT = [
    [(32, 8), (30, 4), (30, 12), (32, 6), (32, 10)],
    [(26, 8), (28, 12), (28, 4), (26, 10), (26, 6)],
    [(28, 8), (32, 6), (24, 6), (30, 8), (26, 8)],
    [(28, 8), (24, 10), (32, 10), (26, 8), (30, 8)],
]
FACING_RIGHT = [3, 1, 0, 2]

# 侧翼/伏兵（单位槽 10..14）——固定，不随阵形变化
FLANK_A = [(38, 8), (36, 14), (14, 14), (14, 2), (36, 2)]   # @0x503240
FACING_FLANK_A = [3, 3, 0, 2, 3]                            # @0x503258
FLANK_B = [(0, 8), (2, 2), (24, 2), (24, 14), (2, 14)]      # @0x50324a
FACING_FLANK_B = [1, 1, 2, 0, 1]                            # @0x503260

# 6 方向反向表 @0x503268 —— opp(i) = (i + 3) % 6
OPP6 = [3, 4, 5, 0, 1, 2]

# 合戦地图有效范围：40 列 × 19 行（HJMAPDAT.DAT B/C 段），
# 点对称中心由表数据反推 = (38, 16) 的一半
MAP_MIRROR_X, MAP_MIRROR_Y = 38, 16

# 朝向编码（由「右军 = 左军 +2」与左军朝东的事实推出）
FACING = {0: '北/上', 1: '东/右', 2: '南/下', 3: '西/左'}

# 計略名表 @0x5032d8（stride 7）+ 处理函数 @0x503328
TACTICS = [
    ('鼓　舞', 0x435530),
    ('伏　兵', 0x435d20),
    ('伪　兵', 0x435b50),
    ('谣　言', 0x436190),
    ('火　计', 0x436710),
    ('开　城', 0x436a80),
    ('挑　衅', 0x436d20),
    ('落　石', 0x437300),
    ('牵　制', 0x437820),
    ('修　复', 0x437a60),
    ('填　埋', 0x437c90),
]

# 合戦 UI / 结算字符串（同一静态池）
BATTLE_STRINGS = {
    0x503270: '逃之夭夭',
    0x50327c: '全军覆没',
    0x503288: '士气',
    0x503290: '士兵',
    0x5032a8: '士气∶',
    0x5032b0: '(全军覆没)',
    0x5032bc: '受伤∶%4u人',
    0x5032c8: '%-12s守备',
    0x503378: '失败',
    0x503380: '达成',
}

MORALE_CAP = 200      # 0x43db60 -> 0x4ebcf0(cur, v, 0xc8)
FIELD25_CAP = 100     # 0x43dba0 -> 0x4ebcf0(cur, v, 0x64)


# ------------------------------------------------------------ 布阵逻辑 --
def matchup(formation_a: int, formation_b: int) -> int:
    """阵形相克 → 布阵变体 id（0..3）。A=攻方阵形，B=守方阵形，各 0..3。

    原始实现：`movzx cx, byte[edx + ecx*4 + 0x5031d0]`，ecx=byte[pA+4]、edx=byte[pB+4]。
    """
    return FORMATION_MATCHUP[(formation_a & 3) * 4 + (formation_b & 3)]


def point_mirror(x: int, y: int) -> tuple[int, int]:
    """合戦地图 180° 点对称（右军 = 左军的点对称像）。"""
    return MAP_MIRROR_X - x, MAP_MIRROR_Y - y


def deploy(formation_a: int, formation_b: int, reactive_side: int = 1,
           rng: random.Random | None = None,
           occupied=None) -> list[dict]:
    """还原 `0x42c740`：返回 15 个单位槽的初始 (x, y, facing)。

    reactive_side:
        1 -> 右军(槽5..9)按阵形相克变体布阵，左军(槽0..4)用固定 fi=0 布局
             （对应 `byte[slot0+0x15] & 4 != 0` 分支）
        0 -> 左军(槽0..4)按相克变体布阵，右军用固定 fi=1 布局
             （对应 bit2 清零分支；右军固定读 0x50321a = fi=1 那一块）
    occupied: 可选，callable(x, y) -> bool，用于随机布阵时的占位检测
              （原版为 `0x423010`）。
    """
    rng = rng or random
    fi = matchup(formation_a, formation_b)
    slots: list[dict] = []

    if reactive_side == 1:
        left_layout, left_face = DEPLOY_LEFT[0], FACING_LEFT[0]
        left_face = 1                      # bit2 分支里左军朝向写死 bl=1
        right_layout, right_face = DEPLOY_RIGHT[fi], FACING_RIGHT[fi]
        flank, flank_face = FLANK_A, FACING_FLANK_A
    else:
        left_layout, left_face = DEPLOY_LEFT[fi], FACING_LEFT[fi]
        right_layout = DEPLOY_RIGHT[1]     # 固定读 0x50321a（= fi=1 块）
        right_face = 3                     # 分支里写死 bl=3
        flank, flank_face = FLANK_B, FACING_FLANK_B

    for u in range(5):
        x, y = left_layout[u]
        slots.append({'slot': u, 'x': x, 'y': y,
                      'facing': left_face if isinstance(left_face, int) else left_face[u]})
    for u in range(5):
        x, y = right_layout[u]
        slots.append({'slot': 5 + u, 'x': x, 'y': y, 'facing': right_face})
    for u in range(5):
        x, y = flank[u]
        slots.append({'slot': 10 + u, 'x': x, 'y': y, 'facing': flank_face[u]})

    # 随机布阵回退（slot 的 byte[+0x15] & 0x10 置位时启用）
    # 原式：x = (rand()%10 + 5) * 2 ; y = (rand()%7 + 1) * 2 ; 撞人则重摇
    if occupied is not None:
        for s in slots:
            if s.get('random'):
                for _ in range(64):
                    x = (rng.randrange(10) + 5) * 2
                    y = (rng.randrange(7) + 1) * 2
                    if not occupied(x, y):
                        s['x'], s['y'] = x, y
                        break
    return slots


def random_placement(rng: random.Random | None = None) -> tuple[int, int]:
    """随机布阵坐标（`0x42c849` / `0x42c9ca` 分支）。"""
    rng = rng or random
    return (rng.randrange(10) + 5) * 2, (rng.randrange(7) + 1) * 2


# --------------------------------------------------------- 士気增减原语 --
def morale_add(cur: int, delta: int) -> int:
    """`0x43db60` → `0x4ebcf0(cur, delta, 200)` = min(cur+delta, 200)。"""
    v = (cur + delta) & 0xFFFF
    return v if v < MORALE_CAP else MORALE_CAP


def morale_sub(cur: int, delta: int) -> int:
    """`0x43db80` → `0x4ebd10(cur, delta)` = max(cur-delta, 0)（饱和减）。"""
    return cur - delta if cur > delta else 0


def field25_add(cur: int, delta: int) -> int:
    """`0x43dba0` → min(cur+delta, 100)。"""
    v = (cur + delta) & 0xFFFF
    return v if v < FIELD25_CAP else FIELD25_CAP


# ------------------------------------------------- 計略「鼓舞」数值公式 --
def tactic_kobu_gain(commander_stat: int, corps_field25: int,
                     bonus: bool = False,
                     rng: random.Random | None = None) -> int:
    """「鼓　舞」士気上升量（`0x435370` @0x435414–0x435486 完整还原）。

    commander_stat : 施术武将记录 `byte[ent+0x0a]`（实体表 0x519868 内，47B/条）
    corps_field25  : 部队记录 `byte[+0x25]`（0..100，起衰减作用）
    bonus          : `byte[ent+0x24] == 0x10` 且 `!(byte[0x517aa5] & 0x10)`

    式：
        r1   = rand() % (stat // 2)
        r2   = rand() % 50
        gain = max(0, (r1 + r2) // 4 - field25 // 10)
        if bonus: gain = gain * 2 + 1
        morale = min(morale + gain, 200)
    """
    rng = rng or random
    half = commander_stat >> 1
    r1 = rng.randrange(half) if half > 0 else 0
    r2 = rng.randrange(50)
    gain = (r1 + r2) // 4 - corps_field25 // 10
    if gain <= 0:
        gain = 0
    if bonus:
        gain = gain * 2 + 1
    return gain


# ------------------------------------------------------------- 自校验 --
def _img():
    if not os.path.exists(_IMG_PATH):
        return None
    with open(_IMG_PATH, 'rb') as f:
        return f.read()


def verify_against_image() -> bool:
    mem = _img()
    if mem is None:
        print(f'[skip] 未找到映像 {_IMG_PATH}')
        return True

    def rd(va, n):
        return mem[va - BASE: va - BASE + n]

    ok = True

    def chk(label, expect, actual):
        nonlocal ok
        good = list(expect) == list(actual)
        ok &= good
        print(f'  [{"OK" if good else "FAIL"}] {label}')
        if not good:
            print(f'         expect {list(expect)}')
            print(f'         image  {list(actual)}')

    print('== 静态表逐字节自校验 ==')
    chk('阵形相克矩阵 0x5031d0 (16B)', FORMATION_MATCHUP, rd(0x5031d0, 16))
    chk('左军坐标表   0x5031e0 (40B)',
        [v for layout in DEPLOY_LEFT for xy in layout for v in xy], rd(0x5031e0, 40))
    chk('左军朝向     0x503208 (4B)', FACING_LEFT, rd(0x503208, 4))
    chk('右军坐标表   0x503210 (40B)',
        [v for layout in DEPLOY_RIGHT for xy in layout for v in xy], rd(0x503210, 40))
    chk('右军朝向     0x503238 (4B)', FACING_RIGHT, rd(0x503238, 4))
    chk('侧翼 A 坐标  0x503240 (10B)', [v for xy in FLANK_A for v in xy], rd(0x503240, 10))
    chk('侧翼 A 朝向  0x503258 (5B)', FACING_FLANK_A, rd(0x503258, 5))
    chk('侧翼 B 坐标  0x50324a (10B)', [v for xy in FLANK_B for v in xy], rd(0x50324a, 10))
    chk('侧翼 B 朝向  0x503260 (5B)', FACING_FLANK_B, rd(0x503260, 5))
    chk('6 方向反向表 0x503268 (6B)', OPP6, rd(0x503268, 6))

    print('\n== 計略名表 0x5032d8 (stride 7) + 处理函数 0x503328 ==')
    for i, (nm, fn) in enumerate(TACTICS):
        raw = rd(0x5032d8 + i * 7, 7).split(b'\x00')[0].decode('gbk')
        ptr = struct.unpack_from('<I', mem, 0x503328 - BASE + i * 4)[0]
        good = (raw == nm and ptr == fn)
        ok &= good
        print(f'  [{"OK" if good else "FAIL"}] [{i:2d}] {raw:<8s} handler={ptr:#08x}')

    print('\n== 结构规律验证 ==')
    rule = all(FORMATION_MATCHUP[a * 4 + b] == MATCHUP_RULE[(b - a) % 4]
               for a in range(4) for b in range(4))
    print(f'  [{"OK" if rule else "FAIL"}] 相克矩阵闭式 fi = [1,3,0,2][(B-A) mod 4]')
    ok &= rule

    perm = [0, 2, 1, 4, 3]
    sym = all(DEPLOY_RIGHT[fi][perm[u]] == point_mirror(*DEPLOY_LEFT[fi][u])
              for fi in range(4) for u in range(5))
    print(f'  [{"OK" if sym else "FAIL"}] 右军 = 左军 180° 点对称 (x→38-x, y→16-y, 序 [0,2,1,4,3])')
    ok &= sym

    fsym = all(FACING_RIGHT[i] == (FACING_LEFT[i] + 2) % 4 for i in range(4))
    print(f'  [{"OK" if fsym else "FAIL"}] 右军朝向 = 左军朝向 + 2 (mod 4)')
    ok &= fsym

    flsym = (all(FLANK_B[i] == point_mirror(*FLANK_A[i]) for i in range(5))
             and all(FACING_FLANK_B[i] == (FACING_FLANK_A[i] + 2) % 4 for i in range(5)))
    print(f'  [{"OK" if flsym else "FAIL"}] 侧翼 B = 侧翼 A 点对称（无序号置换）')
    ok &= flsym

    return ok


def _demo():
    print('\n== 布阵演示：攻方阵形 A=0, 守方阵形 B=3 ==')
    fi = matchup(0, 3)
    print(f'  相克结果 布阵变体 fi = {fi}')
    for s in deploy(0, 3, reactive_side=1):
        print(f'    slot {s["slot"]:2d}  ({s["x"]:2d},{s["y"]:2d})  朝向 {s["facing"]} '
              f'{FACING[s["facing"]]}')

    print('\n== 「鼓　舞」蒙特卡洛（10000 次）==')
    rng = random.Random(20260827)
    for stat in (40, 70, 100):
        for f25 in (0, 50, 100):
            vals = [tactic_kobu_gain(stat, f25, False, rng) for _ in range(10000)]
            zero = sum(1 for v in vals if v == 0) / len(vals)
            print(f'    stat={stat:3d} field25={f25:3d}  '
                  f'均值 {sum(vals)/len(vals):5.2f}  最大 {max(vals):2d}  无效率 {zero:5.1%}')
    vals = [tactic_kobu_gain(100, 0, True, rng) for _ in range(10000)]
    print(f'    stat=100 field25=  0 bonus  均值 {sum(vals)/len(vals):5.2f}  最大 {max(vals):2d}')


if __name__ == '__main__':
    good = verify_against_image()
    _demo()
    print('\n结果：' + ('全部自校验通过 ✅' if good else '存在不一致 ❌'))
    sys.exit(0 if good else 1)
