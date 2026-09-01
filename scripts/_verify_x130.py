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
import json, glob, subprocess, sys

P = _ROOT + '/BREAKTHROUGHS.md'
s = open(P, encoding="utf-8").read()
i = s.find("续130）")
j = s.find("续129）")
blk = s[i:j]
print("续130 block len:", len(blk))
TOK = ["0x507b58", "0x507fc0", "0x4c7c30", "0x4c7e84", "0x4447948", "0x47d890",
       "0x50c3cc", "0x507fdc", "1096/1096", "41300", "59×700", "700/700",
       "0x409340", "bsdata_fields_ref.py", "技能名表", "能力名表", "续55"]
miss = [t for t in TOK if t not in blk]
for t in TOK:
    print(("  OK   " if t in blk else "  MISS "), t)
print("\nMISSING:", miss if miss else "无")

print("\n=== 全 spec JSON 有效性 ===")
bad = 0
for p in sorted(glob.glob(_ROOT + '/scripts/*_spec.json')):
    try:
        json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print("  BAD", p, e)
        bad += 1
print("  全部有效" if bad == 0 else f"  {bad} 个损坏")

print("\n=== bsdata_spec 关键字段 ===")
d = json.load(open(_ROOT + '/scripts/bsdata_spec.json', encoding="utf-8"))
print("  skill_mapping.status :", d["skill_mapping"]["status"])
print("  ability_names        :", d["ability_names"]["values"])
print("  attr_score_table     :", len(d["attr_score_table"]["table"]), "项")
print("  reference_impl       :", d.get("reference_impl"))
print("  still_unknown 已闭   :", sum(1 for x in d["still_unknown"] if x.startswith("✅")))
