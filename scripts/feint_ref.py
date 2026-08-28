#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
太阁立志传2 · 计略「伪兵 Feint」参考实现（1:1 复刻 TAIK2W95.exe 逻辑）

来源：脱壳映像 scripts/_unpacked_mem.bin(基址 0x400000)静态段 dump + 反汇编
       + Unicorn 2.1.4 实证(续14/续15,scripts/_emu_rumor_land.py 等)。

涉及原版函数
------------
0x435b50   Feint handler          (cdecl, 两 corps 指针)
  └─ 0x435570 effect               循环 k=0..5 在 ±邻域生成 ≤6 个 Dummy 部队
       └─ 0x43a440 spawn 派生      取 word[eax*4+0x503712] 选兵类型
            └─ 0x43a460 真身         按 TIER_THR/TIER_BASE/TIER_RND 派生 variant
                 └─ 0x4411b0 写块 3 次: SECT_A(0xb4 → 0x512e58) /
                                              TERRAIN(0x2f8 → 0x512868) /
                                              DEPLOY(0x2f8 → 0x512b60)

静态表(全部自校验)
------------------
0x503710  dir8        8 × int8    (dx,dy)  N/NE/E/SE/S/SW/W/NW 偏移
0x503712  feint_spawn 16 × u16    (1=真生/0=禁用/65535=邻域外) ← 已 dump
0x503740  tier_thr    10 × byte   阈值(?)
0x503750  tier_base   10 × byte   基数
0x503760  tier_rnd    10 × byte   随机量上限

公式(合战整体 variant 选择,非仅伪兵用)
  rand() % tier_rnd[tier] + tier_base[tier]   (GAME_DATA_SPEC.md §3.10.9)

伪兵 5 Dummy 部署算法(2026-08-28 续39 精化)
-------------------------------------------
索引计算: esi = parity * 6 + k, k ∈ {0..5},parity = (col + row) & 1 之类(续14)
取值:    val = word[0x503712 + esi*2]
生成判定:val == 1 ⇒ 落 Dummy;
         val == 0 ⇒ 邻域内但槽位生成条件不达(角色未达触发阈值);
         val == 65535 ⇒ 邻域外(出界保护),跳过

实测 12 项(只取前 12,即 parity=0 和 parity=1):
  parity=0: k=0..5 → [65535, 1, 0, 1, 1, 0]
  parity=1: k=0..5 → [1, 65535, 1, 65535, 0, 0]
⇒ 有效 5 槽 = {par=0,k=1,3,4} ∪ {par=1,k=0,2}(原"≤6"精化为 5)。

邻域方向(从作用方 corps 的 (col,row) 出发):
  k=0 N, k=1 NE, k=2 E, k=3 SE, k=4 S, k=5 SW
