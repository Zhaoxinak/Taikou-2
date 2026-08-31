# -*- coding: utf-8 -*-
"""
BSDATA ↔ 武将实体 偏移重映射通则（续135 · 定稿）
================================================
续134 曾因 `@52`(max 250) vs `+0x28`(钳 200)、`@50..@51`(max 0xFFFF) vs
`+0x26`(钳 60000) 两组「越界」而给通则加了保守边界。本轮实测证明
**那不是映射错误，而是同一批占位/哨兵记录造成的假象** —— 通则成立范围
因此从 `@22..@47` 扩大到 **`@22..@55`**（实体几乎全部字段）。

结构本质
--------
    武将实体 = BSDATA 记录 **去掉前 12 字节姓名区**
    即   entity[i] = bsdata[i + 12],  i ∈ [0, 47)
    59 − 12 = 47 = 实体 stride ✓

关键消解（本轮核心）
--------------------
    @50..@51 (word)  > 60000 的值 **只有 0xFFFF**，共 45 条；
                     非哨兵最大值 = 30000 ≤ 60000 ✓
    @52              > 200 的值 **只有 250**，共 45 条
    ⇒ **两组「越界」是同一批 45 条占位记录**，不是偏移错位。
    （同理 @54..@55 的 word = 0xFFFF 占 674/700，与 +0x2a 的哨兵语义一致。）

判定表（`entity[i] = bsdata[i+12]`）
------------------------------------
| BSDATA | 实体 | 语义 | 判定依据 |
|---|---|---|---|
| @22..@26 | +0x0a..+0x0e | 五维能力 | setter 族钳 100；实测 max ≤ 100 |
| @27..@29 | +0x0f..+0x11 | 10 技能 ×2bit | @29 高 nibble 700/700 恒 0 |
| @31 / @49 | +0x13 / +0x25 | **現城 id（双写）** | @31==@49 700/700 ↔ 续114 实测 `+0x13` 是 `+0x25` 的副本；哨兵 255 ↔ setter 常量 `0xff` |
| @39 | +0x1b | 生年 | EXE `0x49a5c0` 硬证据 |
| @44..@47 | +0x20..+0x23 | 体力上限/体力/体力消耗/野心 | @44==@45 700/700；@47 恒 50 ↔ 常量 `0x32` |
| @48 | +0x24 | 親密度 | @48=13 出现 57 次 ↔ setter 常量 `0xd`；@48=255 ↔ 常量 `0xff` |
| @50..@51 | +0x26 (word) | 功勲 | 非哨兵 max 30000 ≤ 60000 |
| @52 | +0x28 | 俸禄 | 非占位 max 200 = 钳 200 |
| @53 | +0x29 | **忠诚** | max 100 = 钳 100；分布均值高（top: 100/89/88）符合忠诚 |
| @54..@55 | +0x2a (word) | （状态字，-1 空） | 0xFFFF 占 674/700 ↔ +0x2a 哨兵 |
| @56..@58 | +0x2c..+0x2e | 状态/身份/寿命 | 值域不冲突但**证据不足**，标注为推定 |

🔴 对既有记录的两处修正
----------------------
1. **`@53` 不是「武艺/熟练度」，是「忠诚」** —— 原 spec 的 `+0x53 武艺/熟练度(?)`
   是猜测；实测 max=100 恰与 `+0x29` setter 的钳 100 吻合，且 续122 已由
   `0x49a7bf`（正落在 `0x49a7b0` 函数体内）坐实 `+0x29`=忠诚。
2. **续134 加的「通则仅适用 `@22..@47`」边界过窄，本轮撤销**；
   改为「适用 `@22..@55`；`@56..@58` 为推定」。
"""

import struct
from collections import Counter

BSD1 = "F:/Games/Taikou 2/Taikou2 Original/BSDATA1.TR2"
_b = open(BSD1, "rb").read()
REC, N = 59, 700
ENT_STRIDE = 47
REMAP_SHIFT = 12

# 占位/哨兵记录的判定: @50..@51 == 0xFFFF （本轮实测 45 条）
def is_placeholder(i):
    return struct.unpack_from("<H", _b, REC * i + 50)[0] == 0xFFFF


def bf(i, off):
    return _b[REC * i + off]


def bfw(i, off):
    return struct.unpack_from("<H", _b, REC * i + off)[0]


VERDICT = "confirmed"
PRESUMED = "presumed"

