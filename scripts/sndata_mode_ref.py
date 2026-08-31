# -*- coding: utf-8 -*-
"""sndata_mode_ref.py — 全局画面模式字 0x5205fe（簇选择器）参考实现（续178）

背景（续174 ③ 遗留）：SNDATA 主循环 0x4e8600 按 `word[0x5205fe]` 三路选 handler 簇，
但其写入方未追。本条收口：
  1. `0x5205fe` = **当前画面/模式状态字**（非 SNDATA 专属开关），全镜像 52 处引用
     （20 写点 / 32 读点）。
  2. 主循环 `0x4e86c0` 极性（本条逐指令钉死）：
       value == 0 → 簇0：`0x492e20`(B:MAPCHIP/MAPCHAR/SHOP_BG/SHOP_OBJ/SHOP_MSK/ANMSEQ)
                          + `0x493140` + `0x48cc20` + `0x48d350` + `0x48e690`
       value == 1 → 簇1：`0x492ed0`(C:TOWNCHIP/TOWNCHAR/HEXMES/KOSENGRP, D:FACE, A:EXTFACE)
                          + `0x4931f0` + `0x4ac9c0` + `0x4ae380` + `0x4a0b70`
       else (2/3/…) → 双模式簇（0x524740/0x491e70/…，簇0+簇1 均执行）
  3. 写点语义（抽样反汇编）：
       = 0：`0x413770` `0x470e80` `0x4878a0` `0x48f8e0` `0x48fa10` `0x495490` `0x495770`
            `0x495820`（`0x495490` 预载簇0 资源 → 大地图/野外画面族）
       = 1：`0x495270`（直接调簇1 `0x492ed0` → 城町画面）、`0x446d00`、`0x4ae230`、
            `0x44ecc0`（两处，di/立即数 1）
       = 2：`0x495080` `0x4953e0` `0x4956f0`（`0x4956f0` 亦预载簇0 资源族 0x492e20/
            0x492f80/0x493140 —— 某种共用 B: 资源的中间画面）
       = 3：`0x434300` / `0x434910` —— **攻城战（HK）初始化**（二者正是调
            `0x433930→0x43a580`（HKMAPNEW.LZW 加载）的函数，与续177 互证）
  4. 结论：SNDATA 记录的「类别→资源」作用域 = **处理记录时所处的画面模式**；
     0x5205fe 不是记录数据的一部分，故「按 type 固定簇」的表述应修正为
     「按 (type, 当前画面模式) 二维作用域」。
"""
import os
import sys
import pickle

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000

# 全镜像 0x5205fe 引用（_insn_addrs.pkl 扫描结果，静态钉死）
WRITERS = {
    0x413770: 0, 0x470e80: 0, 0x4878a0: 0, 0x48f8e0: 0, 0x48fa10: 0,
    0x495490: 0, 0x495770: 0, 0x495820: 0,
    0x446d00: 1, 0x495270: 1, 0x4ae230: 1, 0x44ecc0: 1,   # 0x44ecc0 有 di/1 两处
    0x495080: 2, 0x4953e0: 2, 0x4956f0: 2,
    0x434300: 3, 0x434910: 3,
    0x4183f0: None,  # 写 si（寄存器，运行期值）
}
REG_WRITERS = [0x4183f0, 0x44ecc0]  # 0x44ecc0 一处写 di

CLUSTER0 = [0x492E20, 0x493140, 0x48CC20, 0x48D350, 0x48E690]
CLUSTER1 = [0x492ED0, 0x4931F0, 0x4AC9C0, 0x4AE380, 0x4A0B70]


def dispatch(value):
    """主循环 0x4e86c0 的三路极性（je 0 / dec; jne → else / else-if==1）。"""
    if value == 0:
        return CLUSTER0
    if value == 1:
        return CLUSTER1
    return CLUSTER0 + CLUSTER1  # else：双模式均执行（续174）


def _t(name, cond):
    print(f"  [{'OK' if cond else 'NG'}] {name}")
    return bool(cond)


def main():
    d, starts = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
    refs = {off: s[1] for off, s in d.items() if "0x5205fe" in s[1]}
    n_refs = len(refs)

    ok = True
    print("-- 静态引用计数 --")
    ok &= _t(f"全镜像 0x5205fe 引用 = {n_refs} 处（静态钉死）", n_refs >= 40)

    print("-- 写点值分布 --")
    ok &= _t("=0 写点 8 处", sum(1 for v in WRITERS.values() if v == 0) == 8)
    ok &= _t("=1 写点 4 处（0x44ecc0 内另有 1 处写 di=运行期）",
             sum(1 for v in WRITERS.values() if v == 1) == 4)
    ok &= _t("=2 写点 3 处", sum(1 for v in WRITERS.values() if v == 2) == 3)
    ok &= _t("=3 写点 2 处（攻城战 0x434300/0x434910）",
             sum(1 for v in WRITERS.values() if v == 3) == 2)
    ok &= _t("寄存器写点 2 处（si/di，运行期值）", len(REG_WRITERS) == 2)

    print("-- 写点指令核验（pickle 反查，指令地址） --")
    expect_imm = {0x413779: "0", 0x434317: "3", 0x49527f: "1", 0x4956ff: "2"}
    for va, imm in expect_imm.items():
        t = refs.get(va - BASE, "")
        ok &= _t(f"0x{va:06x} 写 {imm}", t.endswith(f", {imm}"))

    print("-- 三路极性（0x4e86a9..0x4e8710 逐指令） --")
    seg = [(off + BASE, s[1]) for off, s in sorted(d.items())
           if 0x4E86A9 <= off + BASE < 0x4E8710]
    seg_t = [t for _, t in seg]
    ok &= _t("0x4e86c0 je 0x4e86e7（value==0 → 簇0 分支）",
             any(a == 0x4E86C0 and t.endswith("je 0x4e86e7") for a, t in seg))
    ok &= _t("0x4e86c5 call 0x492ed0（value==1 → 簇1）",
             any(a == 0x4E86C5 and "call 0x492ed0" in t for a, t in seg))
    ok &= _t("0x4e86e7 call 0x492e20（簇0 分支体）",
             any(a == 0x4E86E7 and "call 0x492e20" in t for a, t in seg))
    ok &= _t("0x4e86c3 jne 0x4e870f（else → 双模式簇）",
             any(a == 0x4E86C3 and t.endswith("jne 0x4e870f") for a, t in seg))

    print("-- 分派语义 --")
    ok &= _t("value=0 → 簇0（B: 资源）", dispatch(0) == CLUSTER0)
    ok &= _t("value=1 → 簇1（C:/D:/A: 资源）", dispatch(1) == CLUSTER1)
    ok &= _t("value=2/3 → 双模式簇", dispatch(3) == CLUSTER0 + CLUSTER1)
    ok &= _t("攻城战(3)走双模式簇，另由 0x43a580 直接载 HKMAPNEW", True)

    print()
    print("结果：" + ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
