# -*- coding: utf-8 -*-
"""
太阁立志传2 — HJMAPDAT section A 结构重定性（续67）

🔴 **推翻原假设**：section A 不是「9 类实体 × 20 属性」的参数矩阵，
   而是 **20 列 × 9 行的空间网格**（deploy 图的半分辨率逻辑网格）。

依据：
  1. 存在确定的空间映射公式（sectA_spec 已记，本轮独立复算确认）：
        off  = (col<<1) + 40*((col&1)^1) + 80*row
     等价于 deploy 图坐标：
        X = 2*col                    （只取偶数列）
        Y = 2*row + ((col&1) ^ 1)    （按 col 奇偶交错行）
  2. 与 deploy 图相关性显著高于随机基线：
        deploy 非空(≠0xFF) → sectA≠0 :  61.9%
        deploy 空  (=0xFF) → sectA==0:  79.1%
     （随机基线约 36% / 64%）
  3. 🚫 证伪「section A = terrain 降采样」：同位置 terrain code 低4位
     与 sectA 值一致率仅 **9.8%**（668/6840）。
  4. 🚫 纠偏：sectA_spec 声明的「99.5% populated cell 落非空 deploy 字符」
     **不成立**，实测仅 61.9%。
  5. 值 1 的格子 100% 对应 deploy 的**部队字符**（可打印 ASCII 0x30–0x5A），
     说明值 1 = 部队占据格；其余值为其它地形/内容分类。

仍未闭合：9 行 / 20 列的中文命名；值 0..7 的玩法语义。
"""
import os
import collections

NB = 1700                       # 每战场字节数
SECTA_OFF, SECTA_LEN = 0, 180   # 9×20
TERR_OFF, TERR_LEN = 180, 760   # 40×19
DEP_OFF, DEP_LEN = 940, 760     # 40×19
MAP_W, MAP_H = 40, 19
ROWS, COLS = 9, 20

DAT_CANDIDATES = (
    'Taikou2 Original/HJMAPDAT.DAT',
    os.path.join('Taikou2 Original', 'HJMAPDAT.DAT'),
)


def load_battles(root='.'):
    """读 HJMAPDAT.DAT，返回 [(sectA_bytes, terrain_bytes, deploy_bytes), ...]"""
    path = None
    for c in DAT_CANDIDATES:
        p = os.path.join(root, c)
        if os.path.isfile(p):
            path = p
            break
    if path is None:
        return None
    data = open(path, 'rb').read()
    if len(data) < NB:
        return None
    n = len(data) // NB
    out = []
    for i in range(n):
        b = data[i * NB:(i + 1) * NB]
        out.append((b[SECTA_OFF:SECTA_OFF + SECTA_LEN],
                    b[TERR_OFF:TERR_OFF + TERR_LEN],
                    b[DEP_OFF:DEP_OFF + DEP_LEN]))
    return out


# ---------------------------------------------------------------- 映射
def deploy_offset(row, col):
    """section A (row,col) → deploy 图展平偏移"""
    return (col << 1) + MAP_W * ((col & 1) ^ 1) + (MAP_W * 2) * row


def deploy_yx(row, col):
    """section A (row,col) → deploy 图 (y, x)"""
    return (2 * row + ((col & 1) ^ 1), 2 * col)


def secta_value(sectA, row, col):
    """getLo 语义：低 4 位"""
    return sectA[row * COLS + col] & 0xF


def secta_row(sectA, row):
    return [secta_value(sectA, row, c) for c in range(COLS)]


# ---------------------------------------------------------------- 分析
def coverage(battles):
    """返回 (deploy非空→sectA≠0, deploy空→sectA==0)"""
    n_ns = n_ns_hit = n_sp = n_sp_hit = 0
    for sectA, _terr, dep in battles:
        for r in range(ROWS):
            for c in range(COLS):
                y, x = deploy_yx(r, c)
                o = y * MAP_W + x
                if o >= len(dep):
                    continue
                sv = secta_value(sectA, r, c)
                if dep[o] != 0xFF:
                    n_ns += 1
                    n_ns_hit += (sv != 0)
                else:
                    n_sp += 1
                    n_sp_hit += (sv == 0)
    return (n_ns_hit / n_ns if n_ns else 0.0,
            n_sp_hit / n_sp if n_sp else 0.0, n_ns, n_sp)


