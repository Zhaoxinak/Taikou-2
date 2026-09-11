# -*- coding: utf-8 -*-
import json

texts = json.load(open("scripts/msgx_all_texts.json", "r", encoding="utf-8"))["texts"]
kws = ["义父", "义子", "义兄", "义弟", "血缘", "姻戚", "女婿", "养子", "縁者", "亲族", "一族", "父子", "父亲", "儿子", "哥哥", "弟弟", "主君", "盟友"]
lines = []
for kw in kws:
    hits = [(int(k), v) for k, v in texts.items() if kw in v]
    if hits:
        lines.append(f"=== {kw} ({len(hits)}) ===")
        for i, v in sorted(hits)[:12]:
            lines.append(f"  {i}: {v[:100]}")

# Also: province names table? check if 1f geography matches
# 织田 id17 → table 16. What's province 16?
# Look for province name table in known addrs
lines.append("\n=== known province check ===")
# From game knowledge 尾张 is often around mid; 
# Read GAME or names if available
import os
for p in ["scripts/bsdata_names.json", "scripts/province_names.json", "scripts/kokudata_names.json"]:
    if os.path.exists(p):
        lines.append(f"found {p}")

open("scripts/_scratch/_rel_msgx.txt", "w", encoding="utf-8").write("\n".join(lines))
print("hits lines", len(lines))
for L in lines[:40]:
    print(L)
