#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bootstrap.py — 全新克隆/换机器后的一键数据重建
=============================================
⚠️ 为什么要这个脚本
------------------------------------------------------------------
`.gitignore` 第 58 行忽略了整个 `/data/`，所以 `data/*.json` **不在版本库里**。
这些文件全部是**导出产物**，由原版二进制（`Taikou2 Original/`，已入版本库）
离线解析生成 —— 只要原版目录在，就能 100% 重建，且结果字节一致。

新机器 / 换 AI 接手时，clone 完直接跑本脚本即可，不要手工拷 data/。

用法
----
    python scripts/bootstrap.py

依赖：仅 Python 标准库（与 export_for_godot.py 一致）。

生成内容
--------
    data/officers.json   700 武将（695 真实 + 5 占位）
    data/castles.json    200 城
    data/provinces.json   49 国
    data/names.json      370 名称
    data/skills.json      10 技能名
    data/gaiji.json        外字替换表
    data/consts.json       全局常量
    data/text.json      6211 条 MSGX 文本（UTF-8）
    data/battles.json     38 张战图
    data/shops.json       30 条店铺人格记录（本项由 export_shops_json.py 生成）

退出码 0 = 全部就绪；非 0 = 有缺失，按提示排查。
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
ORIGINAL = os.path.join(ROOT, "Taikou2 Original")

# 期望校验：文件名 -> (取哪个键计数, 最小条数)
#   键为 None 表示直接对顶层计数（顶层是 list，或像 text.json 那样以 id 为键的 dict）
#   ⚠️ 注意各文件结构不统一：castles/provinces/names/skills 是「包装字典」，
#      真实数据在 .castles / .provinces / .province_names / .names 里，
#      直接 len(dict) 只会数到顶层键数（曾误报为 2/7/4）。
EXPECT = {
    "officers.json":  (None, 695),              # 695 真实 + 5 占位 = 700
    "castles.json":   ("castles", 200),
    "provinces.json": ("provinces", 49),
    "names.json":     ("province_names", 49),   # 另有 castle_town_names 204 等
    "skills.json":    ("names", 10),
    "text.json":      (None, 6211),             # 顶层是 {"0":..,"1":..} 共 6211 键
    "battles.json":   (None, 38),
    "shops.json":     (None, 30),
    # 以下只校验存在（条数不固定或为纯配置字典）
    "gaiji.json":     (None, 0),
    "consts.json":    (None, 0),
}


def run(script: str) -> bool:
    path = os.path.join(ROOT, "scripts", script)
    if not os.path.exists(path):
        print(f"  [缺失] scripts/{script}")
        return False
    print(f"  → 运行 scripts/{script} …")
    r = subprocess.run([sys.executable, path], cwd=ROOT)
    if r.returncode != 0:
        print(f"  [失败] {script} 退出码 {r.returncode}")
        return False
    return True


def main() -> int:
    print("=" * 60)
    print("太阁立志传2 · 数据重建 bootstrap")
    print("=" * 60)

    if not os.path.isdir(ORIGINAL):
        print(f"[错误] 找不到原版目录：{ORIGINAL}")
        print("      该目录已入版本库；若缺失请检查 clone 是否完整。")
        return 1
    print(f"[ok] 原版目录存在（{len(os.listdir(ORIGINAL))} 个文件）")

    os.makedirs(DATA, exist_ok=True)

    print("\n[1/2] 导出原版数据 → data/")
    if not run("export_for_godot.py"):
        return 1

    print("\n[2/2] 导出店铺人格记录 → data/shops.json")
    if not run("export_shops_json.py"):
        return 1

    print("\n[校验] 逐项检查 data/：")
    bad = []
    for name, (key, minimum) in EXPECT.items():
        p = os.path.join(DATA, name)
        if not os.path.exists(p):
            print(f"  [缺失] {name}")
            bad.append(name)
            continue
        if minimum <= 0:
            print(f"  [ok]   {name:<16} 存在")
            continue
        try:
            obj = json.load(open(p, encoding="utf-8"))
            target = obj if key is None else obj.get(key)
            n = len(target) if isinstance(target, (list, dict)) else 0
        except Exception as e:
            print(f"  [损坏] {name}: {e}")
            bad.append(name)
            continue
        ok = n >= minimum
        where = "顶层" if key is None else f".{key}"
        print(f"  {'[ok]  ' if ok else '[不足]'} {name:<16} {where} {n} 条（期望 ≥{minimum}）")
        if not ok:
            bad.append(name)

    print("")
    if bad:
        print(f"[失败] 以下文件异常：{', '.join(bad)}")
        return 1

    print("[成功] data/ 全部就绪，Godot 可直接运行。")
    print("")
    print("下一步：")
    print("  1) 安装 Godot 4.7.1（可执行程序本身未入版本库，需自行下载）")
    print("  2) 用 Godot 打开工程根目录下的 project.godot")
    print("  3) 无头回归自检：")
    print("     Godot_v4.7.1-stable_win64_console.exe --headless "
          "--script res://tools/_test_diplomacy.gd")
    print("")
    print("┌──────────────────────────────────────────────────────────┐")
    print("│ ⚠️  scripts/_unpacked_mem.bin（2MB 脱壳映像）也被 gitignore │")
    print("│    且**没有生成器**。所有 scripts/*_ref.py 反向脚本依赖它，  │")
    print("│    换机器后需从本机手工拷贝，否则反向脚本无法运行。        │")
    print("└──────────────────────────────────────────────────────────┘")
    return 0


if __name__ == "__main__":
    sys.exit(main())