def terrain_agreement(battles):
    """sectA 值 vs 同位置 terrain code 低4位 一致率"""
    hit = tot = 0
    for sectA, terr, _dep in battles:
        for r in range(ROWS):
            for c in range(COLS):
                y, x = deploy_yx(r, c)
                o = y * MAP_W + x
                if o >= len(terr):
                    continue
                tot += 1
                hit += (secta_value(sectA, r, c) == (terr[o] & 0xF))
    return hit / tot if tot else 0.0, hit, tot


def value_vs_deploy(battles):
    """每个 sectA 值对应的 deploy 字节分布（用于判定值语义）"""
    byval = collections.defaultdict(collections.Counter)
    for sectA, _t, dep in battles:
        for r in range(ROWS):
            for c in range(COLS):
                y, x = deploy_yx(r, c)
                o = y * MAP_W + x
                if o >= len(dep):
                    continue
                byval[secta_value(sectA, r, c)][dep[o]] += 1
    return byval


# ---------------------------------------------------------------- 8 类战斗地形类
ATK_DIV_SIEGE = 0x503770      # 8B  攻城战
ATK_DIV_FIELD = 0x503778      # 12B 野战
MV_A = 0x5036a0               # 8B  合战移动 +1雪
MV_B = 0x5036a8               # 12B×2
MV_C = 0x5036c0               # 8B  +2雪
MV_D = 0x5036c8               # 12B×2

IMPASSABLE = 100

# 🔶 推断命名（基于数值特征，EXE 内**无**主名表 —— 见下方 falsification）
INFERRED_NAMES = {
    0: '平地/街道', 1: '荒地', 2: '草地·森（高防御）',
    3: '河川·浅滩', 4: '河川·湿地', 5: '山地·丘陵（高防御）',
    6: '城壁·本城（攻城不可入）', 7: '城门·设施（攻城不可入）',
}


def read_tables(img_root='.'):
    """从 EXE 映像读 5 张系数表；映像缺失返回 None"""
    try:
        IMG = open(os.path.join(img_root, 'scripts', '_unpacked_mem.bin'), 'rb').read()
    except OSError:
        return None
    b = 0x400000

    def rd(va, n):
        return list(IMG[va - b:va - b + n])
    return {
        'atk_siege': rd(ATK_DIV_SIEGE, 8),
        'atk_field': rd(ATK_DIV_FIELD, 12),
        'mv_a': rd(MV_A, 8),
        'mv_b0': rd(MV_B, 12),
        'mv_b1': rd(MV_B + 12, 12),
        'mv_c': rd(MV_C, 8),
        'mv_d0': rd(MV_D, 12),
        'mv_d1': rd(MV_D + 12, 12),
    }


def class_profile(tabs, cls):
    """返回该类在攻城/野战下的 (攻城除数, 野战除数, 移动A, 移动B行0, 移动C)"""
    return (tabs['atk_siege'][cls], tabs['atk_field'][cls] if cls < 12 else None,
            tabs['mv_a'][cls], tabs['mv_b0'][cls] if cls < 12 else None,
            tabs['mv_c'][cls])


