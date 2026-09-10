#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BGM 素材接入生成器 —— 原版 CD 音轨（中文版 MP3/ 方案）→ Godot 常量表。

权威依据（本轮新破，见 BREAKTHROUGHS）：
  * `0x498f45`: `push 0x22`(=34) + `mov ecx, 0x5256c4` + `call 0x498e60`
    ⇒ **BGM 子系统对象 0x5256c4，轨数 = 34**，与 `Taikou2 Original/MP3/01..34.mp3` 一一对应。
    （同址 `push 0x27`(=39) + `mov ecx, 0x5256c8` = 音效子系统，与 sfx 表 39 项互证。）
  * BGM 播放入口 = `CdPlay` @0x401310（4 参：track, flag, from, to），
    轨号 = 槽位 + 2（`0x498eb8 add al,2`），门控 `word[0x50b8f0]==4`。

产物：
  src/audio/Bgm.gd        —— COUNT / PATHS / DUR / SLOT_OFFSET 常量表
  scripts/bgm_tracks.json —— 轨号→文件/时长/大小 清单（供 Python↔Godot 交叉校验）

用法：python scripts/gen_bgm_assets.py
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC_DIR = os.path.join(ROOT, "Taikou2 Original", "MP3")
OUT_GD = os.path.join(ROOT, "src", "audio", "Bgm.gd")
OUT_JSON = os.path.join(HERE, "bgm_tracks.json")

TRACK_COUNT = 34  # 0x498f45 push 0x22

# —— MP3 帧头解析（CBR + Xing/VBRI）——
_BR = {
    (1, 3): [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0],
    (2, 3): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],
    (25, 3): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],
    (1, 1): [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, 0],
    (1, 2): [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, 0],
    (2, 1): [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, 0],
    (2, 2): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],
}
_SR = {1: [44100, 48000, 32000], 2: [22050, 24000, 16000], 25: [11025, 12000, 8000]}
_SPF = {(1, 1): 384, (1, 2): 1152, (1, 3): 1152, (2, 1): 384, (2, 2): 1152, (2, 3): 576,
        (25, 1): 384, (25, 2): 1152, (25, 3): 576}


def _find_frame(d, start=0):
    """定位第一个合法 MP3 帧同步字，返回偏移；未找到返回 -1"""
    n = len(d)
    i = start
    while i < n - 4:
        if d[i] == 0xFF and (d[i + 1] & 0xE0) == 0xE0:
            ver_bits = (d[i + 1] >> 3) & 3
            layer = (d[i + 1] >> 1) & 3
            br_idx = (d[i + 2] >> 4) & 0xF
            sr_idx = (d[i + 2] >> 2) & 3
            if (ver_bits != 1 and layer != 0 and br_idx not in (0, 15) and sr_idx != 3):
                return i
        i += 1
    return -1


def mp3_duration(path):
    """返回秒（float）。优先 Xing/Info 帧数，否则按 CBR 估算。"""
    d = open(path, "rb").read()
    # 跳过 ID3v2
    off = 0
    if d[:3] == b"ID3":
        size = ((d[6] & 0x7F) << 21) | ((d[7] & 0x7F) << 14) | ((d[8] & 0x7F) << 7) | (d[9] & 0x7F)
        off = 10 + size
    f = _find_frame(d, off)
    if f < 0:
        return 0.0
    b1, b2, b3 = d[f], d[f + 1], d[f + 2]
    ver_bits = (b2 >> 3) & 3
    ver = {3: 1, 2: 2, 0: 25}.get(ver_bits, 2)
    layer = 4 - ((b2 >> 1) & 3)
    br_idx = (b3 >> 4) & 0xF
    sr_idx = (b3 >> 2) & 3
    key = (ver, layer)
    if key not in _BR:
        return 0.0
    bitrate = _BR[key][br_idx] * 1000
    sample_rate = _SR[ver][sr_idx]
    spf = _SPF[key]
    if bitrate == 0 or sample_rate == 0:
        return 0.0
    # Xing / Info（VBR 帧数）
    side = 32 if (ver == 1) else 17
    xing = d[f + 4 + side: f + 4 + side + 4]
    if xing in (b"Xing", b"Info"):
        flags = struct.unpack_from(">I", d, f + 4 + side + 4)[0]
        p = f + 4 + side + 8
        if flags & 1:
            frames = struct.unpack_from(">I", d, p)[0]
            return frames * spf / float(sample_rate)
    # CBR 估算
    return (len(d) - f) * 8.0 / bitrate


