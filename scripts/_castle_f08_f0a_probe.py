# -*- coding: utf-8 -*-
"""找城表 `+0x08` / `+0x0a` 的消费方。

只取「引用了城表 0x51eb88 区域或 stride 31」的函数，再在其中找 [reg+8] / [reg+0xa] 访问，
输出 ±6 条上下文，便于人工判语义。
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

import bisect, pickle, re, sys

BASE = 0x400000
d = pickle.load(open(_ROOT + '/scripts/_insn_addrs.pkl', "rb"))
IMAP = d[0]
FSTART = sorted(d[1])
RVAS = sorted(IMAP)


def owner(r):
    i = bisect.bisect_right(FSTART, r) - 1
    return FSTART[i] if i >= 0 else FSTART[0]


def fend(r):
    i = bisect.bisect_right(FSTART, r) - 1
    return FSTART[i + 1] if i + 1 < len(FSTART) else max(IMAP) + 1


TBL = 0x51EB88

# 涉城表函数：字面 0x51eb88 / +31 迭代 / ×31(shl5-sub)
cand = set()
for i, r in enumerate(RVAS):
    t = IMAP[r][1]
    if "0x51eb88" in t or "add esi, 0x1f" in t or "add edi, 0x1f" in t or "add ebx, 0x1f" in t \
       or "add eax, 0x1f" in t or "add ecx, 0x1f" in t:
        cand.add(owner(r))
print("涉城表函数数:", len(cand))

TARGETS = ["+ 8]", "+ 0xa]"]
hits = {}
for f in sorted(cand):
    e = min(fend(f), f + 0x600)
    body = [(r + BASE, IMAP[r][1]) for r in RVAS[bisect.bisect_left(RVAS, f):bisect.bisect_left(RVAS, e)]]
    for idx, (a, t) in enumerate(body):
        if "[" not in t or "esp" in t.split("[")[1][:4] or "ebp" in t.split("[")[1][:4]:
            continue
        m = re.search(r"\[(\w+)(?:\s*\+\s*(0x[0-9a-f]+|\d+))?\]", t)
        if not m:
            continue
        disp_s = m.group(2)
        if disp_s is None:
            continue
        disp = int(disp_s, 16) if disp_s.startswith("0x") else int(disp_s)
        if disp not in (8, 0xa):
            continue
        hits.setdefault((f + BASE, disp), []).append((idx, body))

print("命中 (函数, 偏移) 组数:", len(hits))
print()
for (f, disp) in sorted(hits, key=lambda x: (x[1], x[0])):
    idx, body = hits[(f, disp)][0]
    print(f"----- func 0x{f:06x}  [reg+{'0x%x' % disp}]  (共 {len(hits[(f, disp)])} 处) -----")
    shown = set()
    for (i2, _) in hits[(f, disp)]:
        for j in range(max(0, i2 - 6), min(len(body), i2 + 7)):
            if j in shown:
                continue
            shown.add(j)
            a, t = body[j]
            mark = "   <<<< HIT" if j == i2 else ""
            print(f"  0x{a:06x}  {t}{mark}")
        print("  " + "-" * 44)
    print()
