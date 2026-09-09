# -*- coding: utf-8 -*-
"""
finalize_portraits.py — 把 ImageGen 原始图缩放落地为正式立绘
=========================================================
流程：_portrait_raw/{id}/*.png  →  512×640 RGBA  →  assets/sprites/portraits/

命名规则（2026-09-09 用户需求）
------------------------------
  单张：  {id}_{姓名}.png          例：13_织田信长.png
  多张：  {id}_{姓名}-1.png / -2.png …   例：13_织田信长-1.png、13_织田信长-2.png
         （同一武将有多张候选时按生成顺序编号；加载器默认取 -1）

⚠️ 加载器侧已同步支持：src/render/asset_loader.gd 的 load_portrait(id, name)
   依次尝试 {id}_{name}.png → {id}_{name}-1.png → {id}.png → 占位图。
   所以旧式纯 id 命名（{id}.png）仍然可用，不会因改名而读不到图。

为什么要缩放
------------
src/render/AssetSpec.gd: PORTRAIT_SIZE = 512×640（4:5）。
ImageGen 出图是 1024×1280（2x）；若直接入库，695 张会把仓库撑到约 1GB。

依赖：Pillow（本机系统 Python 3.12 有；托管 3.13 无）。

用法
----
    "C:/Users/Administrator/AppData/Local/Programs/Python/Python312/python.exe" \
        tools/finalize_portraits.py                # 处理 _portrait_raw/ 下全部
    ... tools/finalize_portraits.py --only 13 257  # 只处理指定 id
"""
import argparse
import json
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow：请用系统 Python 3.12（有 Pillow 12.3.0）运行本脚本")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "_portrait_raw")
OUT = os.path.join(ROOT, "assets", "sprites", "portraits")
FINAL = (512, 640)   # AssetSpec.PORTRAIT_SIZE


def load_names():
    """id -> 姓名（surname+given），用于文件名。"""
    officers = json.load(open(os.path.join(ROOT, "data", "officers.json"), encoding="utf-8"))
    return {int(o["id"]): o.get("surname", "") + o.get("given", "") for o in officers}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", type=int, help="只处理指定 id")
    args = ap.parse_args()

    if not os.path.isdir(RAW):
        sys.exit(f"找不到 {RAW}（尚无待处理原图）")
    os.makedirs(OUT, exist_ok=True)
    names = load_names()

    ids = args.only if args.only else sorted(
        int(d) for d in os.listdir(RAW) if d.isdigit() and os.path.isdir(os.path.join(RAW, d))
    )

    ok = fail = 0
    for oid in ids:
        src_dir = os.path.join(RAW, str(oid))
        if not os.path.isdir(src_dir):
            print(f"  [跳过] 无原图目录 {oid}")
            fail += 1
            continue
        pngs = [f for f in os.listdir(src_dir) if f.lower().endswith(".png")]
        if not pngs:
            print(f"  [跳过] {oid} 目录内无 png")
            fail += 1
            continue
        # 按修改时间排序：最早生成的排前面（保证 -1/-2 顺序稳定）
        pngs.sort(key=lambda f: os.path.getmtime(os.path.join(src_dir, f)))

        name = names.get(oid, "")
        multi = len(pngs) > 1
        for i, f in enumerate(pngs, start=1):
            suffix = f"-{i}" if multi else ""
            dst = os.path.join(OUT, f"{oid}_{name}{suffix}.png")
            try:
                im = Image.open(os.path.join(src_dir, f))
                if im.mode != "RGBA":
                    im = im.convert("RGBA")
                if im.size != FINAL:
                    im = im.resize(FINAL, Image.LANCZOS)
                im.save(dst, "PNG", optimize=True)
                kb = os.path.getsize(dst) // 1024
                print(f"  [ok] {os.path.basename(dst)}  {im.size[0]}x{im.size[1]}  {kb} KB")
                ok += 1
            except Exception as e:
                print(f"  [失败] {oid} {f}: {e}")
                fail += 1

    print(f"\n完成：成功 {ok} / 失败 {fail}  输出目录 {OUT}")
    if ok:
        print("下一步：重跑 tools/gen_portrait_prompts.py 刷新台账（已存在的会自动标记 done）")


if __name__ == "__main__":
    main()