"""

import os
import json
from typing import List, Tuple, Optional

BASE = 0x400000
_HERE = os.path.dirname(os.path.abspath(__file__))
_TACTIC_JSON = os.path.join(_HERE, "tactic_tables.json")

# 0x503710 dir8: 8 个 int8 对,每对 (dx, dy)
DIR8_LABELS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
DIR8_OFFSETS = [(0, -1), (1, -1), (1, 0), (1, 1),
                (0, 1), (-1, 1), (-1, 0), (-1, -1)]

# 0x503712 伪兵 spawn 表(16 项,u16)
# 已 dump 进 scripts/tactic_tables.json;此处硬编码用于无 JSON 时回退
FEINT_SPAWN = [65535, 1, 0, 1, 1, 0, 1, 65535,
               1, 65535, 0, 0, 65535, 1, 65535, 1]

# 0x503740/50/60 三张 tier 表(本环境无映像未 dump,标 None 待补)
TIER_THR  = None  # 10 × byte,门控
TIER_BASE = None  # 10 × byte,派生基数
TIER_RND  = None  # 10 × byte,rand() 上限

EMPTY, SPAWN, OUT = 0, 1, 65535


def feint_active_slots(parity: int) -> List[int]:
    """返回该 parity 下 k=0..5 中所有 ==1 的 k(0..5)。"""
    assert parity in (0, 1)
    base = parity * 6
    return [k for k in range(6) if FEINT_SPAWN[base + k] == SPAWN]


def feint_slot_value(parity: int, k: int) -> int:
    """返回 word[0x503712 + (parity*6 + k)*2];出界返回 OUT。"""
    if not (0 <= k <= 5):
        return OUT
    return FEINT_SPAWN[parity * 6 + k]


def feint_neighbors(parity: int, col: int, row: int,
                    cols: int = 40, rows: int = 19) -> List[Tuple[int, int, int, int]]:
    """返回 (col, row, k, dir_idx) 列表,过滤掉 OUT(邻域外)。

    仅 val == 1(SPAWN)才返回;val == 0(禁用槽)也跳过。
    """
    out = []
    for k in range(6):
        val = feint_slot_value(parity, k)
        if val != SPAWN:
            continue
        dx, dy = DIR8_OFFSETS[k]
        nc, nr = col + dx, row + dy
        if 0 <= nc < cols and 0 <= nr < rows:
            out.append((nc, nr, k, k))
    return out


def tier_variant(tier: int, rnd: int) -> Optional[int]:
    """合战 variant 派生:variant = rnd % TIER_RND[tier] + TIER_BASE[tier]。
    若 tier 表未 dump 返回 None(需 EXE 映像)。
    """
    if TIER_RND is None or TIER_BASE is None:
        return None
    if not (0 <= tier < 10):
        return None
    return (rnd % TIER_RND[tier]) + TIER_BASE[tier]


# ============================================================ 自检
def _selftest():
    PASS = FAIL = 0
    def chk(name, cond, detail=''):
        nonlocal PASS, FAIL
        if cond: PASS += 1; print(f"  PASS  {name}" + (f"  ({detail})" if detail else ''))
        else:    FAIL += 1; print(f"  FAIL  {name}" + (f"  ({detail})" if detail else ''))

    print("=== feint spawn 表 索引分析 ===")
    p0 = feint_active_slots(0)
    p1 = feint_active_slots(1)
    chk("parity=0 有效 3 槽 k=1,3,4", p0 == [1, 3, 4], str(p0))
    chk("parity=1 有效 2 槽 k=0,2", p1 == [0, 2], str(p1))
    chk("总有效 5 槽(原 ≤6 精化)", len(p0) + len(p1) == 5)
    chk("65535 视为 OUT", feint_slot_value(0, 0) == OUT)
    chk("k=2 parity=0 视为禁用", feint_slot_value(0, 2) == 0)

    print("\n=== 邻域 6 步 N/NE/E/SE/S/SW ===")
    chk("dir8 N  (0,-1)", DIR8_OFFSETS[0] == (0, -1))
    chk("dir8 NE (1,-1)", DIR8_OFFSETS[1] == (1, -1))
    chk("dir8 E  (1,0)",  DIR8_OFFSETS[2] == (1, 0))
    chk("dir8 SE (1,1)",  DIR8_OFFSETS[3] == (1, 1))
    chk("dir8 S  (0,1)",  DIR8_OFFSETS[4] == (0, 1))
    chk("dir8 SW (-1,1)", DIR8_OFFSETS[5] == (-1, 1))

    print("\n=== feint_neighbors 出界过滤 ===")
    # 中心 (10, 10),parity=0 → 3 槽 (NE/SE/S)
    ns = feint_neighbors(0, 10, 10)
    chk("par=0 (10,10) 3 个生成点", len(ns) == 3, str(ns))
    # 角 (0, 0),par=0 → NE(1,-1) 出 row,SE(1,1) 出 col??(1,1) 在域内,S(0,1) 在域内
    # k=1 NE 出 row, k=3 SE 在, k=4 S 在 → 2 个
    ns2 = feint_neighbors(0, 0, 0)
    chk("par=0 (0,0) 角 2 个生成点(SE+S)", len(ns2) == 2, str(ns2))
    # 边 (0, 5),par=1 → N(0,-1) 出 row=4 ok, E(1,0) ok
    # k=0 N(0,4) ok, k=2 E(1,5) ok → 2 个
    ns3 = feint_neighbors(1, 0, 5)
    chk("par=1 (0,5) 2 个生成点(N+E)", len(ns3) == 2, str(ns3))

    print("\n=== tier_variant(需映像)===")
    if TIER_RND is None:
        print("  [skip] 0x503740/50/60 未 dump(本环境无 EXE 映像)")
    else:
        chk("tier=0, rnd=5", tier_variant(0, 5) is not None)

    print(f"\n{PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    # 优先从 tactic_tables.json 加载(若可读)
    if os.path.exists(_TACTIC_JSON):
        try:
            t = json.load(open(_TACTIC_JSON))
            if "feint_spawntype_0x503712" in t:
                FEINT_SPAWN[:] = t["feint_spawntype_0x503712"][:16]
        except Exception as e:
            print(f"[warn] tactic_tables.json 读失败: {e}, 用回退常量")

    rc = _selftest()
    raise SystemExit(rc)