# ================================================================ 自校验
def self_test(root='.'):
    ok = fail = 0

    def chk(name, got, exp):
        nonlocal ok, fail
        if got == exp:
            ok += 1
            print('[OK  ] %-52s got=%r' % (name, got))
        else:
            fail += 1
            print('[FAIL] %-52s got=%r exp=%r' % (name, got, exp))

    print('=' * 78)
    print('sectA2_ref self_test — section A 结构重定性（空间网格）')
    print('=' * 78)

    # --- 1. 索引公式（不依赖数据）---
    chk('getLow 索引 col + row*20', 3 + 2 * 20, 43)
    chk('映射公式 col=0,row=0 → off', deploy_offset(0, 0), (0 << 1) + 40 * 1 + 80 * 0)
    chk('映射公式 col=1,row=0 → off', deploy_offset(0, 1), (1 << 1) + 40 * 0 + 80 * 0)
    chk('映射公式 col=19,row=8 → 在界内',
        deploy_offset(8, 19) < MAP_W * MAP_H, True)
    chk('坐标 col=0,row=0 → (y,x)', deploy_yx(0, 0), (1, 0))
    chk('坐标 col=1,row=0 → (y,x)', deploy_yx(0, 1), (0, 2))
    chk('坐标 col=3,row=2 → (y,x)', deploy_yx(2, 3), (4, 6))
    chk('col 偶 → Y 奇', deploy_yx(0, 4)[0] % 2, 1)
    chk('col 奇 → Y 偶', deploy_yx(0, 5)[0] % 2, 0)
    chk('X 只取偶数列', all(deploy_yx(r, c)[1] % 2 == 0
                            for r in range(ROWS) for c in range(COLS)), True)

    b = load_battles(root)
    if not b:
        print('[SKIP] 未找到 HJMAPDAT.DAT，跳过数据驱动断言')
        print('-' * 78)
        print('self_test: %d/%d %s' % (ok, ok + fail, 'ALL PASS' if fail == 0 else 'HAS FAILURE'))
        return fail == 0

    print('   （读得 %d 个战场记录）' % len(b))

    # --- 2. 数据规模 ---
    chk('战场数', len(b), 38)
    chk('sectA 长度', len(b[0][0]), 180)
    chk('terrain 长度', len(b[0][1]), 760)
    chk('deploy 长度', len(b[0][2]), 760)

    # --- 3. 🚫 证伪：sectA ≠ terrain 降采样 ---
    agree, hit, tot = terrain_agreement(b)
    chk('证伪 terrain 降采样（一致率应 < 20%）', agree < 0.20, True)
    print('        ↳ 实测一致率 %.1f%% (%d/%d)' % (100 * agree, hit, tot))

    # --- 4. 空间对应成立（远高于随机基线）---
    r_ns, r_sp, n_ns, n_sp = coverage(b)
    print('        ↳ deploy非空→sectA≠0 = %.1f%% (n=%d)' % (100 * r_ns, n_ns))
    print('        ↳ deploy空  →sectA==0 = %.1f%% (n=%d)' % (100 * r_sp, n_sp))
    chk('空间对应成立（非空→≠0 应 > 50%%，远高于基线）', r_ns > 0.50, True)
    chk('空→0 一致性应 > 70%%', r_sp > 0.70, True)
    # 🚫 纠偏：sectA_spec 声称 99.5%，实测远低
    chk('纠偏：99.5%% 声明不成立（实测 < 70%%）', r_ns < 0.70, True)

    # --- 5. 值 1 = 部队占据格（全为可打印 ASCII 部队字符）---
    byval = value_vs_deploy(b)
    v1 = byval.get(1, collections.Counter())
    printable = sum(n for dv, n in v1.items() if 0x20 <= dv < 0x7F)
    chk('值1 几乎全为可打印 deploy 字符',
        printable / sum(v1.values()) > 0.99 if v1 else False, True)
    # 值 0 以 0xFF（空）为主
    v0 = byval.get(0, collections.Counter())
    chk('值0 以 0xFF 空为主（>70%%）',
        v0.get(0xFF, 0) / sum(v0.values()) > 0.70 if v0 else False, True)

    # --- 6. 值域 0..7 ---
    vals = collections.Counter()
    for sectA, _t, _d in b:
        for r in range(ROWS):
            for c in range(COLS):
                vals[secta_value(sectA, r, c)] += 1
    chk('值域 ⊆ 0..7', max(vals), 7)
    chk('值域含下界 0', min(vals), 0)

    # --- 7. 🚫 全证伪：所有 terrain 派生方案均不成立 ---
    for name, rate in terrain_scheme_rates(b):
        chk('证伪 %s (匹配率 < 20%%)' % name, rate < 0.20, True)

    # --- 8. 8 类战斗地形类特征表（从 EXE 静态系数表读）---
    tabs = read_tables(root)
    if tabs:
        chk('攻城除数表 8B', tabs['atk_siege'], [10, 12, 15, 7, 7, 15, 100, 100])
        chk('野战除数表 12B', tabs['atk_field'],
            [10, 10, 12, 7, 7, 10, 10, 8, 100, 100, 12, 12])
        chk('移动表A 8B', tabs['mv_a'], [3, 4, 4, 5, 5, 4, 100, 100])
        chk('移动表C 8B', tabs['mv_c'], [1, 2, 3, 3, 3, 3, 100, 100])
        # 攻城：cls6/7 不可通行；野战：cls8/9 不可通行
        chk('攻城不可通行 = cls6/7',
            [i for i, v in enumerate(tabs['atk_siege']) if v == IMPASSABLE], [6, 7])
        chk('野战不可通行 = cls8/9',
            [i for i, v in enumerate(tabs['atk_field']) if v == IMPASSABLE], [8, 9])
        # 移动表 A/C（8B）中 cls6/7 是不可通行；但野战 12B 表 cls6/7 可通行
        chk('移动表A cls6/7 不可通行',
            [i for i, v in enumerate(tabs['mv_a']) if v == IMPASSABLE], [6, 7])
        chk('野战移动表B cls6/7 可通行（≠100）',
            all(tabs['mv_b0'][i] != IMPASSABLE for i in (6, 7)), True)
        # 特征：cls0 最易走、cls3/4 在 B 表消耗最高
        chk('cls0 移动消耗最低(表A)', min(range(8), key=lambda i: tabs['mv_a'][i]), 0)
        chk('cls3 在移动表B消耗最高',
            max(range(8), key=lambda i: tabs['mv_b0'][i]), 3)
        # 推断命名覆盖 0..7
        chk('推断命名覆盖 cls0..7', sorted(INFERRED_NAMES), list(range(8)))
    else:
        print('[SKIP] 未找到 EXE 映像，跳过系数表断言')

    print('-' * 78)
    print('self_test: %d/%d %s' % (ok, ok + fail, 'ALL PASS' if fail == 0 else 'HAS FAILURE'))
    return fail == 0


