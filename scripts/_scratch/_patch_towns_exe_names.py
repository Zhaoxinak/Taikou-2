# -*- coding: utf-8 -*-
"""Sync scripts/towns.json castle names with EXE authority (castle_names_exe.json)."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOWNS = os.path.join(ROOT, "scripts", "towns.json")
EXE_NAMES = os.path.join(ROOT, "scripts", "castle_names_exe.json")

# home_city id -> EXE name overrides beyond castle_names_exe (extended name table)
EXTRA = {
    124: "本愿寺",  # code 0x7C, name_table slot 88+0x7C region
}


def main():
    towns = json.load(open(TOWNS, encoding="utf-8"))
    exe = {c["id"]: c["exe_name"] for c in json.load(open(EXE_NAMES, encoding="utf-8"))["castles"]}
    exe.update(EXTRA)

    changed = []
    for t in towns["towns"]:
        cid = t["id"]
        if cid not in exe:
            continue
        auth = exe[cid]
        old = t["name"]
        new = auth + "城"
        if old == new:
            continue
        t["name"] = new
        if auth in t.get("desc", ""):
            pass
        elif old.replace("城", "") in t.get("desc", ""):
            t["desc"] = t["desc"].replace(old.replace("城", ""), auth)
        else:
            t["desc"] = t["desc"].replace(old, new)
        changed.append((cid, t["code_hex"], old, new))

    towns["source"] = "TOWNPOS.DAT + castle_names_exe.json (EXE authoritative names, 2026-08-28)"
    json.dump(towns, open(TOWNS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("patched %d towns:" % len(changed))
    for row in changed:
        print("  id=%d code=%s  %s -> %s" % row)


if __name__ == "__main__":
    main()
