# -*- coding: utf-8 -*-
"""
Build scripts/skill_master_table.json — skill → training route table.

Sources:
  - skills_spec.json (10 skill names, selector categories)
  - name_table.json role_type_names (师父/NPC pool)
  - MSGX all_messages.txt (town/master hints)
  - EXE static: skill registry builder 0x443d80, character pool base 0x517850 (12B stride)
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MSGX = os.path.join(ROOT, "scripts", "_probe", "msgx", "all_messages.txt")


def load_msgx_hints():
    hints = {}
    if not os.path.isfile(MSGX):
        return hints
    text = open(MSGX, encoding="utf-8", errors="replace").read()
    patterns = [
        (0, r"辩才.*受教|口才"),
        (1, r"马术.*马行|马行.*学习"),
        (2, r"算术.*京|算术.*界镇|算术.*商人"),
        (3, r"剑术.*鹿岛|上泉伊势守"),
        (4, r"忍术.*小田原|忍术.*奈良|忍者"),
        (5, r"兵法.*军事|兵法.*武将"),
        (6, r"洋枪.*杂贺|国友|铸造"),
        (7, r"筑城.*穴太|筑城.*巧匠|筑城.*武将"),
        (8, r"礼法.*京|礼法.*甲府|礼法.*严岛|高僧"),
        (9, r"茶道.*千宗|茶道.*界镇"),
    ]
    for idx, pat in patterns:
        hits = [ln.strip() for ln in text.splitlines() if re.search(pat, ln)]
        if hits:
            hints[idx] = hits[:6]
    return hints


def clean_masters(names):
    skip = {"", "井", "谷", "店", "人", "卿", "生", "季", "约", "守", "斋", "宁"}
    out = []
    for n in names:
        if not n or len(n) < 2:
            continue
        if n in skip or "\ufffd" in n:
            continue
        if n not in out:
            out.append(n)
    return out


def main():
    skills = json.load(open(os.path.join(ROOT, "scripts", "skills_spec.json"), encoding="utf-8"))
    nt = json.load(open(os.path.join(ROOT, "scripts", "name_table.json"), encoding="utf-8"))
    msgx = load_msgx_hints()

    skill_entries = []
    routes = {
        0: {"mode": "general_high_口才", "places": [], "masters": [],
            "note": "MSGX: 辩才受教于辩才高超的武将（非固定师父）"},
        1: {"mode": "facility", "places": ["马行"], "masters": ["马行"],
            "note": "MSGX: 在马行做杂工学习马术"},
        2: {"mode": "town_npc", "places": ["京", "界镇"], "masters": ["大商人"],
            "note": "MSGX: 京/界镇大商人；需交涉，非即时传授"},
        3: {"mode": "town_master", "places": ["鹿岛"], "masters": ["上泉伊势守"],
            "note": "MSGX#1597: 关东鹿岛镇，剑术道场"},
        4: {"mode": "town_facility", "places": ["小田原", "奈良"], "masters": ["百地", "忍者"],
            "note": "MSGX#1748: 小田原/奈良忍者；最好带忍术能力者"},
        5: {"mode": "general_high_统率", "places": [], "masters": [],
            "note": "MSGX: 受教军事才能卓越武将；统御/内政亦可通过寺院讲道"},
        6: {"mode": "town_craft", "places": ["杂贺", "界镇"], "masters": ["国友", "枪铸造"],
            "note": "MSGX: 杂贺洋枪；EXE 名池含国友(铁炮师)"},
        7: {"mode": "general_or_craft", "places": ["近江"], "masters": ["穴太众"],
            "note": "MSGX: 筑城高武将/穴太众(近江)；巧匠事件链"},
        8: {"mode": "temple", "places": ["京", "甲府", "严岛"], "masters": ["高僧", "施药院", "快川"],
            "note": "MSGX#1749/#1675: 寺院高僧；礼法需政治+武功"},
        9: {"mode": "town_master", "places": ["界镇", "博多"], "masters": ["千宗易", "绍鸥", "茶道大师"],
            "note": "MSGX#412/#1206: 千宗易(界镇)；需茶具"},
    }

    master_pool = clean_masters(nt.get("role_type_names", []))
    extra_places = [p for p in nt.get("extra_place_names", []) if p and len(p) >= 2]

    for s in skills["skill_enumeration"]["canonical_order"]:
        idx = s["index"]
        r = routes.get(idx, {})
        skill_entries.append({
            "index": idx,
            "name": s["name"],
            "training_mode": r.get("mode", "unknown"),
            "recommended_places": r.get("places", []),
            "master_keywords": r.get("masters", []),
            "mechanism_note": r.get("note", ""),
            "msgx_evidence": msgx.get(idx, []),
        })

    out = {
        "source": "skills_spec + name_table + MSGX hints + EXE skill registry arch (0x443d80/0x517850)",
        "status": "routing_hints_complete; per-town spawn table runtime-only (0x517850/0x51e1f8 static=0)",
        "skill_registry": {
            "builder": "0x443d80",
            "global_ptr": "0x517838",
            "character_pool_base": "0x517850",
            "character_stride_bytes": 12,
            "skill_stream_va": "0x51e1f8",
            "skill_stream_count": 200,
            "skill_stream_stride_bytes": 10,
            "match_key": "index = (npc_ptr - 0x517850) / 12; word with ah|=0x80, al&7 = category",
            "menu_builder": "0x45f600",
            "selector": "0x45f690",
            "menu_category_map": {
                "0": "skill objects with byte@8&7 == 4",
                "1": "byte@8&7 == 1",
                "2": "byte@8&7 in {6,7}",
                "3": "byte@8&7 in {5,3}",
            },
        },
        "training_duration_msg": "MSGX#553/#554: 学习%s需%u天",
        "master_name_pool_exe": master_pool,
        "extra_town_names": extra_places,
        "skills": skill_entries,
    }

    path = os.path.join(ROOT, "scripts", "skill_master_table.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("wrote", path, "(%d skills, %d master pool names)" % (len(skill_entries), len(master_pool)))


if __name__ == "__main__":
    main()