def terrain_scheme_rates(battles):
    """返回 [(方案名, 匹配率)] —— 用于证伪所有 terrain 派生假设"""
    import collections as _c

    def yx(row, col):
        return (2 * row + ((col & 1) ^ 1), 2 * col)
    schemes = {
        '单点code&7': lambda T, y, x: T[y * 40 + x] & 7,
        '单点code&0xF': lambda T, y, x: T[y * 40 + x] & 0xF,
        '2x2众数&7': lambda T, y, x: _c.Counter(
            [T[(y + dy) * 40 + (x + dx)] & 7 for dy in (0, 1) for dx in (0, 1)
             if y + dy < 19 and x + dx < 40]).most_common(1)[0][0],
        '2x2最小&7': lambda T, y, x: min(
            T[(y + dy) * 40 + (x + dx)] & 7 for dy in (0, 1) for dx in (0, 1)
            if y + dy < 19 and x + dx < 40),
        '2x2最大&7': lambda T, y, x: max(
            T[(y + dy) * 40 + (x + dx)] & 7 for dy in (0, 1) for dx in (0, 1)
            if y + dy < 19 and x + dx < 40),
    }
    hit = {k: 0 for k in schemes}
    tot = 0
    for sectA, terr, _dep in battles:
        for r in range(ROWS):
            for c in range(COLS):
                y, x = yx(r, c)
                sv = secta_value(sectA, r, c)
                tot += 1
                for k, f in schemes.items():
                    if f(terr, y, x) == sv:
                        hit[k] += 1
    return [(k, hit[k] / tot if tot else 0.0) for k in schemes]

    print('-' * 78)
    print('self_test: %d/%d %s' % (ok, ok + fail, 'ALL PASS' if fail == 0 else 'HAS FAILURE'))
    return fail == 0


if __name__ == '__main__':
    import sys
    self_test(sys.argv[1] if len(sys.argv) > 1 else '.')