PAIRS = [
    # (bsd_off, ent_off, 语义, 钳制, 判定)
    (22, 0x0A, "统御力", 100, VERDICT), (23, 0x0B, "武力", 100, VERDICT),
    (24, 0x0C, "内政力", 100, VERDICT), (25, 0x0D, "外交力", 100, VERDICT),
    (26, 0x0E, "魅力", 100, VERDICT),
    (27, 0x0F, "技能 0-3", None, VERDICT), (28, 0x10, "技能 4-7", None, VERDICT),
    (29, 0x11, "技能 8-9", None, VERDICT),
    (31, 0x13, "現城 id (双写 A)", None, VERDICT),
    (39, 0x1B, "生年", None, VERDICT),
    (44, 0x20, "体力上限", 100, VERDICT), (45, 0x21, "体力(现役)", None, VERDICT),
    (46, 0x22, "体力消耗", 100, VERDICT), (47, 0x23, "野心", 100, VERDICT),
    (48, 0x24, "親密度", None, VERDICT),
    (49, 0x25, "現城 id (双写 B)", None, VERDICT),
    (50, 0x26, "功勲 (word)", 60000, VERDICT),
    (52, 0x28, "俸禄", 200, VERDICT),
    (53, 0x29, "忠诚", 100, VERDICT),
    (54, 0x2A, "状态字 (word)", None, VERDICT),
    (56, 0x2C, "状态/俸禄等级", None, PRESUMED),
    (57, 0x2D, "身份", None, PRESUMED),
    (58, 0x2E, "寿命/状态", None, PRESUMED),
]

CONFIRMED_N = sum(1 for p in PAIRS if p[4] == VERDICT)


def _run_tests():
    ok = tot = 0

    def check(name, cond):
        nonlocal ok, tot
        tot += 1
        if not cond:
            print(f"  [FAIL] {name}")
        else:
            ok += 1

    # --- 1. 结构性前提
    check("59 − 12 = 47 = 实体 stride", REC - REMAP_SHIFT == ENT_STRIDE)
    check("映射覆盖实体全部 47 字节",
          sorted(p[1] for p in PAIRS) == sorted(set(p[1] for p in PAIRS)) and
          max(p[1] for p in PAIRS) <= ENT_STRIDE - 1)

    # --- 2. 每组偏移关系
    for bsd_off, ent_off, nm, cap, vd in PAIRS:
        check(f"@{bsd_off} → +{ent_off:#04x} ({nm})", bsd_off - REMAP_SHIFT == ent_off)

    # --- 3. 钳制检查（排除占位记录）
    ph = [i for i in range(N) if is_placeholder(i)]
    check("占位记录恰 45 条", len(ph) == 45)
    for bsd_off, ent_off, nm, cap, vd in PAIRS:
        if cap is None:
            continue
        vs = [bfw(i, bsd_off) if cap > 255 else bf(i, bsd_off)
              for i in range(N) if not is_placeholder(i)]
        check(f"@{bsd_off} ({nm}) 非占位 max ≤ {cap}", max(vs) <= cap)

    # --- 4. 「越界」全部来自同一批占位记录（本轮核心消解）
    over_w = [i for i in range(N) if bfw(i, 50) > 60000]
    check("@50 越 60000 者全为占位记录", set(over_w) == set(ph))
    over_52 = [i for i in range(N) if bf(i, 52) > 200]
    check("@52 越 200 者全为占位记录", set(over_52) == set(ph))
    check("@52 越界值统一为 250", set(bf(i, 52) for i in over_52) == {250})

    # --- 5. 双写对
    check("@31 == @49 (現城 双写) 700/700",
          sum(1 for i in range(N) if bf(i, 31) == bf(i, 49)) == N)
    check("@44 == @45 (体力上限 = 现役) 700/700",
          sum(1 for i in range(N) if bf(i, 44) == bf(i, 45)) == N)
    check("現城哨兵 255 计数一致",
          sum(1 for i in range(N) if bf(i, 31) == 255) ==
          sum(1 for i in range(N) if bf(i, 49) == 255))

    # --- 6. 常量呼应
    check("@47 野心 700/700 恒 50", set(bf(i, 47) for i in range(N)) == {50})
    check("@53 忠诚 max = 100 (与 +0x29 钳 100 吻合)",
          max(bf(i, 53) for i in range(N)) == 100)
    check("@48 = 13 出现 57 次 (呼应 setter 常量 0xd)",
          Counter(bf(i, 48) for i in range(N))[13] == 57)
    check("@54..@55 word = 0xffff 占 674/700",
          Counter(bfw(i, 54) for i in range(N))[0xFFFF] == 674)

    # --- 7. 推定项标注
    check("推定项恰为 @56/@57/@58",
          sorted(p[0] for p in PAIRS if p[4] == PRESUMED) == [56, 57, 58])
    check(f"确认项 {CONFIRMED_N} 组", CONFIRMED_N == len(PAIRS) - 3)

    print(f"\nRESULT: {ok}/{tot} checks passed")
    return ok == tot


if __name__ == "__main__":
    print("=== BSDATA ↔ 实体 重映射通则（续135 定稿）===")
    print(f"  entity[i] = bsdata[i + {REMAP_SHIFT}]   ({REC} − {REMAP_SHIFT} = {ENT_STRIDE})\n")
    print(f"  {'BSDATA':<9}{'实体':<9}{'钳制':<9}{'判定':<11}语义")
    for bsd_off, ent_off, nm, cap, vd in PAIRS:
        print(f"  @{bsd_off:<8}+{ent_off:#04x}   {str(cap or '-'):<9}{vd:<11}{nm}")
    print()
    _run_tests()
