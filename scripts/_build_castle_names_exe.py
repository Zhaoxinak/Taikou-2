#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build canonical castle-name artifact from the correctly-decoded EXE name
table. Castle id c -> name_table[88 + c] (verified). Capture the 10 authentic
alternate names the game uses internally vs the community castle_names.json."""
import json, os
SC = os.path.dirname(os.path.abspath(__file__))
nt = json.load(open(os.path.join(SC, "name_table.json"), encoding="utf-8"))
cc = json.load(open(os.path.join(SC, "castle_names.json"), encoding="utf-8"))
exenames = nt["castle_town_names"]          # indices 88..291 -> [0..203]
community = {c["id"]: c["name"] for c in cc["castles"]}

canon = []
for c in range(92):
    exe = exenames[c]
    com = community.get(c, "")
    alt = (exe != com)
    canon.append({"id": c, "exe_name": exe, "community_name": com, "is_alt": alt})

alts = [x for x in canon if x["is_alt"]]
print("canonical 92 castles built; %d differ from community table:" % len(alts))
for x in alts:
    print(f"  id={x['id']:2d}  EXE={x['exe_name']!s:6s}  community={x['community_name']}")

out = {
    "source": "EXE name table @0x506ca8, castle block = name_table[88 + id]",
    "note": "EXE names are authoritative in-game names; community table differs in 10 cases "
            "(5 are historical alt names: 泷山/泷川, 兴津/兴泽, 稻叶山/岐阜, 朽木谷/二条, 本愿寺/大阪; "
            "5 are variant kanji of same reading: 二俣/二俁, 长筱/长篠, 桢岛/槙岛, 高规/高槻, 御著/御着).",
    "castles": canon,
}
json.dump(out, open(os.path.join(SC, "castle_names_exe.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("wrote castle_names_exe.json")
