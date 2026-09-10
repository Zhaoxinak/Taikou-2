extends RefCounted
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
const COUNT: int = 34
## 合法轨号范围（MCI CD 轨号 1-based）
const TRACK_MIN: int = 1
const TRACK_MAX: int = 34
## 槽位→轨号偏移（原版 0x498eb8）
const SLOT_OFFSET: int = 2

const PATHS: Array = ["res://Taikou2 Original/MP3/01.mp3", "res://Taikou2 Original/MP3/02.mp3", "res://Taikou2 Original/MP3/03.mp3", "res://Taikou2 Original/MP3/04.mp3", "res://Taikou2 Original/MP3/05.mp3", "res://Taikou2 Original/MP3/06.mp3", "res://Taikou2 Original/MP3/07.mp3", "res://Taikou2 Original/MP3/08.mp3", "res://Taikou2 Original/MP3/09.mp3", "res://Taikou2 Original/MP3/10.mp3", "res://Taikou2 Original/MP3/11.mp3", "res://Taikou2 Original/MP3/12.mp3", "res://Taikou2 Original/MP3/13.mp3", "res://Taikou2 Original/MP3/14.mp3", "res://Taikou2 Original/MP3/15.mp3", "res://Taikou2 Original/MP3/16.mp3", "res://Taikou2 Original/MP3/17.mp3", "res://Taikou2 Original/MP3/18.mp3", "res://Taikou2 Original/MP3/19.mp3", "res://Taikou2 Original/MP3/20.mp3", "res://Taikou2 Original/MP3/21.mp3", "res://Taikou2 Original/MP3/22.mp3", "res://Taikou2 Original/MP3/23.mp3", "res://Taikou2 Original/MP3/24.mp3", "res://Taikou2 Original/MP3/25.mp3", "res://Taikou2 Original/MP3/26.mp3", "res://Taikou2 Original/MP3/27.mp3", "res://Taikou2 Original/MP3/28.mp3", "res://Taikou2 Original/MP3/29.mp3", "res://Taikou2 Original/MP3/30.mp3", "res://Taikou2 Original/MP3/31.mp3", "res://Taikou2 Original/MP3/32.mp3", "res://Taikou2 Original/MP3/33.mp3", "res://Taikou2 Original/MP3/34.mp3"]

const DUR: Array[float] = [76.7, 67.06, 62.59, 58.33, 64.0, 62.12, 81.37, 81.14, 93.34, 59.14, 61.28, 97.18, 70.03, 85.19, 60.21, 71.81, 61.13, 77.51, 82.29, 57.03, 146.73, 140.07, 129.12, 115.2, 36.99, 160.16, 112.17, 9.98, 9.98, 9.98, 9.98, 10.29, 9.98, 9.98]

## 槽位（原版 BGM 枚举）→ CD 轨号；越界返回 0（= 停止）
static func track_for_slot(slot: int) -> int:
	if slot < 0:
		return 0
	return slot + SLOT_OFFSET

## 轨号 → 文件名（01.mp3 .. 34.mp3）
static func file_of(track: int) -> String:
	if track < TRACK_MIN or track > TRACK_MAX:
		return ""
	return "%02d.mp3" % track
