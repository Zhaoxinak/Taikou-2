# -*- coding: utf-8 -*-
"""找出 +0x2a 相关 setter/getter 的调用方，并做 ecx 溯源（含一层实参下探）。

目标函数：
  0x49a7d0  word[ecx+0x2a] = val            (整字 setter —— 主君索引?)
  0x49ba30  word = (w & 0xffe3) | (v<<2)    (bits2-4 setter)
  0x49ba60  getter (w>>2)&7
  0x49ba70  word = (w & 0xfffc) | min(v,3)  (bits0-1 setter)
  0x49baa0  getter w&3
溯源：向上 12 条指令找 `mov ecx, imm` / `lea ecx, ...` / `push imm; call helper`。
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

import bisect, pickle
from collections import Counter

BASE = 0x400000
d = pickle.load(open(_ROOT + '/scripts/_insn_addrs.pkl', "rb"))
IMAP = d[0]
fstarts = sorted(d[1])
RVAS = sorted(IMAP)

def owner(rva):
    i = bisect.bisect_right(fstarts, rva) - 1
    return fstarts[i] if i >= 0 else fstarts[0]

TARGETS = {
    0x49a7d0: "SET_WORD +0x2a (整字)",
    0x49ba30: "SET bits2-4 (<<2, &0xffe3)",
    0x49ba60: "GET bits2-4 (>>2)&7",
    0x49ba70: "SET bits0-1 (&0xfffc)",
    0x49baa0: "GET bits0-1 (&3)",
}
TRVA = {t - BASE: n for t, n in TARGETS.items()}

# 收集 call 站点
sites = {t: [] for t in TRVA}
for i, r in enumerate(RVAS):
    t = IMAP[r][1]
    if t.startswith("call 0x"):
        tgt = int(t.split()[1], 16) - BASE
        if tgt in TRVA:
            sites[tgt].append(i)

for tr, name in sorted(TRVA.items()):
    ss = sites[tr]
    print("=" * 78)
    print(f"### 0x{tr+BASE:06x}  {name}   调用站点 {len(ss)} 处")
    if not ss:
        print("   (无直接 call 站点)")
        continue
    ctxs = Counter()
    for i in ss:
        lo = max(0, i - 12)
        found = None
        for j in range(i - 1, lo - 1, -1):
            t = IMAP[RVAS[j]][1]
            # 字面基址
            if t.startswith("mov ecx, 0x") or t.startswith("lea ecx,"):
                found = ("LIT", IMAP[RVAS[j]][1])
                break
            if t.startswith("push 0x") and j + 1 == i:
                found = ("ARG", IMAP[RVAS[j]][1])
                break
            if t.startswith("call ") and j + 1 == i:
                found = ("VIACALL", IMAP[RVAS[j]][1])
                break
            if t.startswith("mov ecx,") and "0x" in t:
                found = ("LIT", t)
                break
            if t.startswith("mov ecx,"):
                found = ("REG", t)
                break
        key = found[1] if found else "(未溯源)"
        ctxs[(found[0] if found else "?", key)] += 1
    print("  --- ecx 来源归类 ---")
    for (kind, txt), n in ctxs.most_common():
        print(f"   [{kind:8s}] x{n:<3d} {txt}")
