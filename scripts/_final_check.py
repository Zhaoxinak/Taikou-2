# -*- coding: utf-8 -*-
"""_final_check.py — 续95 交付前总校验"""
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

import json, os, subprocess, glob

ROOT = _ROOT
SCR = os.path.join(ROOT, "scripts")
PY = ("C:/Users/Administrator/.workbuddy/binaries/python/envs/"
      "default/Scripts/python.exe")

print("=" * 70)
print("1) 新增参考实现自检")
print("=" * 70)
r = subprocess.run([PY, "diplomacy2_ref.py"], cwd=ROOT,
                   capture_output=True, text=True, timeout=120)
out = (r.stdout or "") + (r.stderr or "")
print("  ", [l for l in out.strip().splitlines() if "RESULT" in l] or out[-200:])

print()
print("=" * 70)
print("2) 所有 spec JSON 有效性")
print("=" * 70)
bad = 0
for p in sorted(glob.glob(os.path.join(SCR, "*_spec.json"))):
    try:
        json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print("  BAD", os.path.basename(p), e)
        bad += 1
print(f"  {len(glob.glob(os.path.join(SCR,'*_spec.json')))} 个 spec JSON，损坏 {bad}")

print()
print("=" * 70)
print("3) BREAKTHROUGHS 续95 锚点")
print("=" * 70)
s = open(os.path.join(ROOT, "BREAKTHROUGHS.md"), encoding="utf-8").read()
for t in ["续95", "续94", "续93"]:
    print(f"  {t}: {s.count(t)} 次")
print("  续89 交叉引用已加:", "续95 已闭合前两项" in s)

print()
print("=" * 70)
print("4) 全工程自检")
print("=" * 70)
r = subprocess.run([PY, "_run_all_selfchecks.py"], cwd=SCR,
                   capture_output=True, text=True, timeout=900)
lines = [l for l in r.stdout.splitlines() if "结果:" in l or "PASS /" in l]
print("  ", lines[-1] if lines else r.stdout[-300:])

print()
print("=" * 70)
print("5) 技能文件")
print("=" * 70)
sk = ("C:/Users/Administrator/.workbuddy/skills/"
      "taikou2-indirect-dispatch-reverse/SKILL.md")
print("  存在:", os.path.exists(sk), " 大小:", os.path.getsize(sk) if os.path.exists(sk) else 0)
