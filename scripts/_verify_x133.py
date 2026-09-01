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
import json, glob

s = open(_ROOT + '/BREAKTHROUGHS.md', encoding="utf-8").read()
i = s.find("续133）")
j = s.find("续132）")
blk = s[i:j]
print("续133 block len:", len(blk))
TOK = ["0x49a5f0", "0x49a8b0", "0x49a630", "0x49a770", "0x49a7b0", "0x49a820",
       "0x49a840", "0x49a860", "0xEA60", "60000", "0x9FFF", "0xF8FF",
       "0x513b14", "64/64", "忠诚", "功勲", "F2B", "0x49a7bf", "续127"]
miss = [t for t in TOK if t not in blk]
for t in TOK:
    print(("  OK   " if t in blk else "  MISS "), t)
print("\nMISSING:", miss if miss else "无")

bad = 0
for p in sorted(glob.glob(_ROOT + '/scripts/*_spec.json')):
    try:
        json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print("  BAD", p, e)
        bad += 1
print("\n全 spec JSON:", "全部有效" if bad == 0 else f"{bad} 个损坏")

d = json.load(open(_ROOT + '/scripts/bsdata_spec.json', encoding="utf-8"))
print("\n尾段字段数:", len(d["entity_tail_method_table"]["fields"]))
print("+0x26     :", d["entity_tail_method_table"]["fields"]["+0x26"])
print("+0x29     :", d["entity_tail_method_table"]["fields"]["+0x29"])
print("ref impl  :", d["reference_impl"])
for fn in ("promo_spec.json", "promote3_spec.json"):
    dd = json.load(open(_ROOT + '/scripts/' + fn, encoding="utf-8"))
    for k in ("still_unknown", "open_questions"):
        if k in dd:
            print(f"{fn}[{k}] 已闭:", sum(1 for x in dd[k] if str(x).startswith("✅")),
                  "/", len(dd[k]))