def arr_str(name, values, typed=False):
    body = ", ".join(('"%s"' % v) if isinstance(v, str) else str(v) for v in values)
    return "const %s: Array%s = [%s]" % (name, ("[float]" if typed else ""), body)


def main():
    tracks = []
    ok = True
    for t in range(1, TRACK_COUNT + 1):
        fn = "%02d.mp3" % t
        p = os.path.join(SRC_DIR, fn)
        if not os.path.exists(p):
            print("  MISSING", fn)
            ok = False
            dur = 0.0
            size = 0
        else:
            dur = mp3_duration(p)
            size = os.path.getsize(p)
            if dur <= 0:
                ok = False
                print("  BAD DURATION", fn)
        tracks.append({"track": t, "file": fn,
                       "path": "res://Taikou2 Original/MP3/%s" % fn,
                       "duration": round(dur, 2), "size": size})

    paths = [t["path"] for t in tracks]
    durs = [t["duration"] for t in tracks]

    gd = '''extends RefCounted
## Bgm — 原版 BGM（CD 音轨 / 中文版 MP3 方案）常量表 —— 由 scripts/gen_bgm_assets.py 生成，勿手改。
##
## 权威依据：
##   * 轨数 34 = `0x498f45 push 0x22` + `mov ecx,0x5256c4`(BGM 子系统对象) + `call 0x498e60`;
##     同址 `push 0x27`(=39) + `mov ecx,0x5256c8` 为音效子系统（与 Sfx.COUNT=39 互证）。
##   * 播放入口 = `CdPlay` @0x401310（4 参 track/flag/from/to）；`add esp,0x10` 实证。
##   * 槽位→轨号：**轨号 = 槽位 + 2**（`0x498eb8 add al,2`）。
##   * 轨 0 = 停止（走 CdStopClose 0x4012c0）；正在播同轨则跳过（防重播，0x401322）。
##
## ⚠️ 不声明 class_name（无头 --script 模式不建全局类缓存），引用方 preload。

## CD 音轨总数（= MP3/ 下文件数，原版 0x22）
const COUNT: int = %d
## 合法轨号范围（MCI CD 轨号 1-based）
const TRACK_MIN: int = 1
const TRACK_MAX: int = %d
## 槽位→轨号偏移（原版 0x498eb8）
const SLOT_OFFSET: int = 2

%s

%s

## 槽位（原版 BGM 枚举）→ CD 轨号；越界返回 0（= 停止）
static func track_for_slot(slot: int) -> int:
	if slot < 0:
		return 0
	return slot + SLOT_OFFSET

## 轨号 → 文件名（01.mp3 .. 34.mp3）
static func file_of(track: int) -> String:
	if track < TRACK_MIN or track > TRACK_MAX:
		return ""
	return "%%02d.mp3" %% track
''' % (TRACK_COUNT, TRACK_COUNT,
       arr_str("PATHS", paths), arr_str("DUR", durs, typed=True))

    os.makedirs(os.path.dirname(OUT_GD), exist_ok=True)
    with open(OUT_GD, "w", encoding="utf-8") as f:
        f.write(gd)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"count": TRACK_COUNT, "tracks": tracks}, f, ensure_ascii=False, indent=2)

    total = sum(t["duration"] for t in tracks)
    print("BGM 轨数 %d，总时长 %.1f 秒（%.1f 分钟）" % (len(tracks), total, total / 60.0))
    for t in tracks[:6]:
        print("  轨 %2d  %6.2fs  %s" % (t["track"], t["duration"], t["file"]))
    print("  ...")
    for t in tracks[-3:]:
        print("  轨 %2d  %6.2fs  %s" % (t["track"], t["duration"], t["file"]))
    print("产物:", OUT_GD)
    print("清单:", OUT_JSON)
    print("[selftest] %s" % ("PASS" if ok and len(tracks) == TRACK_COUNT else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
