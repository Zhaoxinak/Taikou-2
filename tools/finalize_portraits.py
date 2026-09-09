# -*- coding: utf-8 -*-
"""
finalize_portraits.py — 把 ImageGen 原始图缩放落地为正式立绘
=========================================================
流程：_portrait_raw/{id}/*.png  →  512×640 RGBA  →  assets/sprites/portraits/{id}.png

为什么要缩放
------------
src/render/AssetSpec.gd: PORTRAIT_SIZE = 512×640（4:5）。
ImageGen 出图是 1024×1280（2x）；若直接入库，695 张会把仓库撑到约 1GB。
缩到 512×640 后单张约 200–400KB，且 **真图按同名替换即可，无需改代码**。

⚠️ 文件名是 {id}.png（asset_loader.gd 按 "res://assets/sprites/portraits/%d.png" 加载），
   不是 portrait_prompts.json 里写的 full_XXXX.png（该写法已过时）。

依赖：Pillow（本机系统 Python 3.12 有；托管 3.13 无）。

用法
----
    "C:/Users/Administrator/AppData/Local/Programs/Python/Python312/python.exe" \
        tools/finalize_portraits.py                # 处理 _portrait_raw/ 下全部
    ... tools/finalize_portraits.py --only 13 257  # 只处理指定 id
"""
import argparse
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", type=int, help="只处理指定 id")
    args = ap.parse_args()

    if not os.path.isdir(RAW):
        sys.exit(f"找不到 {RAW}（尚无待处理原图）")
    os.makedirs(OUT, exist_ok=True)

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
        # 取最新一张（同一 id 重复生成时以最新为准）
        src = max(os.path.join(src_dir, f) for f in pngs)
        dst = os.path.join(OUT, f"{oid}.png")
        try:
            im = Image.open(src)
            if im.mode != "RGBA":
                im = im.convert("RGBA")
            if im.size != FINAL:
                im = im.resize(FINAL, Image.LANCZOS)
            im.save(dst, "PNG", optimize=True)
            size_kb = os.path.getsize(dst) // 1024
            print(f"  [ok] {oid:>3}.png  {im.size[0]}x{im.size[1]}  {size_kb} KB")
            ok += 1
        except Exception as e:
            print(f"  [失败] {oid}: {e}")
            fail += 1

    print(f"\n完成：成功 {ok} / 失败 {fail}  输出目录 {OUT}")
    if ok:
        print("下一步：重跑 tools/gen_portrait_prompts.py 刷新台账（已存在的会自动标记 done）")


if __name__ == "__main__":
    main()
