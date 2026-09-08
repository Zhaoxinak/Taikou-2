# -*- coding: utf-8 -*-
"""生成音效资产 + GDScript 常量表（阶段 6：音效 39 个接入）

输入：
  scripts/sfx_subsystem.json   —— 逆向权威：id / 原文件名 / 中文语义 / 类别
  scripts/_decoded_kos/*.wav   —— KOS 解码产物（1 字节 XOR 0xAE + WAV）
输出：
  assets/audio/sfx/<NAME>.wav  —— 供运行时载入
  src/audio/Sfx.gd             —— id → 名称/语义/类别/路径 常量表

⚠️ 载入方式用 `AudioStreamWAV.load_from_file(绝对路径)`，不用 `ResourceLoader.load(res://)`：
   后者依赖 .import 导入缓存，未导入过的工程会静默失败（与 CJK 字体同一个坑）。
"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_JSON = os.path.join(ROOT, "scripts", "sfx_subsystem.json")
SRC_DIR = os.path.join(ROOT, "scripts", "_decoded_kos")
OUT_DIR = os.path.join(ROOT, "assets", "audio", "sfx")
OUT_GD = os.path.join(ROOT, "src", "audio", "Sfx.gd")


def main() -> int:
    data = json.load(open(SRC_JSON, encoding="utf-8"))
    sfx = data["sfx"]
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(OUT_GD), exist_ok=True)

    names, zhs, cats, paths = [], [], [], []
    missing = []
    for e in sfx:
        sid = int(e["id"])
        base = e["file"].split(":")[-1].replace(".KOS", "").replace(".kos", "")
        src = os.path.join(SRC_DIR, base + ".wav")
        if not os.path.exists(src):
            missing.append((sid, base))
            continue
        dst = os.path.join(OUT_DIR, base + ".wav")
        if not os.path.exists(dst) or os.path.getsize(src) != os.path.getsize(dst):
            shutil.copy2(src, dst)
        # 按 id 顺序入表（数组下标即音效 id）
        names.append(base)
        zhs.append(str(e.get("zh", "")))
        cats.append(str(e.get("cat", "")))
        paths.append("res://assets/audio/sfx/%s.wav" % base)

    n = len(names)
    # 校验 id 连续
    ids = [int(e["id"]) for e in sfx]
    if ids != list(range(n)):
        print("  !! id 不连续: %s" % ids[:10])
    if missing:
        print("  !! 缺失 wav: %s" % missing)

    def arr(key: str, vals) -> str:
        body = ",\n\t".join('\t"%s"' % v.replace('"', '\\"') for v in vals)
        return "const %s : Array[String] = [\n\t%s\n]" % (key, body)

    gd = '''extends RefCounted
## 音效常量表（自动生成，勿手改）—— 由 scripts/gen_sfx_assets.py 从
## scripts/sfx_subsystem.json（逆向权威，续195）+ scripts/_decoded_kos/ 生成。
##
## 原版 `play_sfx(id)`（0x4997c0）用数字 id；本表以下标 = id 还原映射。
## ⚠️ 不用 class_name（无头模式不建类缓存），引用方 preload 本脚本。

const COUNT : int = %d

## 下标 = 音效 id → 原文件名（不含扩展名）
%s

## 下标 = 音效 id → 中文语义
%s

## 下标 = 音效 id → 类别（UI / 战斗 / 内政 …）
%s

## 下标 = 音效 id → 资产路径（res://）
%s

## 原版判定为「死资源」的 id（无任何调用点，续248）—— 资产存在但原版从不播放
const DEAD_IDS : Array = [15, 36]
''' % (n, arr("NAMES", names), arr("ZH", zhs),
       arr("CATS", cats), arr("PATHS", paths))

    open(OUT_GD, "w", encoding="utf-8", newline="\n").write(gd)
    print("音效 %d 个 → %s" % (n, OUT_DIR))
    print("常量表 → %s" % OUT_GD)
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
