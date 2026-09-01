# -*- coding: utf-8 -*-

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
import json, os

ROOT = _ROOT
s = open(os.path.join(ROOT, "BREAKTHROUGHS.md"), encoding="utf-8").read()

i = s.find("（续95）")
j = s.find("## [2026-08-29（续94）]")
blk = s[i:j]
print("续95 block chars:", len(blk))
print("续95 位置:", i, " 续94 位置:", j)

TOK = ["0x51dc60", "0x49fd80", "0x49fe40", "0x49ff10", "0x49fe37", "0x49ff0d",
       "0x5080d0", "0x5080f8", "0x4b981c", "0x4b985c", "0x4c4270", "0x4c7734",
       "0x4c2e4e", "0x4d9e50", "0x4b97a8", "0x4b9890", "0x4b9ae0", "0x4c5699",
       "0x525ea4", "0x525ea0", "0x51eb88", "0x66666667", "0x4b956e", "0x4b94f4",
       "0x4b94ac", "0x5179b8", "0x51dc5f", "0x47f045", "0x4b8f70", "0x4b9250"]
miss = [t for t in TOK if t not in blk]
print("tokens PRESENT:", len(TOK) - len(miss), "/", len(TOK))
if miss:
    print("MISSING:", miss)

# 关键中文串（确认没被 shell 破坏）
CN = ["上三角", "主从関係", "外交関係", "盟友", "支配", "从属",
      "0x66666667", "除数", "20", "功勋", "纠偏"]
print("中文串检查:", {c: (c in blk) for c in CN})

# JSON 有效性
p = os.path.join(ROOT, "scripts", "diplomacy_spec.json")
d = json.load(open(p, encoding="utf-8"))
print("diplomacy_spec.json OK, keys:", list(d.keys()))
print("  core_api:", list(d["core_api"].keys()))
print("  still_unknown:", len(d["still_unknown"]), "条")
print("  corrections:", len(d["corrections_to_89"]), "条")
