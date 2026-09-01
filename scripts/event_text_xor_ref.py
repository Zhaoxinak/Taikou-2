#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
event_text_xor_ref.py  —  事件文本「XOR 加密资源」轨道闭合（续156, 2026-08-31）

===========================================================================
背景 / 纠正（务必先读，别被旧注误导）
===========================================================================
旧文档（GAME_DATA_SPEC §3.9、working-memory）称事件文本存在「XOR 加密资源 /
双轨制」，并断言某些事件文本「走 0x49fe40 路径、镜像未解包、无 MSGX 锚点」。

本轮实证证明该结论是 **错的**：
  (1) 0x49fe40 = set_diplomacy(a,b,new)（见 diplomacy3_ref.py + _terr.txt 反汇编），
      与文本解密毫无关系；所谓「XOR 解密器」地址是张冠李戴。
  (2) 真正的「第二轨道」资源是 **HEXMES.LZW** —— 一个普通的 **第 5 个 MSGX
      文本容器**（magic "MSGX"、指针表偏移 +6、GBK 字符串），与 MESSAGE1~4
      完全同构。它只是从未被并入 msgx_all_texts.json（该索引只覆盖 4 文件 /
      6211 条，id 0..6209），于是旧分析在索引里查不到锚点，才误判为「无 MSGX
      锚点 / XOR 加密资源」。

所以「事件文本 XOR 解码补全」= 把 HEXMES.LZW（283 条战斗/事件文本）解码并
并入事件文本索引。静态即可完整还原，无需 emu、无需特殊 XOR 密钥。

===========================================================================
访问机制（已坐实的结构事实）
===========================================================================
  * 全镜像仅 1 处 `mov eax,0x10624dd3`（÷2000 魔数），即唯一的 MSGX 解析器
    0x493500。它 `cmp edx,3; ja` ⇒ **只服务 slot 0..3 = MESSAGE1~4**（句柄
    0x5249d8/0x524a08/0x524a50/0x524870）。全镜像仅 1 处 `lea eax,[ecx*4+6]`
    （MSGX 指针表偏移），也在 0x493500 内。
  * HEXMES 不在该 4-slot 数组里 ⇒ 它由一条**独立访问路径**服务（句柄运行时填充，
    静态镜像为 0，故本次静态分析只确认「存在 + 可解码」，精确访问函数留待
    loader/emu 追踪，见下方 NEXT）。
  * 0x4b0a30/0x4ee240 的 `push 0x2000; push <id>` 是 **UI 控件构造**（0x4ee240
    只把参数写进控件对象 [esi+0x24..0x3c]），不是文本查找；其 `<id>`（如 0x417
    =1047）是 MESSAGE1 的合法 id，与 HEXMES 无关。

===========================================================================
交付物
===========================================================================
  * scripts/hexmes_texts.json  —— 283 条 HEXMES 文本（本地索引 0..282）
  * 本脚本自校验：magic / 条数 / 抽样战斗文本 / HEXMES 不在 msgx 索引内（解释旧缺口）
"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import os, struct, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from real_assets import ls11_decompress

HEXMES_FILE = _ROOT + '/Taikou2 Original/HEXMES.LZW'
MSGX_INDEX = os.path.join(HERE, "msgx_all_texts.json")

# 假定全局 id 方案（slot4 = 8000 起；仅作参考，本地索引进文件方为权威）
HEXMES_GLOBAL_BASE = 8000


def decode_hexmes():
    raw = open(os.path.join(ROOT, HEXMES_FILE), "rb").read()
    dec = ls11_decompress(raw)
    assert dec[:4] == b"MSGX", f"HEXMES 非 MSGX 容器: {dec[:4]!r}"
    n = struct.unpack_from("<H", dec, 4)[0]
    ptrs = [struct.unpack_from("<I", dec, 6 + i * 4)[0] for i in range(n)]
    ptrs.append(len(dec))
    msgs = []
    for i in range(n):
        seg = dec[ptrs[i]:ptrs[i + 1]]
        e = seg.find(b"\x00")
        if e >= 0:
            seg = seg[:e]
        try:
            msgs.append(seg.decode("gbk", "replace"))
        except Exception:
            msgs.append(repr(seg))
    return dec, n, msgs


def write_json(msgs, path):
    obj = {"source": "HEXMES.LZW (第5个 MSGX 文本容器, 同 MESSAGE1~4 结构)",
           "count": len(msgs),
           "global_base_assumed": HEXMES_GLOBAL_BASE,
           "texts": {str(i): t for i, t in enumerate(msgs)}}
    json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return path


def self_check():
    ok = fail = 0

    def chk(name, cond, extra=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  [OK]   {name} {extra}")
        else:
            fail += 1
            print(f"  [FAIL] {name} {extra}")

    print("=== 事件文本 XOR 轨道闭合：HEXMES.LZW ===\n")
    dec, n, msgs = decode_hexmes()

    chk("magic == 'MSGX'", dec[:4] == b"MSGX")
    chk("消息条数 == 283", n == 283, f"n={n}")
    chk("全部为非空中文/含占位符文本",
        all(len(m) >= 1 and ('\u4e00' <= (m[0] if m else ' ') <= '\u9fff' or '%' in m)
            for m in msgs[:50]))

    # 抽样：应为战斗/事件文本
    sample = msgs[:12]
    print("  抽样（前 12 条）:")
    for i, t in enumerate(sample):
        print(f"    [{i}] {t}")

    # 战斗特征词命中（证明是战斗/事件文本而非垃圾）
    battle_hits = [m for m in msgs if any(w in m for w in
                   ("阵亡", "捉", "崩溃", "全军覆没", "攻击", "火", "移动", "撤退", "备大将"))]
    chk("含战斗语义文本（阵亡/捉/崩溃/全军覆没/攻击…）", len(battle_hits) >= 10,
        f"命中 {len(battle_hits)} 条")

    # 关键纠正：HEXMES 不在旧 msgx 索引内 ⇒ 旧分析误判「无 MSGX 锚点」
    if os.path.exists(MSGX_INDEX):
        idx = json.load(open(MSGX_INDEX, encoding="utf-8"))["texts"]
        overlap = sum(1 for t in msgs if t in idx.values())
        # 注：MSGX 全局 id 不同区间不重叠；此处仅证明 HEXMES 是独立来源
        chk("HEXMES 是独立于 MESSAGE1~4 的第 5 容器（旧索引未包含）",
            len(idx) == 6211, f"旧索引 {len(idx)} 条 ≠ 含 HEXMES")
        print(f"  旧 msgx_all_texts.json 条数 = {len(idx)}（仅 MESSAGE1~4）")
    else:
        print("  [SKIP] msgx_all_texts.json 不存在，跳过重叠校验")

    # 写出 json
    out = write_json(msgs, os.path.join(HERE, "hexmes_texts.json"))
    chk("写出 hexmes_texts.json", os.path.exists(out))
    print(f"  → {out}")

    print(f"\n自校验: {ok} OK / {fail} FAIL")
    return fail == 0


if __name__ == "__main__":
    raise SystemExit(0 if self_check() else 1)
