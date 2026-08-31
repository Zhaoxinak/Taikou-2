# -*- coding: utf-8 -*-
"""全工程破解进度审计: 汇总所有 *_spec.json 的 still_unknown / 待破字段。"""
import json, os, glob, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)

UNKNOWN_KEYS = ("still_unknown", "unknown", "todo", "open_questions",
                "unresolved", "待破", "仍未知")

def walk_unknown(obj, path=""):
    """递归找出所有 unknown 类键。"""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kp = f"{path}.{k}" if path else k
            if k.lower() in UNKNOWN_KEYS or k in UNKNOWN_KEYS:
                out.append((kp, v))
            else:
                out.extend(walk_unknown(v, kp))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(walk_unknown(v, f"{path}[{i}]"))
    return out

print("=" * 78)
print("  太阁立志传2 逆向工程 — 破解进度审计")
print("=" * 78)

specs = sorted(glob.glob(os.path.join(BASE, "*_spec.json")))
total_unknown = 0
per_spec = []

for sp in specs:
    name = os.path.basename(sp)
    try:
        d = json.load(open(sp, encoding="utf-8"))
    except Exception as e:
        print(f"\n[{name}] JSON 解析失败: {e}")
        continue
    unks = walk_unknown(d)
    cnt = 0
    closed = 0
    items = []

    def is_closed(s):
        """以 ✅ / [已破 开头的条目视为已闭合, 不计入未破。"""
        t = s.lstrip()
        return t.startswith("✅") or t.startswith("[已破")

    for kp, v in unks:
        if isinstance(v, list):
            for it in v:
                s = it if isinstance(it, str) else json.dumps(it, ensure_ascii=False)
                if is_closed(s):
                    closed += 1
                    continue
                items.append((kp, s))
            cnt += len(v)
        elif isinstance(v, str):
            if is_closed(v):
                closed += 1
            else:
                items.append((kp, v))
            cnt += 1
        elif isinstance(v, dict):
            for k2, v2 in v.items():
                s = str(v2)
                if is_closed(s):
                    closed += 1
                    continue
                items.append((f"{kp}.{k2}", s))
            cnt += len(v)
    # cnt 只计真正未破
    cnt = len(items)
    total_unknown += cnt
    per_spec.append((name, cnt, items, d.get("selfcheck") or d.get("self_check")))

print("\n### 一、各规格文件未破项计数\n")
print(f"{'规格文件':<32}{'未破项':>7}   自检状态")
print("-" * 78)
for name, cnt, items, sc in per_spec:
    mark = "✅ 全闭合" if cnt == 0 else f"🔶 {cnt} 项开放"
    scs = (sc or "")[:28]
    print(f"{name:<32}{cnt:>7}   {scs}")
print("-" * 78)
print(f"{'合计':<32}{total_unknown:>7}")

print("\n### 二、未破项明细\n")
for name, cnt, items, sc in per_spec:
    if not items:
        continue
    print(f"\n【{name}】")
    for kp, s in items:
        s1 = s.replace("\n", " ")
        if len(s1) > 150:
            s1 = s1[:150] + "…"
        print(f"  - ({kp}) {s1}")

# ref 自检文件清单
refs = sorted(glob.glob(os.path.join(BASE, "*_ref.py")))
print(f"\n### 三、参考实现 (自检脚本) 共 {len(refs)} 个")
print("  " + ", ".join(os.path.basename(r) for r in refs))
