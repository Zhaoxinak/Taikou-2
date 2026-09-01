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
i = s.find("续132）")
j = s.find("续131）")
blk = s[i:j]
print("续132 block len:", len(blk))
TOK = ["0x513b14", "0x49a2b0", "0x49a350", "0x49a4d0", "0x49a500", "0x49a5a0",
       "0x49a5c0", "0x49a5e0", "0x507b58", "0x507fc0", "0x0a", "0x0e", "0x1b",
       "统御力", "魅力", "102/102", "12 (0x0C)", "0x49a630", "0x440cxx"]
miss = [t for t in TOK if t not in blk]
for t in TOK:
    print(("  OK   " if t in blk else "  MISS "), t)
print("\nMISSING:", miss if miss else "无")

print("\n=== 全 spec JSON ===")
bad = 0
for p in sorted(glob.glob(_ROOT + '/scripts/*_spec.json')):
    try:
        json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print("  BAD", p, e)
        bad += 1
print("  全部有效" if bad == 0 else f"  {bad} 个损坏")

d = json.load(open(_ROOT + '/scripts/bsdata_spec.json', encoding="utf-8"))
print("\n=== bsdata_spec ===")
print("  remap        :", d["entity_offset_remap"]["rule"])
print("  ability block:", d["entity_ability_block"]["mapping"])
print("  method table :", d["entity_method_table"]["object_pointer"])
print("  ref impl     :", d["reference_impl"])
