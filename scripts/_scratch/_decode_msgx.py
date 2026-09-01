#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解码 MESSAGE*.LZW (MSGX+GBK) 全部文本，并按战斗词汇搜索，配对 HJMAPDAT 9 单位 id。"""
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

import os, struct, json, sys
sys.path.insert(0, os.path.dirname(__file__))
from real_assets import ls11_decompress

DATA_ROOT = "F:/Games/Taikou2"
OUT = _ROOT + '/scripts/_probe/msgx'
os.makedirs(OUT, exist_ok=True)

def decode_msgx(fname):
    raw = open(os.path.join(DATA_ROOT, fname), "rb").read()
    dec = ls11_decompress(raw)
    if not dec or dec[:4] != b"MSGX":
        return None, []
    n = struct.unpack_from("<H", dec, 4)[0]
    ptrs = [struct.unpack_from("<I", dec, 6 + i*4)[0] for i in range(n)]
    ptrs.append(len(dec))
    msgs = []
    for i in range(n):
        seg = dec[ptrs[i]:ptrs[i+1]]
        # GBK decode up to first null
        end = seg.find(b"\x00")
        if end >= 0:
            seg = seg[:end]
        try:
            txt = seg.decode("gbk", "replace")
        except Exception:
            txt = repr(seg)
        msgs.append(txt)
    return dec, msgs

all_msgs = []   # list of (file, index, text)
per_file = {}
for fname in ["MESSAGE1.LZW", "MESSAGE2.LZW", "MESSAGE3.LZW", "MESSAGE4.LZW"]:
    dec, msgs = decode_msgx(fname)
    if dec is None:
        print(f"{fname}: FAIL")
        continue
    per_file[fname] = msgs
    print(f"{fname}: raw={len(dec)}B, {len(msgs)} msgs")
    for i, t in enumerate(msgs):
        all_msgs.append((fname, i, t))

# 保存全部文本
with open(os.path.join(OUT, "all_messages.txt"), "w", encoding="utf-8") as f:
    for fn, i, t in all_msgs:
        f.write(f"[{fn}#{i}] {t}\n")

print(f"\nTOTAL messages: {len(all_msgs)}")

# ── 战斗词汇搜索 ──────────────────────────────────────
BATTLE_WORDS = ["足軽","足轻","騎馬","骑兵","鉄砲","铁炮","弓","攻城","水軍","水军",
                "忍者","一向","母衣","槍","枪","鶴翼","鶴","魚鱗","鱼鳞","偃月","鋒矢","锋矢",
                "火計","火计","伏兵","罠","陷阱","投石","攻城槌","井欄","井栏","神火","鼓舞",
                "陣形","阵形","計略","计略","兵種","兵种","部隊","部队","武将","鉄騎","铁骑",
                "砲","炮","盾","突撃","突击","防柵","防栅","城","本陣","本阵","柵","栅"]
hits = {}
for fn, i, t in all_msgs:
    for w in BATTLE_WORDS:
        if w in t:
            hits.setdefault(w, []).append((fn, i, t))

print("\n=== 战斗词汇命中 ===")
for w in BATTLE_WORDS:
    if w in hits:
        print(f"\n【{w}】{len(hits[w])} 处")
        for fn, i, t in hits[w][:8]:
            print(f"   {fn}#{i}: {t}")

# ── 找连续的单位/阵形/计略名称块 ────────────────────────
# 兵种通常 2 字；尝试定位连续 2 字词的密集区
print("\n=== 候选：2 字战斗名词密集块（前 40 条含 battle 词）===")
cnt = 0
for fn, i, t in all_msgs:
    if any(w in t for w in ["足","騎","鉄","铁","弓","攻","水","忍","陣","鶴","魚","計","伏","火","突","盾"]):
        print(f"   {fn}#{i}: {t}")
        cnt += 1
        if cnt >= 40:
            break
